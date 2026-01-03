# ==============================================================================
# BI-CRM PERFORMANCE 2.0
# Streamlit | BI Corporativo | Franquias
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="BI-CRM Performance 2.0",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILO GLOBAL
# ==============================================================================
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 26px; font-weight: bold; }
.block-container { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FUNÇÕES UTILITÁRIAS
# ==============================================================================
def encontrar_coluna(df, termos):
    for col in df.columns:
        col_norm = col.strip().lower()
        for termo in termos:
            if termo in col_norm:
                return col
    return None

def ler_csv_universal(file):
    for sep in [';', ',']:
        for enc in ['utf-8-sig', 'latin-1']:
            try:
                return pd.read_csv(file, sep=sep, encoding=enc)
            except:
                pass
    return pd.DataFrame()

# ==============================================================================
# CONEXÃO GOOGLE SHEETS
# ==============================================================================
@st.cache_resource(show_spinner=False)
def conectar_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    if "CREDENCIAIS_GOOGLE" in os.environ:
        creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
    elif "gsheets" in st.secrets:
        creds_dict = dict(st.secrets["gsheets"])
    else:
        raise RuntimeError("Credenciais Google não encontradas")

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("BI_Historico").sheet1

@st.cache_data(show_spinner=False)
def carregar_historico():
    sheet = conectar_gsheets()
    return pd.DataFrame(sheet.get_all_records())

# ==============================================================================
# PROCESSAMENTO E INTELIGÊNCIA DE BI
# ==============================================================================
@st.cache_data(show_spinner=False)
def processar_dados(df):
    if df.empty:
        return df

    df = df.copy()
    df.columns = df.columns.str.strip()

    col_etapa   = encontrar_coluna(df, ['etapa', 'fase', 'stage'])
    col_estado  = encontrar_coluna(df, ['estado'])
    col_motivo  = encontrar_coluna(df, ['motivo'])
    col_data    = encontrar_coluna(df, ['criacao', 'criação'])
    col_resp    = encontrar_coluna(df, ['responsavel'])
    col_tel     = encontrar_coluna(df, ['telefone'])

    etapa  = df[col_etapa].astype(str).str.lower() if col_etapa else ''
    estado = df[col_estado].astype(str).str.lower() if col_estado else ''
    motivo = df[col_motivo].astype(str).str.lower() if col_motivo else ''

    # ---------------- STATUS (REGRA DE OURO) ----------------
    df['Status_Calc'] = 'Em Andamento'

    if col_etapa:
        df.loc[etapa == 'faturado', 'Status_Calc'] = 'Ganho'

    df.loc[
        (estado == 'perdida') |
        ((motivo != '') & (motivo != 'nan')),
        'Status_Calc'
    ] = 'Perdido'

    # ---------------- DATA ----------------
    if col_data:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_data], errors='coerce', dayfirst=True)

    # ---------------- SCORE DE SONDAGEM ----------------
    perguntas = ['Atuação', 'Cidade Interesse', 'Prazo', 'Investimento', 'Capital de Investimento']
    score = 0
    for p in perguntas:
        if p in df.columns:
            score += df[p].notna() & (df[p].astype(str).str.strip() != '')

    df['Score_Sondagem'] = (score / len(perguntas)) * 100

    # ---------------- ALERTAS ----------------
    df['Alerta_Inalcancavel'] = (
        etapa.str.contains('aguardando') & etapa.str.contains('sem resposta')
    )

    df['Erro_Origem'] = (
        df[col_tel].astype(str).str.contains('errado', case=False)
        if col_tel else False
    )

    return df

# ==============================================================================
# FILTROS
# ==============================================================================
def aplicar_filtros(df):
    st.sidebar.header("🎯 Filtros")

    marca = st.sidebar.selectbox(
        "Marca",
        ['Todas', 'Microlins', 'Prepara IA', 'Ensina Mais Pedro', 'Ensina Mais Lu']
    )

    if marca != 'Todas':
        if 'Pedro' in marca:
            df = df[df['Responsável'].str.contains('pedro', case=False, na=False)]
        elif 'Lu' in marca:
            df = df[df['Responsável'].str.contains('lu', case=False, na=False)]

    return df

# ==============================================================================
# DASHBOARD
# ==============================================================================
def render_dashboard(df):
    if df.empty:
        st.warning("Sem dados disponíveis.")
        return

    st.title("📊 BI-CRM Performance 2.0")

    # ---------------- PERÍODO ----------------
    if 'Data_Criacao_DT' in df.columns:
        st.info(
            f"📅 Período analisado: "
            f"{df['Data_Criacao_DT'].min().date()} → {df['Data_Criacao_DT'].max().date()}"
        )

    # ---------------- KPIs ----------------
    total = len(df)
    ganhos = (df['Status_Calc'] == 'Ganho').sum()
    conv = ganhos / total * 100 if total else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", total)
    c2.metric("Vendas", ganhos, f"{conv:.1f}%")
    c3.metric("Score Médio", f"{df['Score_Sondagem'].mean():.0f}%")
    c4.metric("Perdidos", (df['Status_Calc'] == 'Perdido').sum())

    # ---------------- FUNIL ----------------
    funil_ordem = [
        "Sem resposta", "Aguardando Resposta", "Confirmou Interesse",
        "Qualificado", "Reunião Agendada", "Reunião Realizada",
        "Follow-up", "negociação", "Em aprovação", "Faturado"
    ]

    funil_df = (
        df['Etapa']
        .value_counts()
        .reindex(funil_ordem)
        .fillna(0)
        .reset_index()
    )

    fig_funil = go.Funnel(
        y=funil_df['index'],
        x=funil_df['Etapa'],
        textinfo="value+percent initial"
    )

    st.plotly_chart(go.Figure(fig_funil), use_container_width=True)

    # ---------------- PERDAS ----------------
    perdas = (
        df[df['Status_Calc'] == 'Perdido']['Motivo de Perda']
        .value_counts()
        .reset_index()
    )
    perdas['Percentual'] = perdas['Motivo de Perda'] / total * 100

    fig_perdas = px.bar(
        perdas,
        x='Motivo de Perda',
        y='index',
        orientation='h',
        text=perdas['Motivo de Perda'].round(1).astype(str) + '%',
        title="Motivos de Perda"
    )

    st.plotly_chart(fig_perdas, use_container_width=True)

    st.divider()
    st.dataframe(df, use_container_width=True)

# ==============================================================================
# MAIN
# ==============================================================================
def main():
    st.sidebar.header("📥 Entrada de Dados")

    arquivo = st.sidebar.file_uploader("Upload Pedro.csv", type=['csv'])

    if arquivo:
        df_csv = ler_csv_universal(arquivo)
        df_hist = carregar_historico()
        df = pd.concat([df_csv, df_hist], ignore_index=True)
    else:
        df = carregar_historico()

    df = processar_dados(df)
    df = aplicar_filtros(df)
    render_dashboard(df)

# ==============================================================================
# START
# ==============================================================================
if __name__ == "__main__":
    main()
