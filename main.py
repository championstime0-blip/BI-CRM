import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import gspread
import os
import json
from google.oauth2.service_account import Credentials

# =====================================================
# CONFIG STREAMLIT
# =====================================================
st.set_page_config(
    page_title="BI Expansão Performance",
    page_icon="🚀",
    layout="wide"
)

st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #000000 !important;
    color: #FFFFFF !important;
}
.stApp {
    background-color: #000000;
}
</style>
""", unsafe_allow_html=True)

st.title("🚀 BI Expansão Performance")

# =====================================================
# GOOGLE SHEETS AUTH (ENV VAR)
# =====================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

if "GOOGLE_SERVICE_ACCOUNT_JSON" not in os.environ:
    st.error("Variável GOOGLE_SERVICE_ACCOUNT_JSON não configurada no ambiente.")
    st.stop()

service_account_info = json.loads(
    os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]
)

creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES
)

gc = gspread.authorize(creds)

SPREADSHEET = "BI_Historico"
WORKSHEET = "HISTORICO_LEADS"

# =====================================================
# FUNÇÕES DB
# =====================================================
def load_db():
    sh = gc.open(SPREADSHEET)
    ws = sh.worksheet(WORKSHEET)
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    return df, ws

def seed_if_empty(ws):
    ws.append_row([
        datetime.now().strftime("%Y-%m-%d"),
        "SEM1",
        "Seed",
        "Sem resposta",
        "Em Andamento",
        "",
        "sistema",
        "seed",
        "N/A"
    ])

# =====================================================
# NORMALIZAÇÃO
# =====================================================
def normalize(df):
    if df.empty:
        return df

    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    if "Status_Calc" not in df.columns:
        df["Status_Calc"] = "Em Andamento"

    df.loc[df["Etapa"].str.lower() == "faturado", "Status_Calc"] = "Ganho"
    df.loc[df.get("Motivo de Perda", "") != "", "Status_Calc"] = "Perdido"

    return df

# =====================================================
# KPIs
# =====================================================
def kpis(df):
    total = len(df)
    ganhos = (df["Status_Calc"] == "Ganho").sum()
    perdas = (df["Status_Calc"] == "Perdido").sum()
    conversao = (ganhos / total * 100) if total else 0
    return total, ganhos, perdas, conversao

# =====================================================
