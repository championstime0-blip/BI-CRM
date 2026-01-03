import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ================= CONFIG STREAMLIT =================
st.set_page_config(
    page_title="BI Expansão Performance",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================= CSS =================
st.markdown("""
<style>
.stApp { background-color: #0e1117; color: #ffffff; }
h1, h2, h3, h4 { color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE SHEETS =================
def conectar_gsheets():
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        if "CREDENCIAIS_GOOGLE" in os.environ:
            creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            st.error("Variável CREDENCIAIS_GOOGLE não configurada.")
            return None

        client = gspread.authorize(creds)
        return client.open("BI_Historico").sheet1

    except Exception as e:
        st.error(f"Erro Google Sheets: {e}")
        return None

def salvar_no_gsheets(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet is None:
        return False

    df_save = df.copy()
    df_save["semana_ref"] = semana
    df_save["marca_ref"] = marca
    df_save["data_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_rows(df_save.fillna("").astype(str).values.tolist())
    return True

def carregar_historico():
    sheet = conectar_gsheets()
    if sheet:
        return pd.DataFrame(sheet.get_all_records())
    return pd.DataFrame()

# ================= LEITURA CSV =================
def load_data(file):
    raw = file.getvalue()
    for enc in ["utf-8-sig", "latin-1", "iso-8859-1"]:
        try:
            text = raw.decode(enc)
            sep = ";" if ";" in text.splitlines()[0] else ","
            return pd.read_csv(io.StringIO(text), sep=sep)
        except:
            pass
    return pd.DataFrame()

# ================= PROCESSAMENTO =================
def process_data(df):
    df.columns = [c.strip() for c in df.columns]

    col_data = next((c for c in df.columns if "data" in c.lower()), None)
    if col_data:
        df["Data_Criacao_DT"] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

    def status_calc(row):
        etapa = str(row.get("Etapa", "")).lower()
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()

        if "faturado" in etapa or "venda" in etapa:
            return "Ganho"
        if motivo not in ["", "nan", "-", "nada"]:
            return "Perdido"
        return "Em Andamento"

    df["Status_Calc"] = df.apply(status_calc, axis=1)
    return df

# ================= DASHBOARD =================
def dashboard(df):
    st.title("🚀 BI Expansão – Performance")

    total = len(df)
    ganhos = len(df[df["Status_Calc"] == "Ganho"])

    st.metric("Leads Totais", total)
    st.metric("Vendas", ganhos)

    # ===== GRÁFICO STATUS (CORRIGIDO) =====
    df_status = (
        df["Status_Calc"]
        .value_counts()
        .reset_index()
        .rename(columns={"index": "Status", "Status_Calc": "Quantidade"})
    )

    fig_status = px.bar(
        df_status,
        x="Status",
        y="Quantidade",
        text="Quantidade",
        title="Status dos Leads"
    )
    fig_status.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig_status, use_container_width=True)

    # ===== FUNIL =====
    ordem_funil = [
        "Sem resposta",
        "Aguardando Resposta",
        "Confirmou Interesse",
        "Qualificado",
        "Reunião Agendada",
        "Reunião Realizada",
        "Em aprovação",
        "Faturado"
    ]

    df_funil = (
        df["Etapa"]
        .value_counts()
        .reindex(ordem_funil)
        .fillna(0)
        .reset_index()
        .rename(columns={"index": "Etapa", "Etapa": "Quantidade"})
    )

    fig_funil = go.Figure(go.Funnel(
        y=df_funil["Etapa"],
        x=df_funil["Quantidade"],
        textinfo="value+percent initial"
    ))

    fig_funil.update_layout(
        title="Funil Comercial",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)"
    )

    st.plotly_chart(fig_funil, use_container_width=True)

    # ===== MOTIVOS DE PERDA =====
    df_loss = df[df["Status_Calc"] == "Perdido"]

    if not df_loss.empty:
        df_motivos = (
            df_loss["Motivo de Perda"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "Motivo", "Motivo de Perda": "Quantidade"})
        )

        fig_loss = px.bar(
            df_motivos,
            x="Quantidade",
            y="Motivo",
            orientation="h",
            text="Quantidade",
            title="Motivos de Perda"
        )

        fig_loss.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )

        st.plotly_chart(fig_loss, use_container_width=True)

# ================= APP =================
modo = st.radio("Modo:", ["Importar CSV", "Histórico"], horizontal=True)

if modo == "Importar CSV":
    file = st.file_uploader("Upload CSV", type="csv")
    if file:
        df = process_data(load_data(file))
        dashboard(df)

else:
    df_hist = carregar_historico()
    if not df_hist.empty:
        dashboard(df_hist)
    else:
        st.warning("Histórico vazio.")
