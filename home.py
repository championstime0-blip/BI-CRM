import streamlit as st
from backend.sheets import connect_sheet

st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# ===== CONFIG =====
SHEET_ID = "1ZlDk-xuq4T09vajvdkeStu9sKSO4-f4QHDJkSSiWm5g"
ABA_BASE = "BASE"


# ===== SECRETS =====
credentials = st.secrets["google_service_account"]

# ===== LOAD =====
@st.cache_data(ttl=300)
def carregar_base(creds):
    df, _ = connect_sheet(creds, SHEET_ID, ABA_BASE)
    return df

df = carregar_base(credentials)

st.success(f"Base carregada com sucesso ({len(df)} linhas)")
st.dataframe(df.head())
