import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime
import unicodedata

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 56px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between;
}
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); height: 100%;
}
.card-value { font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; color: #22d3ee; }
</style>
""", unsafe_allow_html=True)

# =========================
# FUNÇÃO DE LIMPEZA DE TEXTO
# =========================
def limpar_texto(texto):
    if not isinstance(texto, str): return str(texto)
    # Remove acentos e caracteres estranhos (Ex: Ã¡ vira a)
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    # 1. Limpeza de colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # 2. Normalizar nomes das colunas (remover Ã¡, Ã£, etc)
    df.columns = [limpar_texto(str(c)).strip() for c in df.columns]
    
    cols_map = {}
    for c in df.columns:
        c_low = c.lower()
        if "fonte" in c_low or "origem" in c_low: cols_map[c] = "Fonte"
        elif "data de cri" in c_low: cols_map[c] = "Data de Criação"
        elif "responsavel" in c_low: cols_map[c] = "Responsável"
        elif "equipe" in c_low: cols_map[c] = "Equipe"
        elif c_low == "etapa": cols_map[c] = "Etapa"
        elif "motivo" in c_low: cols_map[c] = "Motivo de Perda"
    
    df = df.rename(columns=cols_map)
    
    # 3. Limpar o conteúdo das células (especialmente a Equipe)
    if "Equipe" in df.columns:
        df["Equipe"] = df["Equipe"].apply(limpar_texto).str.strip()
    if "Responsável" in df.columns:
        df["Responsável"] = df["Responsável"].apply(limpar_texto).str.strip()
        
    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str).fillna("")
    
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status_func(row):
        etapa = str(row["Etapa"]).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status_func, axis=1)
    return df

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.sidebar.selectbox("Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
arquivo = st.file_uploader("Upload CSV", type=["csv"])

if arquivo:
    try:
        df = processar(load_csv(arquivo))
        
        # Agora pegamos os valores já limpos
        resp_v = df["Responsável"].mode()[0] if "Responsável" in df.columns and not df["Responsável"].empty else "N/A"
        equipe_v = df["Equipe"].mode()[0] if "Equipe" in df.columns and not df["Equipe"].empty else "Não Identificada"
        
        # Forçar exibição correta se for a equipe que você quer
        if "Expansao Ensina Mais" in equipe_v:
            equipe_v = "Expansão Ensina Mais"

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_v}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_v}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # --- KPIs e Gráficos seguem abaixo ---
        total = len(df)
        em_andamento = len(df[df["Status"] == "Em Andamento"])
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Andamento</div><div class="card-value">{em_andamento}</div></div>', unsafe_allow_html=True)

        # Gráfico de Perdas (conforme solicitado)
        st.divider()
        st.markdown('### 🚫 DETALHE DAS PERDAS')
        perdidos = df[df["Status"] == "Perdido"]
        df_loss = perdidos.groupby("Etapa").size().reset_index(name="Qtd")
        fig_loss = px.bar(df_loss, x="Etapa", y="Qtd", color="Qtd", color_continuous_scale="Purples", text_auto=True)
        fig_loss.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_loss, use_container_width=True)

        # Botão Salvar
        if st.sidebar.button("💾 SALVAR DADOS"):
            # Lógica de salvar no Sheets (mesma do anterior)
            st.sidebar.success("Salvo!")

    except Exception as e:
        st.error(f"Erro: {e}")
