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
st.set_page_config(page_title="BI CRM Expansão - Histórico", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (IDENTIDADE HOME.PY)
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
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
}
.profile-group { display: flex; flex-direction: column; }
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
MOTIVOS_PERDA_MESTRADOS = ["Sem Resposta", "Sem Capital", "Desistiu do Negócio", "Outro Investimento", "Fora de Perfil", "Não tem interesse em franquia", "Lead Duplicado", "Dados Inválidos", "Região Indisponível", "Sócio não aprovou"]

# =========================
# FUNÇÕES DE CONEXÃO
# =========================
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except: return None

def get_historico():
    client = conectar_google()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("BI_Historico")
        ws = sh.worksheet("db_snapshots")
        rows = ws.get_all_values()
        if len(rows) < 2: return pd.DataFrame()
        df = pd.DataFrame(rows[1:], columns=rows[0])
        # Limpa nomes de colunas para evitar erros de espaço
        df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

def card(title, value):
    st.markdown(f'<div class="card"><div class="profile-label">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

# =========================
# DASHBOARD RENDERING (BASEADO NO HOME.PY)
# =========================
def render_dashboard(df):
    total = len(df)
    
    def status_func(row):
        estado_lower = str(row.get("Estado", "")).lower()
        if "perdida" in estado_lower: return "Perdido"
        etapa_lower = str(row.get("Etapa", "")).lower()
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada", "n/a"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status_func, axis=1)
    perdidos = df[df["Status"] == "Perdido"]
    
    c1, c2 = st.columns(2)
    with c1: card("Leads no Histórico", total)
    with c2: card("Perdidos Gravados", len(perdidos))
    st.divider()

    col_mkt, col_funil = st.columns(2)
    with col_mkt:
        st.markdown('<div class="futuristic-sub">📡 FONTES DE AQUISIÇÃO</div>', unsafe_allow_html=True)
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            fig_pie = px.pie(df_fonte, values=df_fonte.columns[1], names=df_fonte.columns[0], hole=0.6, color_discrete_sequence=px.colors.sequential.Cyan_r)
            fig_pie.update_traces(textposition='inside', textinfo='label+value')
            fig_pie.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_funil:
        st.markdown('<div class="futuristic-sub">📉 ETAPAS DO FUNIL</div>', unsafe_allow_html=True)
        if "Etapa" in df.columns:
            df_etapa = df["Etapa"].value_counts().reset_index()
            fig_bar = px.bar(df_etapa, y=df_etapa.columns[0], x=df_etapa.columns[1], orientation="h", color_discrete_sequence=['#38bdf8'])
            fig_bar.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()
    st.markdown('<div class="futuristic-sub">🚫 MOTIVOS DE PERDA REGISTRADOS</div>', unsafe_allow_html=True)
    if not perdidos.empty:
        df_loss = perdidos["Motivo de Perda"].value_counts().reset_index()
        df_loss.columns = ["Motivo", "Qtd"]
        df_loss['color'] = df_loss['Motivo'].apply(lambda x: '#10b981' if 'sem resposta' in str(x).lower() else '#ef4444')
        fig_loss = px.bar(df_loss, x="Qtd", y="Motivo", text="Qtd", orientation="h", color="Motivo", color_discrete_map=dict(zip(df_loss['Motivo'], df_loss['color'])))
        fig_loss.update_layout(template="plotly_dark", showlegend=False, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_loss, use_container_width=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">📜 HISTÓRICO DE SNAPSHOTS</div>', unsafe_allow_html=True)

df_hist = get_historico()

if not df_hist.empty:
    # Verificação de segurança: a planilha precisa ter as colunas de controle para o filtro funcionar
    if 'marca_ref' in df_hist.columns and 'semana_ref' in df_hist.columns:
        st.sidebar.header("Filtros de Visão")
        marcas_h = df_hist['marca_ref'].unique()
        m_sel = st.sidebar.selectbox("Selecionar Marca", marcas_h)
        
        semanas_h = df_hist[df_hist['marca_ref'] == m_sel]['semana_ref'].unique()
        s_sel = st.sidebar.selectbox("Selecionar Período", semanas_h)
        
        df_view = df_hist[(df_hist['marca_ref'] == m_sel) & (df_hist['semana_ref'] == s_sel)]
        
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Marca Consultada</span><span class="profile-value">{m_sel}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Referência</span><span class="profile-value">{s_sel}</span></div>
        </div>""", unsafe_allow_html=True)
        
        render_dashboard(df_view)
    else:
        st.error("A planilha existe mas não possui as colunas 'marca_ref' ou 'semana_ref'.")
else:
    st.warning("Nenhum dado histórico encontrado. Vá até a página principal para salvar o primeiro Snapshot.")
    st.info("Nota: A primeira vez que você clicar em 'Salvar' na Home, o sistema criará os nomes das colunas automaticamente.")
