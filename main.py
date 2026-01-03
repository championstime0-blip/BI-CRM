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
# AUTENTICAÇÃO GOOGLE SHEETS
# ================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

@st.cache_resource
def conectar_gsheets():
    """
    Conecta ao Google Sheets usando Service Account via variável de ambiente
    """
    if "GOOGLE_SERVICE_ACCOUNT_JSON" not in os.environ:
        st.error("❌ Variável GOOGLE_SERVICE_ACCOUNT_JSON não configurada no Render.")
        st.stop()

    try:
        creds_info = json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        creds = Credentials.from_service_account_info(
            creds_info,
            scopes=SCOPES
        )
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error("❌ Erro ao autenticar no Google Sheets")
        st.exception(e)
        st.stop()

def carregar_planilha(nome_planilha: str, aba: str):
    client = conectar_gsheets()
    sheet = client.open(nome_planilha).worksheet(aba)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def salvar_planilha(nome_planilha: str, aba: str, df: pd.DataFrame):
    client = conectar_gsheets()
    sheet = client.open(nome_planilha).worksheet(aba)
    sheet.append_rows(df.fillna("").astype(str).values.tolist())

# ================================
# EXEMPLO DE USO
# ================================
st.title("📊 BI-CRM Performance")

if st.button("🔄 Carregar Histórico"):
    df = carregar_planilha("BI_Historico", "base")
    st.dataframe(df, use_container_width=True)

if st.button("💾 Salvar Exemplo"):
    exemplo = pd.DataFrame([
        {"lead": "João", "status": "Ganho"},
        {"lead": "Maria", "status": "Perdido"}
    ])
    salvar_planilha("BI_Historico", "base", exemplo)
    st.success("Dados salvos com sucesso ✅")
