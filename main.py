import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIG STREAMLIT
# =========================
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

# =========================
# GOOGLE SHEETS AUTH
# =========================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)

gc = gspread.authorize(creds)

SPREADSHEET_NAME = "BI_Historico"
WORKSHEET_NAME = "HISTORICO_LEADS"

# =========================
# FUNÇÕES DB
# =========================
def carregar_historico():
    sh = gc.open(SPREADSHEET_NAME)
    ws = sh.worksheet(WORKSHEET_NAME)

    records = ws.get_all_records()
    df = pd.DataFrame(records)

    return df, ws

def seed_inicial(ws):
    linha_seed = [
        datetime.now().strftime("%Y-%m-%d"),
        "SEM1",
        "EXEMPLO",
        "Seed Inicial",
        "Seed",
        "N/A",
        "sistema",
        "seed_auto",
        "N/A"
    ]
    ws.append_row(linha_seed)

# =========================
# MODOS
# =========================
modo = st.radio(
    "Selecione o Modo:",
    ["📥 Importar Planilha", "🗄️ Histórico Gerencial"],
    horizontal=True
)

# =========================
# HISTÓRICO GERENCIAL
# =========================
if modo == "🗄️ Histórico Gerencial":

    df_hist, ws = carregar_historico()

    # 👉 SE SÓ TIVER CABEÇALHO, CRIA SEED
    if df_hist.empty:
        st.warning("Banco vazio detectado. Criando seed inicial automaticamente...")
        seed_inicial(ws)
        df_hist, _ = carregar_historico()

    st.success("Banco de dados carregado com sucesso.")

    # KPIs
    col1, col2, col3 = st.columns(3)

    col1.metric("Total de Registros", len(df_hist))
    col2.metric("Marcas", df_hist["marca_ref"].nunique())
    col3.metric("Semanas", df_hist["semana_ref"].nunique())

    st.divider()

    st.subheader("📊 Histórico Completo")
    st.dataframe(df_hist, use_container_width=True)

# =========================
# IMPORTAÇÃO (PLACEHOLDER)
# =========================
else:
    st.info("Modo Importar Planilha — em uso para alimentar o histórico.")
