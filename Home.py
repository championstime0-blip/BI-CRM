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

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 56px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 3px; margin-bottom: 10px; text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
}
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); height: 100%;
}
.card-value { font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; color: #22d3ee; }
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def processar(arquivo_bruto):
    # Lendo com encoding correto para evitar Ã£ e Ã¡
    df = pd.read_csv(arquivo_bruto, sep=';', encoding='latin-1', on_bad_lines='skip')
    
    # 1. Limpeza de colunas duplicadas e nomes
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    cols_map = {}
    for c in df.columns:
        c_low = str(c).lower()
        if "fonte" in c_low: cols_map[c] = "Fonte"
        elif "data de criacao" in c_low or "data de cri" in c_low: cols_map[c] = "Data de Criação"
        elif "responsavel" in c_low and "equipe" not in c_low: cols_map[c] = "Responsável"
        elif "equipe" in c_low: cols_map[c] = "Equipe"
        elif "etapa" in c_low: cols_map[c] = "Etapa"
        elif "motivo de perda" in c_low: cols_map[c] = "Motivo de Perda"
    
    df = df.rename(columns=cols_map)

    # 2. Forçar limpeza de texto nas colunas principais para remover erros de encoding residuais
    for col in ["Responsável", "Equipe", "Etapa", "Motivo de Perda"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.encode('latin-1').str.decode('utf-8', errors='ignore').fillna("N/A")
            # Correção manual para o caso específico da Equipe
            df[col] = df[col].str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável")

    # 3. Lógica de Status
    def definir_status(row):
        etapa = str(row.get("Etapa", "")).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "nada", "0"]: return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(definir_status, axis=1)
    return df

# =========================
# APP INTERFACE
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.sidebar.selectbox("Selecione a Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(arquivo)
        
        # --- HEADER DE PERFIL ---
        resp_v = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        equipe_v = df["Equipe"].iloc[0] if "Equipe" in df.columns else "Geral"

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_v}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_v}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # --- KPIs ---
        total = len(df)
        andamento = len(df[df["Status"] == "Em Andamento"])
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Em Andamento</div><div class="card-value">{andamento}</div></div>', unsafe_allow_html=True)

        # --- DETALHE DAS PERDAS ---
        st.markdown('<div class="futuristic-sub">🚫 DETALHE DAS PERDAS</div>', unsafe_allow_html=True)
        perdidos = df[df["Status"] == "Perdido"]
        if not perdidos.empty:
            df_loss = perdidos.groupby("Etapa").size().reset_index(name="Qtd")
            fig_loss = px.bar(df_loss, x="Etapa", y="Qtd", color="Qtd", color_continuous_scale="Blues", text_auto=True)
            fig_loss.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_loss, use_container_width=True)
        else:
            st.info("Nenhuma perda registrada no período.")

        # --- BOTÃO SALVAR ---
        if st.sidebar.button("🚀 SALVAR HISTÓRICO"):
            # Lógica de conexão com Google Sheets deve vir aqui
            st.sidebar.success("Dados prontos para envio!")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
