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

# ================= CONFIG =================
st.set_page_config(page_title="BI Expansão Performance", layout="wide")

st.markdown("""
<style>
.stApp { background-color: #0e1117; color: white; }
h1,h2,h3,h4 { color: white; }
</style>
""", unsafe_allow_html=True)

# ================= GOOGLE SHEETS =================
def conectar_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds).open("BI_Historico").sheet1

def salvar_no_gsheets(df, marca):
    sheet = conectar_gsheets()
    df = df.copy()
    df["marca"] = marca
    df["data_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_rows(df.fillna("").astype(str).values.tolist())

def carregar_historico():
    return pd.DataFrame(conectar_gsheets().get_all_records())

# ================= CSV =================
def load_data(file):
    raw = file.getvalue()
    for enc in ["utf-8-sig", "latin-1", "iso-8859-1"]:
        try:
            txt = raw.decode(enc)
            sep = ";" if ";" in txt.splitlines()[0] else ","
            return pd.read_csv(io.StringIO(txt), sep=sep)
        except:
            pass
    return pd.DataFrame()

def processar_rd(df):
    df.columns = [c.strip() for c in df.columns]

    col_etapa = next(c for c in df.columns if "etapa" in c.lower() or "stage" in c.lower())
    col_motivo = next((c for c in df.columns if "motivo" in c.lower()), None)
    col_data = next(c for c in df.columns if "created" in c.lower() or "data" in c.lower())

    df["Etapa"] = df[col_etapa]
    df["Motivo de Perda"] = df[col_motivo] if col_motivo else ""
    df["Data_Criacao"] = pd.to_datetime(df[col_data], errors="coerce")

    def status(row):
        etapa = str(row["Etapa"]).lower()
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if "venda" in etapa or "ganho" in etapa or "faturado" in etapa:
            return "Ganho"
        if motivo not in ["", "nan"]:
            return "Perdido"
        return "Em Andamento"

    df["Status_Calc"] = df.apply(status, axis=1)
    return df

# ================= DASHBOARD =================
def dashboard(df):
    total = len(df)
    ganhos = len(df[df["Status_Calc"] == "Ganho"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Leads", total)
    c2.metric("Vendas", ganhos)
    c3.metric("Conversão", f"{(ganhos/total*100):.1f}%" if total else "0%")

    # ===== STATUS =====
    df_status = (
        df["Status_Calc"]
        .value_counts()
        .reset_index(name="Qtd")
        .rename(columns={"index": "Status_Calc"})
    )

    fig_status = px.bar(
        df_status,
        x="Status_Calc",
        y="Qtd",
        title="Status dos Leads"
    )
    st.plotly_chart(fig_status, use_container_width=True)

    # ===== FUNIL =====
    ordem = [
        "Sem resposta",
        "Aguardando Resposta",
        "Confirmou Interesse",
        "Qualificado",
        "Reunião Agendada",
        "Reunião Realizada",
        "Venda/Fechamento"
    ]

    df_funil = (
        df["Etapa"]
        .value_counts()
        .reindex(ordem)
        .fillna(0)
        .reset_index(name="Qtd")
        .rename(columns={"index": "Etapa"})
    )

    fig_funil = go.Figure(go.Funnel(
        y=df_funil["Etapa"],
        x=df_funil["Qtd"],
        textinfo="value+percent initial"
    ))
    st.plotly_chart(fig_funil, use_container_width=True)

    # ===== MOTIVOS DE PERDA =====
    perdas = df[df["Status_Calc"] == "Perdido"]
    if not perdas.empty:
        df_motivos = (
            perdas["Motivo de Perda"]
            .value_counts()
            .reset_index(name="Qtd")
            .rename(columns={"index": "Motivo"})
        )

        fig_loss = px.bar(
            df_motivos,
            x="Qtd",
            y="Motivo",
            orientation="h",
            title="Motivos de Perda"
        )
        st.plotly_chart(fig_loss, use_container_width=True)

# ================= APP =================
st.title("🚀 BI Expansão – RD Station")

marca = st.sidebar.selectbox(
    "Marca",
    ["Prepara IA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
)

modo = st.sidebar.radio("Modo", ["Importar", "Histórico"])

if modo == "Importar":
    file = st.file_uploader("Upload RD Station CSV", type="csv")
    if file:
        df = processar_rd(load_data(file))
        if st.sidebar.button("Salvar no Histórico"):
            salvar_no_gsheets(df, marca)
            st.success("Salvo com sucesso")
        dashboard(df)

else:
    df = carregar_historico()
    df = df[df["marca"] == marca]
    dashboard(df)
