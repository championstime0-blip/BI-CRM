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
# CONSTANTES
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
SEMANAS = ["Semana 1", "Semana 2", "Semana 3", "Semana 4"]
SPREADSHEET_NAME = "BI_CRM_EXPANSAO"
ABA_HISTORICO = "HISTORICO_KPIS"

# =========================
# GOOGLE SHEETS
# =========================
def conectar_google_sheets():
    cred_json = os.getenv("CREDENCIAIS_GOOGLE")
    if not cred_json:
        raise ValueError("CREDENCIAIS_GOOGLE não configurada")

    info = json.loads(cred_json)
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(info, scopes=scopes)
    return gspread.authorize(creds)

def salvar_dataframe(df, aba_nome, append=False):
    gc = conectar_google_sheets()

    try:
        sh = gc.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(SPREADSHEET_NAME)

    try:
        ws = sh.worksheet(aba_nome)
        if not append:
            ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=aba_nome, rows=2000, cols=50)

    values = [df.columns.tolist()] + df.values.tolist()
    if append and ws.get_all_values():
        ws.append_rows(df.values.tolist())
    else:
        ws.update(values)

# =========================
# PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()

    mapa = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ["fonte", "origem", "source"]:
            mapa[c] = "Fonte"
        elif cl in ["etapa", "stage"]:
            mapa[c] = "Etapa"
        elif cl in ["motivo de perda", "loss reason"]:
            mapa[c] = "Motivo de Perda"
        elif cl in ["data de criação", "created date"]:
            mapa[c] = "Data de Criação"
        else:
            mapa[c] = c

    df = df.rename(columns=mapa)
    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str)

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors="coerce", dayfirst=True)

    def status(row):
        etapa = row["Etapa"].lower()
        motivo = row["Motivo de Perda"].lower()
        if "faturado" in etapa or "ganho" in etapa:
            return "Ganho"
        if motivo not in ["", "nan", "-", "none"]:
            return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(status, axis=1)
    return df

def filtrar_semana(df, semana):
    if "Data de Criação" not in df.columns:
        return df

    df = df.dropna(subset=["Data de Criação"]).copy()
    df["Semana"] = df["Data de Criação"].dt.day.apply(
        lambda d: "Semana 1" if d <= 7 else
                  "Semana 2" if d <= 14 else
                  "Semana 3" if d <= 21 else
                  "Semana 4"
    )
    return df[df["Semana"] == semana]

# =========================
# KPI AGREGADO
# =========================
def gerar_kpis(df, marca, semana):
    total = len(df)
    ganhos = len(df[df["Status"] == "Ganho"])
    perdidos = len(df[df["Status"] == "Perdido"])
    andamento = len(df[df["Status"] == "Em Andamento"])

    sem_resposta = len(df[
        (df["Etapa"] == "Aguardando Resposta") &
        (df["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))
    ])

    avancados = len(df[df["Etapa"].isin([
        "Qualificado", "Reunião Agendada", "Reunião Realizada",
        "Follow-up", "negociação", "em aprovação", "faturado"
    ])])

    base = total - sem_resposta
    taxa_avanco = round((avancados / base * 100), 1) if base > 0 else 0

    return pd.DataFrame([{
        "Data_Salvamento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Marca": marca,
        "Semana": semana,
        "Leads_Totais": total,
        "Em_Andamento": andamento,
        "Perdidos": perdidos,
        "Ganhos": ganhos,
        "Taxa_Avanco_%": taxa_avanco,
        "Sem_Resposta": sem_resposta
    }])

# =========================
# APP
# =========================
st.title("BI CRM Expansão")

marca = st.selectbox("Marca", MARCAS)
semana = st.selectbox("Semana", SEMANAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    df = load_csv(arquivo)
    df = processar(df)
    df = filtrar_semana(df, semana)

    if st.button("💾 Salvar Base + KPIs"):
        # Base detalhada
        salvar_dataframe(df, f"{marca} - {semana}")

        # KPI agregado
        kpis = gerar_kpis(df, marca, semana)
        salvar_dataframe(kpis, ABA_HISTORICO, append=True)

        st.success("Base e KPIs salvos com sucesso")

    st.dataframe(df, use_container_width=True)
