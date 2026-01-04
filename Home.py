import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# ESTILIZAÇÃO CSS
# =========================
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
</style>""", unsafe_allow_html=True)

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
# FUNÇÕES VISUAIS
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
# MOTOR BLINDADO (CORREÇÕES AQUI)
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    df = pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")
    df = df.loc[:, ~df.columns.duplicated()].copy()
    return df

def processar(df):
    df.columns = df.columns.astype(str).str.strip()

    cols_map = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ["fonte","origem","source","conversion origin","origem do lead"]:
            cols_map[c] = "Fonte"
        elif cl in ["data de criação","data da criação","created date"]:
            cols_map[c] = "Data de Criação"
        elif cl in ["dono do lead","responsável","responsavel","owner"]:
            cols_map[c] = "Responsável"
        elif cl in ["equipe","equipe do dono do lead","team"]:
            cols_map[c] = "Equipe"
        elif "etapa" in cl:
            cols_map[c] = "Etapa"
        elif "motivo" in cl:
            cols_map[c] = "Motivo de Perda"

    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # --- GARANTIA DE COLUNAS CRÍTICAS ---
    for col in ["Etapa","Motivo de Perda","Fonte","Responsável","Equipe"]:
        if col not in df.columns:
            df[col] = ""
        if isinstance(df[col], pd.DataFrame):
            df[col] = df[col].iloc[:, 0]
        df[col] = df[col].astype(str).fillna("").str.strip()

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(
            df["Data de Criação"], errors="coerce", dayfirst=True
        )

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
# DASHBOARD (INALTERADO)
# =========================
def dashboard(df, marca):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]

    perda_especifica = df[
        (df["Etapa"].str.strip() == "Aguardando Resposta") &
        (df["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))
    ]

    c1, c2 = st.columns(2)
    with c1: card("Leads Totais", total)
    with c2: card("Leads em Andamento", len(em_andamento))

    st.divider()

    col_mkt, col_funil = st.columns(2)

    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        df_fonte = df["Fonte"].value_counts().reset_index()
        df_fonte.columns = ["Fonte","Qtd"]
        fig = px.pie(df_fonte, values="Qtd", names="Fonte", hole=0.6)
        fig.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL")
        df_funil = df.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
        fig = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h")
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    subheader_futurista("🚫", "DETALHE DAS PERDAS")
    k1, k2 = st.columns(2)
    with k1: card("Total Perdido", len(perdidos))
    with k2: card("Sem Resposta", len(perda_especifica))

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = load_csv(arquivo)
        df = processar(df)

        resp_val = df["Responsável"].mode().iloc[0] if not df["Responsável"].mode().empty else "Não Identificado"
        equipe_raw = df["Equipe"].mode().iloc[0] if not df["Equipe"].mode().empty else "Geral"
        equipe_val = "Expansão Ensina Mais" if equipe_raw in ["","nan","Geral"] else equipe_raw

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group">
                <span class="profile-label">Responsável</span>
                <span class="profile-value">{resp_val}</span>
            </div>
            <div class="profile-divider"></div>
            <div class="profile-group">
                <span class="profile-label">Equipe do Responsável</span>
                <span class="profile-value">{equipe_val}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        dashboard(df, marca)

    except Exception as e:
        st.error("Erro ao processar o arquivo")
        st.exception(e)
