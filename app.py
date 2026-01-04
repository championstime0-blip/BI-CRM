import streamlit as st
from backend.loader import load_csv
from backend.processor import processar
from backend.kpis import calcular_kpis
from frontend.styles import load_css
from frontend.components import profile_header, date_card
from frontend.dashboard import dashboard

ETAPAS_FUNIL = [
    "Sem contato","Aguardando Resposta","Confirmou Interesse",
    "Qualificado","Reunião Agendada","Reunião Realizada",
    "Follow-up","negociação","em aprovação","faturado"
]

st.set_page_config(layout="wide")
load_css()

st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

file = st.file_uploader("Upload CSV RD Station", type="csv")

if file:
    df = processar(load_csv(file))
    kpis = calcular_kpis(df)

    resp = df["Responsável"].mode()[0] if "Responsável" in df.columns else "Não Identificado"
    equipe = df["Equipe"].mode()[0] if "Equipe" in df.columns else "Geral"

    profile_header(resp, equipe)

    if "Data de Criação" in df.columns:
        date_card(
            df["Data de Criação"].min().strftime("%d/%m/%Y"),
            df["Data de Criação"].max().strftime("%d/%m/%Y")
        )

    dashboard(df, kpis, ETAPAS_FUNIL)
