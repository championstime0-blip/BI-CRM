import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# CSS / FRONT (ORIGINAL — PRESERVADO)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 56px;
    font-weight: 900;
    text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #1e293b;
    text-align: center;
}
.card-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    color: #94a3b8;
    text-transform: uppercase;
}
.card-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 36px;
    color: #22d3ee;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
ETAPAS_FUNIL = [
    "Sem contato","Aguardando Resposta","Confirmou Interesse",
    "Qualificado","Reunião Agendada","Reunião Realizada",
    "Follow-up","negociação","em aprovação","faturado"
]

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]

# =========================
# FUNÇÕES VISUAIS
# =========================
def card(title, value):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# LOAD & PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors="coerce", dayfirst=True)

    df["Etapa"] = df.get("Etapa", "").astype(str)
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str)

    def status(row):
        etapa = row["Etapa"].lower()
        if "faturado" in etapa or "ganho" in etapa:
            return "Ganho"
        if row["Motivo de Perda"].strip():
            return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(status, axis=1)
    return df

# =========================
# DASHBOARD (FUNÇÃO QUE FALTAVA)
# =========================
def dashboard(df, marca):
    total = len(df)
    ganhos = len(df[df["Status"] == "Ganho"])
    perdidos = len(df[df["Status"] == "Perdido"])
    andamento = len(df[df["Status"] == "Em Andamento"])

    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Leads Totais", total)
    with c2: card("Ganhos", ganhos)
    with c3: card("Perdidos", perdidos)
    with c4: card("Em Andamento", andamento)

    st.divider()

    df_funil = df.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
    fig = px.bar(
        df_funil,
        x="Qtd",
        y="Etapa",
        orientation="h",
        color="Qtd",
        color_continuous_scale="Blues"
    )
    fig.update_layout(template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

# =========================
# GOOGLE SHEETS (BACKEND)
# =========================
def conectar_google():
    info = json.loads(os.getenv("CREDENCIAIS_GOOGLE"))
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def salvar_df(df, aba):
    gc = conectar_google()
    sh = gc.open("BI_CRM_EXPANSAO")
    try:
        ws = sh.worksheet(aba)
    except:
        ws = sh.add_worksheet(title=aba, rows=2000, cols=50)
    ws.clear()
    ws.update([df.columns.tolist()] + df.astype(str).values.tolist())

def gerar_kpis_agregados(df, marca):
    return pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Marca": marca,
        "Leads Totais": len(df),
        "Ganhos": len(df[df["Status"] == "Ganho"]),
        "Perdidos": len(df[df["Status"] == "Perdido"]),
        "Em Andamento": len(df[df["Status"] == "Em Andamento"])
    }])

# =========================
# APP
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    df = processar(load_csv(arquivo))
    dashboard(df, marca)

    if st.button("💾 Salvar Base + KPIs"):
        salvar_df(df, f"{marca}_BASE")
        salvar_df(gerar_kpis_agregados(df, marca), "HISTORICO_KPIS")
        st.success("Dados salvos com sucesso")
