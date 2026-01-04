import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# CSS Futurista (Idêntico ao seu anterior)
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
# MOTOR DE PROCESSAMENTO
# =========================
def processar(arquivo_bruto):
    # Lendo o CSV com encoding correto para o RD Station
    df = pd.read_csv(arquivo_bruto, sep=';', encoding='latin-1', on_bad_lines='skip')
    
    # --- SOLUÇÃO DO ERRO 'str': REMOVE COLUNAS DUPLICADAS ---
    # Isso mantém apenas a primeira versão de colunas como 'Cargo' ou 'Email'
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Mapeamento para garantir nomes amigáveis
    mapeamento = {}
    for c in df.columns:
        c_low = str(c).lower()
        if "fonte" in c_low: mapeamento[c] = "Fonte"
        elif "data de cri" in c_low: mapeamento[c] = "Data de Criação"
        elif "responsavel" in c_low or "responsÃ¡vel" in c_low: mapeamento[c] = "Responsável"
        elif "equipe" in c_low: mapeamento[c] = "Equipe"
        elif "etapa" in c_low: mapeamento[c] = "Etapa"
        elif "motivo de perda" in c_low: mapeamento[c] = "Motivo de Perda"
    
    df = df.rename(columns=mapeamento)

    # Limpeza de caracteres especiais (Ã£ -> ã, Ã¡ -> á)
    for col in ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte"]:
        if col in df.columns:
            # Forçamos a conversão para string e limpamos a codificação
            df[col] = df[col].astype(str).str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável").fillna("N/A")

    def definir_status(row):
        etapa = str(row.get("Etapa", "")).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada"]: return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(definir_status, axis=1)
    return df

# =========================
# APP INTERFACE
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

st.sidebar.header("⚙️ Configurações")
marca = st.sidebar.selectbox("Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
semana_ref = st.sidebar.selectbox("Semana de Referência", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"])

arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(arquivo)
        
        # --- CARDS DE PERFIL ---
        resp_v = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        equipe_v = df["Equipe"].iloc[0] if "Equipe" in df.columns else "Geral"

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_v}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_v}</span></div>
        </div>
        """, unsafe_allow_html=True)

        total = len(df)
        andamento = len(df[df["Status"] == "Em Andamento"])
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Andamento</div><div class="card-value">{andamento}</div></div>', unsafe_allow_html=True)

        # Gráfico de Perdas
        st.divider()
        st.markdown("### 🚫 DETALHE DAS PERDAS")
        perdidos = df[df["Status"] == "Perdido"]
        if not perdidos.empty:
            df_loss = perdidos.groupby("Etapa").size().reset_index(name="Qtd")
            fig_loss = px.bar(df_loss, x="Etapa", y="Qtd", color="Qtd", color_continuous_scale="Purples", text_auto=True)
            fig_loss.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_loss, use_container_width=True)

        # Botão Salvar (Lógica para Render)
        st.sidebar.markdown("---")
        if st.sidebar.button(f"🚀 SALVAR DADOS: {semana_ref}"):
            # Aqui entraria a conexão com o gspread que configuramos antes
            st.sidebar.success(f"✅ Dados de {marca} prontos para salvar!")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
