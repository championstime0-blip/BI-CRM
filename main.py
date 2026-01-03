import streamlit as st
import pandas as pd
import json
import os
import gspread
from google.oauth2.service_account import Credentials

# ================================
# CONFIG STREAMLIT
# ================================
st.set_page_config(
    page_title="BI-CRM Performance",
    layout="wide"
)

# ================================
# GOOGLE SHEETS AUTH (RENDER)
# ================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_gsheets():
    """
    Autenticação via variável de ambiente CREDENCIAIS_GOOGLE
    (Padrão Render)
    """
    if "CREDENCIAIS_GOOGLE" not in os.environ:
        st.error("❌ Variável CREDENCIAIS_GOOGLE não encontrada no ambiente.")
        st.stop()

    try:
        creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])

        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

        client = gspread.authorize(creds)
        return client

    except Exception as e:
        st.error("❌ Erro ao autenticar no Google Sheets")
        st.exception(e)
        st.stop()

# ================================
# FUNÇÕES DE BANCO (GSheets)
# ================================
def carregar_planilha(nome_planilha: str, aba: str) -> pd.DataFrame:
    client = conectar_gsheets()
    sheet = client.open(nome_planilha).worksheet(aba)
    return pd.DataFrame(sheet.get_all_records())

def salvar_planilha(nome_planilha: str, aba: str, df: pd.DataFrame):
    client =
