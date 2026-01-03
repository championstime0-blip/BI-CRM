# ===============================
# BI EXPANSÃO – VERSÃO FINAL
# ===============================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import io

import gspread
from google.oauth2.service_account import Credentials

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="BI Expansão Corporativo",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# ESTILO (FUNDO PRETO TOTAL)
# ===============================
st.markdown("""
<style>
    body, .stApp {
        background-color: #000000;
        color: #ffffff;
    }
</style>
""", unsafe_allow_html=True)

# ===============================
# GOOGLE SHEETS – CONEXÃO SEGURA
# ===============================
def conectar_gsheets():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]

        if "CREDENCIAIS_GOOGLE" not in os.environ:
            st.error("❌ Variável CREDENCIAIS_GOOGLE não encontrada no Render")
            return None

        creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        sheet = client.open("BI_Historico")

        try:
            return sheet.worksheet("dados")
        except:
            ws = sheet.add_worksheet(title="dados", rows=1000, cols=50)
            ws.append_row(["data_upload", "semana_ref", "marca_ref"])
            return ws

    except Exception as e:
        st.error(f"Erro Google Sheets: {e}")
        return None

# ===============================
# SALVAR HISTÓRICO
# ===============================
def salvar_no_gsheets(df, semana, marca):
    ws = conectar_gsheets()
    if ws is None or df.empty:
        return False

    df_save = df.copy()
    df_save["data_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df_save["semana_ref"] = semana
    df_save["marca_ref"] = marca

    ws.append_rows(df_save.fillna("").astype(str).values.tolist())
    return True

# ===============================
# CARREGAR HISTÓRICO
# ===============================
def carregar_historico():
    ws = conectar_gsheets()
    if ws is None:
        return pd.DataFrame()
    return pd.DataFrame(ws.get_all_records())

# ===============================
# LEITURA CSV
# ===============================
def load_csv(file):
    raw = file.getvalue()
    for enc in ["utf-8-sig", "latin-1", "cp1252"]:
        try:
            txt = raw.decode(enc)
            sep = ";" if ";" in txt.splitlines()[0] else ","
            return pd.read_csv(io.StringIO(txt), sep=sep)
        except:
            pass
    return pd.DataFrame()

# ===============================
# PROCESSAMENTO
# ===============================
def processar(df):
    if df.empty:
        return df

    df.columns = [c.strip() for c in df.columns]

    if "Etapa" not in df.columns:
        df["Etapa"] = ""

    if "Motivo de Perda" not in df.columns:
        df["Motivo de Perda"] = ""

    def status(row):
        etapa = str(row["Etapa"]).lower()
        motivo = str(row["Motivo de Perda"]).lower()

        if any(x in etapa for x in ["venda", "fechamento", "ganho"]):
            return "Ganho"
        if motivo == "" or motivo == "nan":
            return "Em Andamento"
        return "Perdido"

    df["Status_Calc"] = df.apply(status, axis=1)
    return df

# ===============================
# DASHBOARD
# ===============================
def dashboard(df):
    st.subheader("📊 Visão Geral")

    c1, c2, c3 = st.columns(3)
    c1.metric("Leads", len(df))
    c2.metric("Vendas", len(df[df["Status_Calc"] == "Ganho"]))
    c3.metric("Conversão %",
              round(len(df[df["Status_Calc"] == "Ganho"]) / len(df) * 100, 1) if len(df) else 0)

    st.divider()
    df_status = (
    df["Status_Calc"]
    .value_counts()
    .reset_index()
    .rename(columns={
        "index": "Status",
        "Status_Calc": "Quantidade"
    })
)

fig = px.bar(
    df_status,
    x="Status",
    y="Quantidade",
    title="Status dos Leads",
    text="Quantidade"
)

fig.update_layout(
    xaxis_title="Status",
    yaxis_title="Qtd de Leads",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)"
)

    
    st.plotly_chart(fig, use_container_width=True)

# ===============================
# INTERFACE
# ===============================
st.title("🚀 BI Expansão")

modo = st.radio(
    "Modo de operação",
    ["📥 Importar CSV", "🗄️ Histórico"],
    horizontal=True
)

if modo == "📥 Importar CSV":
    marca = st.sidebar.selectbox("Marca", ["Prepara", "Microlins", "Ensina Mais"])
    semana = st.sidebar.selectbox("Semana", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
    file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

    if file:
        df = processar(load_csv(file))
        dashboard(df)

        if st.sidebar.button("💾 Salvar no Banco"):
            if salvar_no_gsheets(df, semana, marca):
                st.sidebar.success("✅ Salvo com sucesso")

else:
    df_hist = carregar_historico()

    if df_hist.empty:
        st.warning("Banco vazio")
    else:
        marca_f = st.sidebar.selectbox(
            "Marca",
            ["Todas"] + sorted(df_hist["marca_ref"].unique())
        )

        if marca_f != "Todas":
            df_hist = df_hist[df_hist["marca_ref"] == marca_f]

        dashboard(df_hist)
