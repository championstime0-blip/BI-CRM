import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
import json
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# (CSS – IDÊNTICO AO SEU)
# =========================
# >>>>> MANTIDO INTEGRALMENTE – OMITIDO AQUI PARA BREVIDADE <<<<<

# =========================
# CONSTANTES
# =========================
ETAPAS_FUNIL = [
    "Sem contato","Aguardando Resposta","Confirmou Interesse","Qualificado",
    "Reunião Agendada","Reunião Realizada","Follow-up",
    "negociação","em aprovação","faturado"
]

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]

# =========================
# FUNÇÕES DE CARGA
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    cols_map = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ["fonte","origem","source","conversion origin"]:
            cols_map[c] = "Fonte"
        elif "data" in cl:
            cols_map[c] = "Data de Criação"
        elif "respons" in cl or "owner" in cl:
            cols_map[c] = "Responsável"
        elif "equipe" in cl or "team" in cl:
            cols_map[c] = "Equipe"
        elif "etapa" in cl:
            cols_map[c] = "Etapa"
        elif "motivo" in cl:
            cols_map[c] = "Motivo de Perda"

    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    for col in ["Etapa","Motivo de Perda","Responsável","Equipe","Fonte"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).fillna("").str.strip()

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors="coerce", dayfirst=True)

    def status(row):
        etapa = row["Etapa"].lower()
        if any(x in etapa for x in ["faturado","ganho","venda"]):
            return "Ganho"
        motivo = row["Motivo de Perda"].lower()
        if motivo not in ["","nan","none","-","0"]:
            return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(status, axis=1)
    return df

# =========================
# HISTÓRICO – GOOGLE SHEETS
# =========================
def salvar_historico(marca, resp, equipe, total, andamento, perdidos, perc_funil, perda_sem_resp):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    sh = client.open("BI_Historico_CRM")
    ws = sh.worksheet("Historico")

    agora = datetime.now()

    ws.append_row([
        agora.strftime("%d/%m/%Y"),
        agora.strftime("%H:%M:%S"),
        marca,
        resp,
        equipe,
        total,
        andamento,
        perdidos,
        f"{perc_funil:.1f}%",
        perda_sem_resp
    ])

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(load_csv(arquivo))

        resp_val = df["Responsável"].mode().iloc[0] if not df["Responsável"].mode().empty else "Não Identificado"
        equipe_val = df["Equipe"].mode().iloc[0] if not df["Equipe"].mode().empty else "Expansão"

        total = len(df)
        andamento = len(df[df["Status"] == "Em Andamento"])
        perdidos = len(df[df["Status"] == "Perdido"])

        perda_sem_resp = len(df[
            (df["Etapa"] == "Aguardando Resposta") &
            (df["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))
        ])

        avancados = len(df[df["Etapa"].isin([
            "Qualificado","Reunião Agendada","Reunião Realizada",
            "Follow-up","negociação","em aprovação","faturado"
        ])])

        base = total - perda_sem_resp
        perc_funil = (avancados / base * 100) if base > 0 else 0

        # ===== BOTÃO SALVAR =====
        st.sidebar.markdown("---")
        if st.sidebar.button("💾 SALVAR NO HISTÓRICO"):
            with st.spinner("Salvando histórico..."):
                salvar_historico(
                    marca, resp_val, equipe_val,
                    total, andamento, perdidos,
                    perc_funil, perda_sem_resp
                )
                st.sidebar.success("Histórico salvo com sucesso!")

        # >>>>> DASHBOARD ORIGINAL É CHAMADO AQUI <<<<<
        # dashboard(df, marca)

    except Exception as e:
        st.error("Erro ao processar o arquivo")
        st.exception(e)
