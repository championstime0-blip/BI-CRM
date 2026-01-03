import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import gspread
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
# GOOGLE SHEETS AUTH
# =====================================================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "service_account.json",
    scopes=SCOPES
)

gc = gspread.authorize(creds)

SPREADSHEET = "BI_Historico"
WORKSHEET = "HISTORICO_LEADS"

# =====================================================
# UTILIDADES
# =====================================================
FUNIL_ORDEM = [
    "Sem resposta",
    "Aguardando Resposta",
    "Confirmou Interesse",
    "Qualificado",
    "Reunião Agendada",
    "Reunião Realizada",
    "Follow-up",
    "Negociação",
    "Em aprovação",
    "Faturado"
]

SONDAGEM_COLS = [
    "Atuação",
    "Cidade Interesse",
    "Prazo",
    "Investimento",
    "Capital de Investimento"
]

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
    df.columns = df.columns.str.strip()

    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # STATUS CALC
    if "Status_Calc" not in df.columns:
        df["Status_Calc"] = "Em Andamento"

    df.loc[df["Etapa"].str.lower() == "faturado", "Status_Calc"] = "Ganho"
    df.loc[
        (df.get("Estado", "") == "Perdida") |
        (df.get("Motivo de Perda", "") != ""),
        "Status_Calc"
    ] = "Perdido"

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
# FUNIL
# =====================================================
def plot_funil(df):
    etapas = []
    valores = []

    for etapa in FUNIL_ORDEM:
        etapas.append(etapa)
        valores.append((df["Etapa"] == etapa).sum())

    fig = go.Figure(go.Funnel(
        y=etapas,
        x=valores,
        textinfo="value+percent initial"
    ))

    fig.update_layout(
        paper_bgcolor="black",
        plot_bgcolor="black",
        font_color="white"
    )

    return fig

# =====================================================
# MOTIVOS DE PERDA
# =====================================================
def plot_motivos(df):
    perdas = df[df["Status_Calc"] == "Perdido"]
    motivos = perdas["Motivo de Perda"].value_counts()

    fig = go.Figure(go.Bar(
        x=motivos.values,
        y=motivos.index,
        orientation="h"
    ))

    fig.update_layout(
        paper_bgcolor="black",
        plot_bgcolor="black",
        font_color="white"
    )

    return fig

# =====================================================
# UI
# =====================================================
modo = st.radio(
    "Selecione o Modo:",
    ["📥 Importar Planilha", "📊 Dashboard BI"],
    horizontal=True
)

df_db, ws = load_db()

if df_db.empty:
    seed_if_empty(ws)
    df_db, _ = load_db()

df_db = normalize(df_db)

# =====================================================
# IMPORTAÇÃO CSV
# =====================================================
if modo == "📥 Importar Planilha":

    file = st.file_uploader("Upload CSV", type=["csv"])

    if file:
        df_csv = pd.read_csv(file, sep=None, engine="python", encoding="utf-8-sig")
        df_csv = normalize(df_csv)

        # DEDUPLICAÇÃO
        if "Telefone" in df_csv.columns:
            df_csv = df_csv.drop_duplicates(subset=["Telefone"])

        for _, row in df_csv.iterrows():
            ws.append_row(row.tolist())

        st.success("Importação concluída com sucesso!")

# =====================================================
# DASHBOARD BI
# =====================================================
else:
    total, ganhos, perdas, conv = kpis(df_db)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", total)
    c2.metric("Ganhos", ganhos)
    c3.metric("Perdas", perdas)
    c4.metric("Conversão (%)", f"{conv:.2f}%")

    st.divider()

    st.plotly_chart(plot_funil(df_db), use_container_width=True)

    st.divider()

    st.subheader("📉 Motivos de Perda")
    st.plotly_chart(plot_motivos(df_db), use_container_width=True)

    st.divider()

    st.subheader("📄 Base Completa")
    st.dataframe(df_db, use_container_width=True)
