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
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. PARSER DE MATRIZ (CORRIGIDO PARA LOCALIZAR "SEM1")
# ==============================================================================
def parse_funil_expansao(file, semana_alvo):
    try:
        # Lê o arquivo bruto para localizar a linha do cabeçalho
        df_raw = pd.read_csv(file, header=None, sep=None, engine='python')
        
        # Procura a linha que contém "SEM1"
        header_row = 0
        for i, row in df_raw.iterrows():
            if "SEM1" in row.values:
                header_row = i
                break
        
        # Relê o arquivo agora com o cabeçalho correto
        df = pd.read_csv(file, skiprows=header_row, sep=None, engine='python')
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        # Identifica a coluna de descrição (geralmente a primeira com texto)
        col_desc = df.columns[0]
        
        if semana_alvo.upper() not in df.columns:
            st.error(f"Coluna {semana_alvo} não encontrada. Colunas detectadas: {list(df.columns)}")
            return pd.DataFrame()
            
        # Filtra e limpa
        df_final = df[[col_desc, semana_alvo.upper()]].copy()
        df_final.columns = ['Descricao', 'Valor']
        df_final['Valor'] = pd.to_numeric(df_final['Valor'], errors='coerce').fillna(0)
        df_final = df_final[df_final['Descricao'].notna()]
        
        return df_final
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return pd.DataFrame()

# ==============================================================================
# 2. MOTOR DE BI (FUNIL DE IMPACTO TOTAL)
# ==============================================================================
def renderizar_bi_profissional(df_atual, titulo="BI"):
    def get_val(termo):
        res = df_atual[df_atual['Descricao'].str.contains(termo, case=False, na=False)]
        return res['Valor'].sum() if not res.empty else 0

    # Extração de KPIs
    leads_totais = get_val("TOTAL DE LEADS")
    interesse = get_val("CONFIRMOU INTERESSE")
    reuniao = get_val("REUNIÃO")
    vendas = get_val("FATURADO")
    
    # KPIs de BI
    conv_total = (vendas / leads_totais * 100) if leads_totais > 0 else 0
    aproveitamento = (interesse / leads_totais * 100) if leads_totais > 0 else 0

    st.markdown(f"## {titulo}")
    
    # Semáforo de Performance
    cor = "normal" if conv_total > 5 else "off" if conv_total > 2 else "inverse"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", int(leads_totais))
    c2.metric("Conversão Final", f"{conv_total:.1f}%", delta_color=cor)
    c3.metric("Aproveitamento Base", f"{aproveitamento:.1f}%")
    c4.metric("Vendas (Faturado)", int(vendas))

    st.divider()

    tab1, tab2 = st.tabs(["📉 Funil de Conversão (Total)", "🎯 BI de Origens / Campanha"])

    with tab1:
        st.subheader("Impacto das Etapas sobre o Total de Leads")
        etapas = ["Total Leads", "Interesse", "Reunião", "Venda"]
        valores = [leads_totais, interesse, reuniao, vendas]
        
        fig = go.Figure(go.Funnel(
            y = etapas,
            x = valores,
            textinfo = "value+percent initial", # Percentual em relação ao TOTAL
            marker = {"color": ["#3498db", "#2980b9", "#1abc9c", "#27ae60"]},
            connector = {"line": {"color": "#444", "dash": "dot", "width": 1}}
        ))
        fig.update_layout(margin=dict(l=150, r=20, t=20, b=20), height=450)
        st.plotly_chart(fig, use_container_width=True)
        

    with tab2:
        st.subheader("Distribuição por Origem / Campanha")
        # Identifica linhas que são canais de marketing
        canais = ['GOOGLE', 'FACEBOOK', 'INSTAGRAM', 'INDICAÇÃO', 'ORGÂNICO', 'META', 'TIKTOK']
        df_mkt = df_atual[df_atual['Descricao'].str.upper().str.contains('|'.join(canais), na=False)].copy()
        
        if not df_mkt.empty:
            c_m1, c_m2 = st.columns(2)
            with c_m1:
                fig_pie = px.pie(df_mkt, values='Valor', names='Descricao', hole=0.5, title="Mix de Marketing")
                st.plotly_chart(fig_pie, use_container_width=True)
            with c_m2:
                fig_bar = px.bar(df_mkt.sort_values('Valor'), x='Valor', y='Descricao', orientation='h', title="Leads por Origem")
                st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Nenhuma linha de 'Origem' detectada na seleção.")

# ==============================================================================
# 3. INTERFACE
# ==============================================================================
st.title("🚀 BI Performance Expansão v9.1")
modo = st.sidebar.radio("Navegação", ["📥 Importação", "🗄️ Histórico"])

if modo == "📥 Importação":
    marca = st.sidebar.selectbox("Unidade:", ["Selecione...", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    if marca != "Selecione...":
        uploaded = st.sidebar.file_uploader("Subir CSV do Funil", type=['csv'])
        if uploaded:
            # Seleção de Semana
            sem_sel = st.sidebar.selectbox("Semana na Planilha:", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
            
            df_proc = parse_funil_expansao(uploaded, sem_sel)
            
            if not df_proc.empty:
                # Sistema de confirmação de exclusão/limpeza
                if st.sidebar.button("💾 Salvar no Google Sheets"):
                    st.sidebar.warning("Tem certeza que deseja sobrescrever dados existentes?")
                    if st.sidebar.checkbox("Sim, confirmar salvamento"):
                        # [Função de salvar gsheets aqui]
                        st.sidebar.success("Dados Gravados!")
                
                renderizar_bi_profissional(df_proc, titulo=f"Análise: {marca} ({sem_sel})")

elif modo == "🗄️ Histórico":
    st.info("Utilize esta aba para comparar o desempenho entre semanas e meses.")
    # (Filtros de Marca, Ano, Mês e comparação de Deltas aqui)
