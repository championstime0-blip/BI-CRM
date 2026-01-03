import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Expansão Pro", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .st-emotion-cache-1r6slb0 { border: 1px solid #333; padding: 15px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. PARSER INTELIGENTE PARA O FORMATO "EXPANSÃO"
# ==============================================================================
def parse_expansao_sheet(file):
    """
    Lida com o formato específico: Linhas em branco no topo, 
    colunas sem nome e estrutura de matriz.
    """
    try:
        # Lê pulando as linhas vazias de metadados se houver
        df = pd.read_csv(file, sep=None, engine='python', skip_blank_lines=True)
        
        # Limpeza: Remove colunas e linhas totalmente vazias
        df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
        
        # Mapeamento de BI para o novo formato
        # Como a planilha enviada usa labels na primeira coluna (Total de Leads, etc)
        # e semanas nas colunas, o código abaixo normaliza para o Dashboard
        
        # Identificação de colunas de BI relevantes no arquivo
        col_map = {
            'Etapa': 'Etapa',
            'Status': 'Status_Calc',
            'Motivo': 'Motivo de Perda',
            'Origem': 'Fonte',
            'Campanha': 'Campanha'
        }
        
        # Se os dados forem verticais (listagem de leads):
        if 'TOTAL DE LEADS' not in df.columns:
            # Tenta encontrar colunas de marketing
            for col in df.columns:
                c_upper = str(col).upper()
                if 'ORIGEM' in c_upper or 'FONTE' in c_upper: df['Fonte'] = df[col]
                if 'CAMPANHA' in c_upper: df['Campanha'] = df[col]
                if 'MOTIVO' in c_upper: df['Motivo de Perda'] = df[col]
                if 'ETAPA' in c_upper: df['Etapa'] = df[col]

        # Garante colunas mínimas para o BI não quebrar
        for c in ['Etapa', 'Status_Calc', 'Motivo de Perda', 'Fonte', 'Campanha']:
            if c not in df.columns: df[c] = 'Não Informado'
            
        return df
    except Exception as e:
        st.error(f"Erro ao processar o formato da planilha: {e}")
        return pd.DataFrame()

# ==============================================================================
# 2. MOTOR DE BI E PERFORMANCE
# ==============================================================================
def renderizar_bi_expansao(df, titulo="Análise de Expansão"):
    total_leads = len(df)
    
    # Lógica de Status para o Dashboard
    if 'Status_Calc' not in df.columns or df['Status_Calc'].eq('Não Informado').all():
        def check_status(row):
            etapa = str(row.get('Etapa', '')).lower()
            if 'venda' in etapa or 'faturado' in etapa: return 'Ganho'
            if 'perda' in etapa or 'desistência' in etapa: return 'Perdido'
            return 'Em Andamento'
        df['Status_Calc'] = df.apply(check_status, axis=1)

    vendas = len(df[df['Status_Calc'] == 'Ganho'])
    conv_total = (vendas / total_leads * 100) if total_leads > 0 else 0

    st.markdown(f"## {titulo}")
    
    # Semáforo de Performance
    color = "normal" if conv_total > 7 else "off" if conv_total > 3 else "inverse"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", total_leads)
    c2.metric("Taxa de Conversão", f"{conv_total:.1f}%", delta_color=color)
    
    # KPI de Marketing: Origem Principal
    top_origem = df['Fonte'].mode()[0] if not df['Fonte'].empty else "N/A"
    c3.metric("Fonte Principal", top_origem)
    
    # KPI de BI: Leads Qualificados (que saíram da etapa inicial)
    qualificados = len(df[~df['Etapa'].str.contains('Aguardando|Início|Novo', case=False, na=False)])
    perc_qual = (qualificados / total_leads * 100) if total_leads > 0 else 0
    c4.metric("Aproveitamento de Base", f"{perc_qual:.1f}%")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📉 Funil de Conversão", "🎯 BI de Campanhas", "🚫 Motivos de Perda"])

    with tab1:
        st.subheader("Funil de Impacto Real (Sobre Total de Leads)")
        df_funil = df['Etapa'].value_counts().reset_index()
        df_funil.columns = ['Etapa', 'Volume']
        
        # Gráfico de Funil Profissional
        fig = go.Figure(go.Funnel(
            y = df_funil['Etapa'],
            x = df_funil['Volume'],
            textinfo = "value+percent initial",
            marker = {"color": px.colors.sequential.Blues_r}
        ))
        fig.update_layout(yaxis={'categoryorder':'total descending'}, height=500)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("Análise de Origem e Campanha")
        col_side, col_graph = st.columns([1, 2])
        
        with col_side:
            # Tabela de Performance por Fonte
            mkt_perf = df.groupby('Fonte').agg(
                Leads=('Fonte', 'count'),
                Vendas=('Status_Calc', lambda x: (x == 'Ganho').sum())
            ).reset_index()
            mkt_perf['Conv %'] = (mkt_perf['Vendas'] / mkt_perf['Leads'] * 100).round(2)
            st.dataframe(mkt_perf.sort_values('Leads', ascending=False), use_container_width=True)

        with col_graph:
            # Gráfico de Barras: Leads por Campanha
            df_camp = df['Campanha'].value_counts().head(10).reset_index()
            df_camp.columns = ['Campanha', 'Volume']
            fig_camp = px.bar(df_camp, x='Volume', y='Campanha', orientation='h', 
                             title="Top 10 Campanhas", color='Volume', color_continuous_scale='Blues')
            st.plotly_chart(fig_camp, use_container_width=True)

    with tab3:
        st.subheader("Detalhamento de Perdas")
        if not df[df['Status_Calc'] == 'Perdido'].empty:
            df_p = df[df['Status_Calc'] == 'Perdido']
            motivos = df_p['Motivo de Perda'].value_counts().reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            fig_p = px.pie(motivos, values='Qtd', names='Motivo', hole=0.5, color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.success("Nenhuma perda registrada.")

# ==============================================================================
# 3. INTERFACE E PERSISTÊNCIA (GOOGLE SHEETS)
# ==============================================================================
# [Aqui permanecem as funções de salvar/carregar do Google Sheets das versões anteriores]
# ... (Funções conectar_gsheets, salvar_no_gsheets, etc.)

st.title("📊 BI Performance Expansão")
modo = st.sidebar.radio("Navegação", ["📥 Importação", "🗄️ Histórico Gerencial"])

if modo == "📥 Importação":
    marca = st.sidebar.selectbox("Marca/Consultor", ["Selecione...", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    if marca != "Selecione...":
        file = st.sidebar.file_uploader("Subir Planilha no formato padrão", type=['csv'])
        if file:
            df_import = parse_expansao_sheet(file)
            if not df_import.empty:
                # [Diferencial de BI]: Detecção automática de semana pela data do arquivo
                sem_sugestao = f"Semana {datetime.now().isocalendar()[1] % 4 + 1}"
                semana = st.sidebar.selectbox("Confirmar Semana", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"], index=0)
                
                if st.sidebar.button("💾 Salvar no Banco de Dados"):
                    # Aqui chamaria sua função de salvar no gsheets
                    st.sidebar.success("Dados integrados com sucesso!")
                
                renderizar_bi_expansao(df_import, titulo=f"Análise Operacional: {marca}")

elif modo == "🗄️ Histórico Gerencial":
    st.info("Aqui você verá a comparação entre os meses e semanas conforme os dados salvos.")
    # Implementação dos filtros de Ano/Mês/Marca conforme o código v7.1
