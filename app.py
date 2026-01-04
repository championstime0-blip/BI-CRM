import streamlit as st
from backend.sheets import connect_sheet
from backend.processor import processar
from backend.kpis import calcular_kpis
from backend.historico import salvar_snapshot
from frontend.styles import load_css
from frontend.dashboard import dashboard

st.set_page_config(layout="wide")
load_css()

st.title("📊 BI CRM – Expansão")

modo = st.sidebar.radio("Modo de Visualização", ["Diretor", "Operação"])

@st.cache_data(ttl=600)
def carregar_base(creds):
    df, _ = connect_sheet(creds, "CRM_EXPANSAO", "BASE")
    return df

@st.cache_data(ttl=600)
def carregar_historico(creds):
    _, sheet = connect_sheet(creds, "CRM_EXPANSAO", "HISTORICO")
    return sheet

credentials = st.secrets["google_service_account"]

df = carregar_base(credentials)
df = processar(df)

kpis = calcular_kpis(df)

dashboard(kpis, modo)

if st.sidebar.button("📌 Salvar KPI Histórico"):
    _, sheet_hist = connect_sheet(credentials, "CRM_EXPANSAO", "HISTORICO")
    salvar_snapshot(sheet_hist, "Ensina Mais", kpis)
    st.success("Snapshot salvo com sucesso")
