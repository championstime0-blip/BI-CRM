import streamlit as st
import pandas as pd
import json
import os
import gspread
from google.oauth2.service_account import Credentials

# =====================================
# CONFIG STREAMLIT
# =====================================
st.set_page_config(
    page_title="BI-CRM Performance",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================
# GOOGLE SHEETS AUTH (RENDER)
# =====================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_gsheets():
    if "CREDENCIAIS_GOOGLE" not in os.environ:
        st.error("❌ Variável CREDENCIAIS_GOOGLE não encontrada no ambiente.")
        st.stop()

    try:
        creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])

        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

        client = gspread.authorize(credentials)
        return client

    except Exception as e:
        st.error("❌ Erro ao autenticar no Google Sheets")
        st.exception(e)
        st.stop()

# =====================================
# FUNÇÕES DE BANCO (GOOGLE SHEETS)
# =====================================
def carregar_planilha(nome_planilha: str, aba: str) -> pd.DataFrame:
    client = conectar_gsheets()
    sheet = client.open(nome_planilha).worksheet(aba)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def salvar_planilha(nome_planilha: str, aba: str, df: pd.DataFrame):
    client = conectar_gsheets()
    sheet = client.open(nome_planilha).worksheet(aba)
    sheet.append_rows(df.fillna("").astype(str).values.tolist())

# =====================================
# INTERFACE
# =====================================
st.title("📊 BI-CRM Performance")

st.sidebar.header("⚙️ Ações")

if st.sidebar.button("🔄 Carregar Histórico"):
    df = carregar_planilha("BI_Historico", "base")
    st.success("Dados carregados com sucesso ✅")
    st.dataframe(df, use_container_width=True)

if st.sidebar.button("💾 Salvar Exemplo"):
    exemplo = pd.DataFrame([
        {"lead": "João", "status": "Ganho"},
        {"lead": "Maria", "status": "Perdido"}
    ])
    salvar_planilha("BI_Historico", "base", exemplo)
    st.success("Exemplo salvo no Google Sheets ✅")
