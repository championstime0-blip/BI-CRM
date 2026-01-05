import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime
import io

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (IDENTIDADE ORIGINAL)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 56px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 3px; margin-bottom: 10px; text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px; display: flex; align-items: center;
}
.sub-icon { margin-right: 12px; font-size: 24px; color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.6); }
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.profile-group { display: flex; flex-direction: column; }
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); transition: all 0.3s ease; height: 100%;
}
.card:hover { box-shadow: 0 0 25px rgba(56,189,248,0.2); border-color: #38bdf8; transform: translateY(-2px); }
.card-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; min-height: 30px; display: flex; align-items: center; justify-content: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.top-item {
    border-left: 3px solid #22d3ee; padding: 12px 15px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: space-between;
    transition: transform 0.2s; border: 1px solid rgba(34, 211, 238, 0.1); border-left-width: 3px; background: rgba(30, 41, 59, 0.5);
}
.top-rank { font-family: 'Orbitron', sans-serif; font-weight: 900; color: #22d3ee; font-size: 16px; margin-right: 12px; }
.top-name { font-family: 'Rajdhani', sans-serif; color: #f1f5f9; font-weight: 600; font-size: 14px; flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top-val-abs { font-family: 'Orbitron', sans-serif; color: #fff; font-weight: bold; font-size: 14px; margin-left: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES & CONEXÃO
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
MOTIVOS_PERDA_MESTRADOS = ["Sem Resposta", "Sem Capital", "Desistiu do Negócio", "Outro Investimento", "Fora de Perfil", "Não tem interesse em franquia", "Lead Duplicado", "Dados Inválidos", "Região Indisponível", "Sócio não aprovou"]

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        if not creds_json:
             creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
             return gspread.authorize(creds)
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    if raw.strip().startswith("sep="):
        raw = "\n".join(raw.splitlines()[1:])
    sep = ";" if raw.count(";") > raw.count(",") else ","
    return pd.read_csv(io.StringIO(raw), sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    cols_map = {}
    for c in df.columns:
        c_lower = str(c).lower()
        if "fonte" in c_lower and "utm" not in c_lower: cols_map[c] = "Fonte"
        elif "data de cri" in c_lower: cols_map[c] = "Data de Criação"
        elif "respons" in c_lower and "equipe" not in c_lower: cols_map[c] = "Responsável"
        elif "equipes do respons" in c_lower or "equipe" in c_lower: cols_map[c] = "Equipe"
        elif "motivo de perda" in c_lower: cols_map[c] = "Motivo de Perda"
        elif "etapa" in c_lower: cols_map[c] = "Etapa"
        elif "campanha" in c_lower: cols_map[c] = "Campanha"
        elif c_lower == "estado": cols_map[c] = "Estado"

    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()]

    colunas_texto = ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte", "Campanha", "Estado"]
    for col in colunas_texto:
        if col in df.columns:
            if isinstance(df[col], pd.DataFrame): df[col] = df[col].iloc[:, 0]
            df[col] = df[col].astype(str).str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável").fillna("N/A").str.strip()
        else:
            df[col] = "N/A"

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status_func(row):
        estado_lower = str(row.get("Estado", "")).lower()
        if estado_lower == "perdida": return "Perdido"
        etapa_lower = str(row["Etapa"]).lower()
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status_func, axis=1)
    return df

# =========================
# DASHBOARD LOGIC
# =========================
def render_dashboard(df, marca):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    c1, c2 = st.columns(2)
    with c1: card("Leads Totais", total)
    with c2: card("Leads em Andamento", len(em_andamento))
    st.divider()

    col_mkt, col_funil = st.columns(2)
    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, 
                             color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2', '#1e293b'])
            fig_pie.update_traces(textposition='inside', textinfo='label+value')
            fig_pie.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL (ACUMULADO)")
        ordem_funil = ["Confirmou Interesse", "Qualificado", "Reunião Agendada
