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
# CSS / HTML (OBRIGATÓRIO)
# =========================
st.markdown("""
<style>
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #1e293b;
    text-align: center;
}
.card-title {
    font-size: 14px;
    color: #94a3b8;
    text-transform: uppercase;
}
.card-value {
    font-size: 36px;
    font-weight: 700;
    color: #22d3ee;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
SEMANAS = ["Semana 1", "Semana 2", "Semana 3", "Semana 4"]
SPREADSHEET_NAME = "BI_CRM_EXPANSAO"
ABA_HISTORICO = "HISTORICO_KPIS"

# =========================
# COMPONENTES VISUAIS
# =========================
def card(title, value):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# GOOGLE SHEETS
# =========================
def conectar_google():
    info = json.loads(os.getenv("CREDENCIAIS_GOOGLE"))
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def salvar_dataframe(df, aba, append=False):
    gc = conectar_google()
    try:
        sh = gc.open(SPREADSHEET_NAME)
    except:
        sh = gc.create(SPREADSHEET_NAME)

    try:
        ws = sh.worksheet(aba)
    except:
        ws = sh.add_worksheet(title=aba, rows=2000, cols=50)

    if append and ws.get_all_values():
        ws.append_rows(df.values.tolist())
    else:
        ws.clear()
        ws.update([df.columns.tolist()] + df.values.tolist())

# =========================
# PROCESSAMENTO
# =========================
def processar(df):
    df.columns = df.columns.str.strip()
    df["Etapa"] = df["Etapa"].astype(str)
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str)

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors="coerce", dayfirst=True)

    def status(r):
        if "faturado" in r["Etapa"].lower():
            return "Ganho"
        if r["Motivo de Perda"].strip():
            return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(status, axis=1)
    return df

def filtrar_semana(df, semana):
    if "Data de Criação" not in df.columns:
        return df

    df["Semana"] = df["Data de Criação"].dt.day.apply(
        lambda d: "Semana 1" if d <= 7 else
                  "Semana 2" if d <= 14 else
                  "Semana 3" if d <= 21 else
                  "Semana 4"
    )
    return df[df["Semana"] == semana]

# =========================
# KPIs AGREGADOS (HISTÓRICO)
# =========================
def gerar_kpis(df, marca, semana):
    total = len(df)
    ganhos = len(df[df["Status"] == "Ganho"])
    perdidos = len(df[df["Status"] == "Perdido"])
    andamento = len(df[df["Status"] == "Em Andamento"])

    return pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Marca": marca,
        "Semana": semana,
        "Leads_Totais": total,
        "Em_Andamento": andamento,
        "Perdidos": perdidos,
        "Ganhos": ganhos
    }])

# =========================
# APP
# =========================
st.markdown("## BI CRM Expansão")

marca = st.selectbox("Marca", MARCAS)
semana = st.selectbox("Semana", SEMANAS)
arquivo = st.file_uploader("Upload CSV", type=["csv"])

if arquivo:
    df = pd.read_csv(arquivo, sep=None, engine="python")
    df = processar(df)
    df = filtrar_semana(df, semana)

    c1, c2, c3, c4 = st.columns(4)
    with c1: card("Leads Totais", len(df))
    with c2: card("Em Andamento", len(df[df["Status"] == "Em Andamento"]))
    with c3: card("Perdidos", len(df[df["Status"] == "Perdido"]))
    with c4: card("Ganhos", len(df[df["Status"] == "Ganho"]))

    if st.button("💾 Salvar Base + KPIs"):
        salvar_dataframe(df, f"{marca} - {semana}")
        kpis = gerar_kpis(df, marca, semana)
        salvar_dataframe(kpis, ABA_HISTORICO, append=True)
        st.success("Base e KPIs salvos com sucesso")

    st.dataframe(df, use_container_width=True)
