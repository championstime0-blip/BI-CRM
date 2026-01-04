import streamlit as st
import json
import os

from backend.sheets import connect_sheet
from backend.processor import processar
from backend.kpis import calcular_kpis
from backend.historico import salvar_snapshot
from frontend.styles import load_css
from frontend.dashboard import dashboard

# ===============================
# CONFIG
# ===============================
st.set_page_config(layout="wide")
load_css()

st.title("📊 BI CRM – Expansão")

modo = st.sidebar.radio("Modo de Visualização", ["Diretor", "Operação"])

# ===============================
# CREDENCIAIS (ROBUSTO)
# ===============================
def load_credentials():
    # 1️⃣ Tenta Streamlit Secrets (local)
    try:
        return st.secrets["google_service_account"]
    except Exception:
        pass

    # 2️⃣ Tenta ENV VAR (Render)
    env_cred = os.getenv("GOOGLE_SERVICE_ACCOUNT")
    if env_cred:
        return json.loads(env_cred)

    # 3️⃣ Falha clara
    st.error("Credenciais do Google não encontradas. Configure GOOGLE_SERVICE_ACCOUNT.")
    st.stop()

credentials = load_credentials()

# ===============================
# CACHE
# ===============================
@st.cache_data(ttl=600)
def carregar_base(creds):
    SHEET_ID = "SEU_ID_REAL_DA_PLANILHA"
    df, _ = connect_sheet(credentials, SHEET_ID, "BASE")
    return df

# ===============================
# PIPELINE
# ===============================
df = carregar_base(credentials)
df = processar(df)

kpis = calcular_kpis(df)

dashboard(kpis, modo)

# ===============================
# HISTÓRICO
# ===============================
st.sidebar.markdown("---")

if st.sidebar.button("📌 Salvar KPI Histórico"):
    _, sheet_hist = connect_sheet(credentials, "CRM_EXPANSAO", "HISTORICO")
    salvar_snapshot(sheet_hist, "Ensina Mais", kpis)
    st.sidebar.success("Snapshot salvo com sucesso")
