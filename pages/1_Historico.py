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
# ESTILIZAÇÃO CSS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 42px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 2px;
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px;
    margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between;
}
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
        
        df = pd.DataFrame(rows[1:], columns=rows[0])
        df.columns = df.columns.str.strip()
        return df
    except: return pd.DataFrame()

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    if raw.strip().startswith("sep="): raw = "\n".join(raw.splitlines()[1:])
    sep = ";" if raw.count(";") > raw.count(",") else ","
    return pd.read_csv(io.StringIO(raw), sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    cols_map = {}
    for c in df.columns:
        c_lower = str(c).lower()
        if "fonte" in c_lower and "utm" not in c_lower: cols_map[c] = "Fonte"
        elif "etapa" in c_lower: cols_map[c] = "Etapa"
        elif "motivo de perda" in c_lower: cols_map[c] = "Motivo de Perda"
        elif "estado" in c_lower: cols_map[c] = "Estado"

    df = df.rename(columns=cols_map)
    
    def status_func(row):
        if str(row.get("Estado", "")).lower() == "perdida": return "Perdido"
        etapa = str(row.get("Etapa", "")).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        return "Em Andamento" if str(row.get("Motivo de Perda", "")).strip().lower() in ["", "nan", "none", "nada", "0"] else "Perdido"
        
    df["Status"] = df.apply(status_func, axis=1)
    return df

# =========================
# DASHBOARD RENDERING
# =========================
def render_dashboard(df):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="card"><div>Leads</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div>Perdidos</div><div class="card-value">{len(perdidos)}</div></div>', unsafe_allow_html=True)
    
    st.divider()
    if "Fonte" in df.columns:
        df_f = df["Fonte"].value_counts().reset_index()
        fig = px.pie(df_f, values=df_f.columns[1], names=df_f.columns[0], hole=0.6)
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 CRM EXPANSÃO</div>', unsafe_allow_html=True)

modo = st.sidebar.radio("Selecione o Modo", ["Snapshot Atual (Upload)", "Visão Histórica (Salvos)"])

if modo == "Snapshot Atual (Upload)":
    marca_sel = st.sidebar.selectbox("Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
    semana_sel = st.sidebar.selectbox("Semana Ref.", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"])
    arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])
    
    if arquivo:
        df = processar(load_csv(arquivo))
        render_dashboard(df)
        
        if st.sidebar.button("🚀 SALVAR NO HISTÓRICO"):
            client = conectar_google()
            if client:
                sh = client.open("BI_Historico")
                ws = sh.worksheet("db_snapshots")
                
                df_save = df.copy()
                df_save['snapshot_id'] = datetime.now().strftime("%Y%m%d_%H%M%S")
                df_save['data_salvamento'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                df_save['semana_ref'] = semana_sel
                df_save['marca_ref'] = marca_sel
                
                # --- CORREÇÃO DO CABEÇALHO AQUI ---
                current_values = ws.get_all_values()
                if not current_values:
                    # Se a planilha estiver vazia, insere os nomes das colunas na primeira linha
                    ws.append_row(df_save.columns.tolist())
                
                # Insere os dados abaixo do cabeçalho
                ws.append_rows(df_save.astype(str).values.tolist())
                st.sidebar.success("Snapshot e cabeçalhos salvos com sucesso!")

else:
    df_hist = get_historico()
    if not df_hist.empty and 'marca_ref' in df_hist.columns:
        m_sel = st.sidebar.selectbox("Filtrar Marca", df_hist['marca_ref'].unique())
        s_sel = st.sidebar.selectbox("Filtrar Semana", df_hist[df_hist['marca_ref'] == m_sel]['semana_ref'].unique())
        df_view = df_hist[(df_hist['marca_ref'] == m_sel) & (df_hist['semana_ref'] == s_sel)]
        render_dashboard(df_view)
    else:
        st.warning("Nenhum histórico com colunas válidas encontrado.")
