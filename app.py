import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURAÇÃO
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# CSS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@500;700&display=swap');

.stApp { background-color:#0b0f1a; color:#e5e7eb; }

.futuristic-title{
    font-family:'Orbitron';
    font-size:52px;
    font-weight:900;
    background:linear-gradient(90deg,#22d3ee,#818cf8,#c084fc);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    margin-bottom:20px;
}

.futuristic-sub{
    font-family:'Rajdhani';
    font-size:22px;
    font-weight:700;
    text-transform:uppercase;
    border-bottom:1px solid #1e293b;
    margin:30px 0 15px 0;
}

.card{
    background:linear-gradient(135deg,#020617,#111827);
    border:1px solid #1e293b;
    border-radius:14px;
    padding:22px;
    text-align:center;
}

.card-title{
    font-size:13px;
    color:#94a3b8;
    text-transform:uppercase;
    margin-bottom:6px;
}

.card-value{
    font-family:'Orbitron';
    font-size:34px;
    background:linear-gradient(45deg,#38bdf8,#818cf8);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}

.profile-header{
    background:#020617;
    border-left:4px solid #6366f1;
    padding:20px;
    border-radius:8px;
    margin-bottom:20px;
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

MARCAS = ["PreparaIA","Microlins","Ensina Mais 1","Ensina Mais 2"]

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

def subheader(txt):
    st.markdown(f"<div class='futuristic-sub'>{txt}</div>", unsafe_allow_html=True)

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

    rename = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ["fonte","origem","source","conversion origin"]:
            rename[c] = "Fonte"
        if cl in ["data de criação","created date"]:
            rename[c] = "Data de Criação"
        if cl in ["responsável","owner","dono do lead"]:
            rename[c] = "Responsável"
        if cl in ["equipe","team"]:
            rename[c] = "Equipe"

    df = df.rename(columns=rename)

    if "Motivo de Perda" not in df.columns:
        df["Motivo de Perda"] = ""

    df["Etapa"] = df["Etapa"].astype(str).str.strip().str.lower()
    df["Motivo de Perda"] = df["Motivo de Perda"].astype(str)

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors="coerce")

    def status(row):
        if "faturado" in row["Etapa"]:
            return "Ganho"
        if row["Motivo de Perda"].strip():
            return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(status, axis=1)
    return df

# =========================
# DASHBOARD
# =========================
def dashboard(df):
    total = len(df)
    perdidos = df[df["Status"]=="Perdido"]
    andamento = df[df["Status"]=="Em Andamento"]

    c1,c2,c3 = st.columns(3)
    with c1: card("Leads Totais", total)
    with c2: card("Em Andamento", len(andamento))
    with c3: card("Leads Perdidos", len(perdidos))

    subheader("Marketing & Fontes")
    if "Fonte" in df.columns:
        fonte = df["Fonte"].value_counts().reset_index()
        fonte.columns = ["Fonte","Qtd"]
        fig = px.pie(fonte, values="Qtd", names="Fonte", hole=0.55)
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    subheader("Funil de Conversão")
    funil = df.groupby("Etapa").size().reindex([e.lower() for e in ETAPAS_FUNIL]).fillna(0).reset_index(name="Qtd")
    fig2 = px.bar(funil, x="Qtd", y="Etapa", orientation="h")
    fig2.update_layout(template="plotly_dark")
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# APP
# =========================
st.markdown("<div class='futuristic-title'>BI CRM Expansão</div>", unsafe_allow_html=True)

marca = st.selectbox("Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type="csv")

if arquivo:
    df = processar(load_csv(arquivo))
    dashboard(df)
