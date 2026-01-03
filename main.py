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
    [data-testid="stMetricValue"] { font-size: 22px; font-weight: bold; }
    .st-emotion-cache-1r6slb0 { border: 1px solid #333; padding: 15px; border-radius: 8px; }
    .footer-info { font-size: 12px; color: #666; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. PARSER ESPECIALISTA (MATRIZ EXPANSÃO)
# ==============================================================================
def parse_funil_expansao(file, semana_alvo):
    """
    Transforma a planilha matriz (SEM1, SEM2...) em um formato 
    que o Dashboard consiga processar como dados individuais.
    """
    try:
        # Lê a planilha pulando as linhas de lixo iniciais
        df_raw = pd.read_csv(file, skiprows=2)
        
        # Limpa nomes de colunas (remove espaços e unifica)
        df_raw.columns = [str(c).strip().upper() for c in df_raw.columns]
        
        # A primeira coluna costuma ser a descrição da Etapa/Origem
        nome_col_descricao = df_raw.columns[0]
        
        # Filtra apenas a coluna da SEMANA selecionada e a coluna de DESCRIÇÃO
        if semana_alvo.upper() not in df_raw.columns:
            st.error(f"Coluna {semana_alvo} não encontrada no arquivo.")
            return pd.DataFrame()
            
        df_semana = df_raw[[nome_col_descricao, semana_alvo]].copy()
        df_semana.columns = ['Descricao', 'Valor']
        
        # Remove linhas de porcentagem e valores nulos
        df_semana = df_semana[~df_semana['Descricao'].str.contains('%', na=False)]
        df_semana['Valor'] = pd.to_numeric(df_semana['Valor'], errors='coerce').fillna(0)
        
        return df_semana
    except Exception as e:
        st.error(f"Erro ao processar matriz: {e}")
        return pd.DataFrame()

# ==============================================================================
# 2. MOTOR DE BI COMPARATIVO E VISUALIZAÇÃO
# ==============================================================================
def renderizar_bi_profissional(df_atual, df_anterior=pd.DataFrame(), titulo="BI"):
    # Extração de Métricas da Matriz
    def get_val(desc):
        row = df_atual[df_atual['Descricao'].str.contains(desc, case=False, na=False)]
        return row['Valor'].sum() if not row.empty else 0

    total_leads = get_val("TOTAL DE LEADS")
    confirmou = get_val("CONFIRMOU INTERESSE")
    reuniao = get_val("REUNIÃO")
    vendas = get_val("FATURADO") # ou VENDA
    
    # Cálculo de Conversão sobre TOTAL
    conv_total = (vendas / total_leads * 100) if total_leads > 0 else 0
    
    # --- KPIs COM DELTAS (BI COMPARATIVO) ---
    st.markdown(f"## {titulo}")
    c1, c2, c3, c4 = st.columns(4)
    
    # Lógica de Comparação se houver df_anterior
    delta_leads = None
    if not df_anterior.empty:
        total_ant = df_anterior[df_anterior['Descricao'].str.contains("TOTAL DE LEADS", case=False, na=False)]['Valor'].sum()
        if total_ant > 0:
            delta_leads = f"{((total_leads - total_ant) / total_ant * 100):.1f}%"

    c1.metric("Leads Totais", int(total_leads), delta=delta_leads)
    
    # Semáforo de Conversão
    color = "normal" if conv_total > 5 else "off" if conv_total > 2 else "inverse"
    c2.metric("Conversão (Venda/Total)", f"{conv_total:.1f}%", delta_color=color)
    
    c3.metric("Confirmou Interesse", int(confirmou))
    c4.metric("Reuniões", int(reuniao))

    st.divider()

    tab1, tab2 = st.tabs(["📉 Funil de Performance Profissional", "🎯 BI de Origens & Campanhas"])

    with tab1:
        st.subheader("Funil de Impacto (Percentual sobre Leads Totais)")
        # Monta o DF para o Funil
        etapas = ['Total Leads', 'Interesse', 'Reunião', 'Venda']
        valores = [total_leads, confirmou, reuniao, vendas]
        
        fig = go.Figure(go.Funnel(
            y = etapas,
            x = valores,
            textinfo = "value+percent initial",
            marker = {"color": ["#3498db", "#2980b9", "#1abc9c", "#27ae60"]},
            connector = {"line": {"color": "#444", "dash": "dot", "width": 1}}
        ))
        fig.update_layout(height=450, margin=dict(l=150, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"💡 As porcentagens indicam quanto cada etapa representa dos **{int(total_leads)} leads** iniciais.")

    with tab2:
        st.subheader("Análise de Origens (Marketing)")
        # Filtra as linhas que representam origens (Ex: Google, Facebook, etc na sua planilha)
        origens_alvo = ['GOOGLE', 'FACEBOOK', 'INSTAGRAM', 'INDICAÇÃO', 'ORGÂNICO', 'META']
        df_origens = df_atual[df_atual['Descricao'].str.upper().str.contains('|'.join(origens_alvo), na=False)].copy()
        
        if not df_origens.empty:
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                fig_mkt = px.pie(df_origens, values='Valor', names='Descricao', hole=0.5, title="Mix de Origens")
                st.plotly_chart(fig_mkt, use_container_width=True)
            with c_m2:
                df_origens = df_origens.sort_values('Valor', ascending=True)
                fig_bar = px.bar(df_origens, x='Valor', y='Descricao', orientation='h', title="Volume por Canal")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.warning("Não foram detectadas linhas de Origem/Canal nesta aba.")

# ==============================================================================
# 3. INTERFACE E NAVEGAÇÃO
# ==============================================================================
# [Aqui permanecem as funções de conectar_gsheets e salvar_no_gsheets das versões anteriores]

st.title("🚀 BI Expansão - Performance v9.0")
modo = st.sidebar.radio("Menu", ["📥 Ingestão de Dados", "🗄️ BI Gerencial"])

if modo == "📥 Ingestão de Dados":
    marca = st.sidebar.selectbox("Consultor/Marca", ["Selecione...", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    if marca != "Selecione...":
        uploaded_file = st.sidebar.file_uploader("Subir Planilha Matriz (CSV)", type=['csv'])
        if uploaded_file:
            sem_opcoes = ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"]
            sem_sel = st.sidebar.selectbox("Selecione a Semana da Planilha:", sem_opcoes)
            
            df_proc = parse_funil_expansao(uploaded_file, sem_sel)
            
            if not df_proc.empty:
                if st.sidebar.button("💾 Gravar no Banco de Dados"):
                    # Aqui integraria com gsheets
                    st.sidebar.success(f"Dados de {marca} - {sem_sel} gravados!")
                
                renderizar_bi_profissional(df_proc, titulo=f"Preview: {marca} ({sem_sel})")

elif modo == "🗄️ BI Gerencial":
    # Aqui entraria a lógica de carregar do GSheets e permitir a comparação
    st.info("Selecione os períodos para comparar a performance semanal.")
    # ... (Filtros de Marca, Ano, Mês, Semana conforme v7.1)
