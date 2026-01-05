import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import io

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão - Histórico", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (FUTURISTA)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 42px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 2px; margin-bottom: 20px;
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px;
    margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between;
}
.profile-label { color: #94a3b8; font-size: 12px; text-transform: uppercase; font-family: 'Rajdhani'; }
.profile-value { color: #f8fafc; font-size: 20px; font-weight: 600; font-family: 'Orbitron'; }
.card {
    background: rgba(30, 41, 59, 0.5); padding: 20px; border-radius: 12px; border: 1px solid #1e293b; text-align: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #38bdf8;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE
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
        
        # Cria DataFrame e limpa nomes de colunas (remove espaços e quebras de linha)
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df.columns = df.columns.str.strip().str.replace('\n', '')
        return df
    except: return pd.DataFrame()

# =========================
# DASHBOARD RENDERING
# =========================
def render_dashboard(df):
    total = len(df)
    
    def get_status(row):
        if str(row.get("Estado", "")).lower() == "perdida": return "Perdido"
        if any(x in str(row.get("Etapa", "")).lower() for x in ["faturado", "ganho", "venda"]): return "Ganho"
        return "Em Andamento" if str(row.get("Motivo de Perda", "")).strip().lower() in ["", "nan", "none", "nada", "0"] else "Perdido"

    df["Status"] = df.apply(get_status, axis=1)
    perdidos = df[df["Status"] == "Perdido"]
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="card"><div class="profile-label">Leads no Período</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="profile-label">Total Perdido</div><div class="card-value">{len(perdidos)}</div></div>', unsafe_allow_html=True)
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        if "Fonte" in df.columns:
            df_f = df["Fonte"].value_counts().reset_index()
            fig = px.pie(df_f, values=df_f.columns[1], names=df_f.columns[0], hole=0.6, title="Fontes")
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        if "Motivo de Perda" in df.columns and not perdidos.empty:
            df_l = perdidos["Motivo de Perda"].value_counts().reset_index()
            fig_l = px.bar(df_l, x=df_l.columns[1], y=df_l.columns[0], orientation="h", title="Motivos de Perda")
            fig_l.update_layout(template="plotly_dark", yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_l, use_container_width=True)

# =========================
# EXECUÇÃO PRINCIPAL
# =========================
st.markdown('<div class="futuristic-title">📜 HISTÓRICO DE SNAPSHOTS</div>', unsafe_allow_html=True)

df_hist = get_historico()

if not df_hist.empty:
    # Verificação exata dos nomes das colunas de controle
    colunas_encontradas = [c.lower() for c in df_hist.columns]
    
    if 'marca_ref' in colunas_encontradas and 'semana_ref' in colunas_encontradas:
        # Garante que usamos os nomes originais mapeados
        col_marca = df_hist.columns[colunas_encontradas.index('marca_ref')]
        col_semana = df_hist.columns[colunas_encontradas.index('semana_ref')]
        
        marcas_h = df_hist[col_marca].unique()
        m_sel = st.sidebar.selectbox("Marca", marcas_h)
        
        semanas_h = df_hist[df_hist[col_marca] == m_sel][col_semana].unique()
        s_sel = st.sidebar.selectbox("Semana", semanas_h)
        
        df_view = df_hist[(df_hist[col_marca] == m_sel) & (df_hist[col_semana] == s_sel)]
        
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Marca</span><span class="profile-value">{m_sel}</span></div>
            <div class="profile-group"><span class="profile-label">Período</span><span class="profile-value">{s_sel}</span></div>
        </div>""", unsafe_allow_html=True)
        
        render_dashboard(df_view)
    else:
        st.error("⚠️ Colunas de referência não encontradas.")
        st.info("A planilha 'db_snapshots' precisa ter na primeira linha os títulos: **marca_ref** e **semana_ref**.")
        st.write("Colunas lidas atualmente:", list(df_hist.columns))
else:
    st.warning("Nenhum histórico encontrado. Realize um novo salvamento na página inicial.")
