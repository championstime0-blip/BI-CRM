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
# ESTILIZAÇÃO CSS (FRONT ORIGINAL - NÃO ALTERADO)
# =========================
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
/* TODO O SEU CSS ORIGINAL — SEM ALTERAÇÃO */
</style>""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
ETAPAS_FUNIL = [
    "Sem contato","Aguardando Resposta","Confirmou Interesse","Qualificado",
    "Reunião Agendada","Reunião Realizada","Follow-up","negociação","em aprovação","faturado"
]
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]

# =========================
# FUNÇÕES VISUAIS (INALTERADAS)
# =========================
def card(title, value):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f"""
    <div class="futuristic-sub">
        <span class="sub-icon">{icon}</span>{text}
    </div>
    """, unsafe_allow_html=True)

# =========================
# MOTOR DE DADOS (INALTERADO)
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    df["Etapa"] = df["Etapa"].astype(str)
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str)
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors="coerce")
    def status(r):
        if "faturado" in r["Etapa"].lower():
            return "Ganho"
        if r["Motivo de Perda"].strip():
            return "Perdido"
        return "Em Andamento"
    df["Status"] = df.apply(status, axis=1)
    return df

# =========================
# BACK-END (NOVO — ISOLADO)
# =========================
def gerar_kpis_agregados(df, marca):
    return pd.DataFrame([{
        "Data": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Marca": marca,
        "Leads Totais": len(df),
        "Ganhos": len(df[df["Status"] == "Ganho"]),
        "Perdidos": len(df[df["Status"] == "Perdido"]),
        "Em Andamento": len(df[df["Status"] == "Em Andamento"])
    }])

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
    ws.update([df.columns.tolist()] + df.values.tolist())

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
        st.success("Dados e KPIs salvos com sucesso")
