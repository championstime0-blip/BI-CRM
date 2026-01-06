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
# ESTILIZAÇÃO CSS (COMPLETA)
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
}
.profile-group { display: flex; flex-direction: column; }
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
}
.card-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; min-height: 30px; display: flex; align-items: center; justify-content: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES & CONEXÃO
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
MOTIVOS_PERDA_MESTRADOS = [
    "Sem Resposta", "Sem Capital", "Desistiu do Negócio", "Outro Investimento", 
    "Fora de Perfil", "Não tem interesse em franquia", "Lead Duplicado", 
    "Dados Inválidos", "Região Indisponível", "Sócio não aprovou"
]

def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except: return None

# =========================
# FUNÇÕES DE UI
# =========================
def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

# =========================
# LÓGICA DE DADOS
# =========================
def status_logic(row):
    estado = str(row.get("Estado", "")).lower()
    if estado == "perdida": return "Perdido"
    etapa = str(row.get("Etapa", "")).lower()
    if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
    motivo = str(row.get("Motivo de Perda", "")).strip().lower()
    if motivo not in ["", "nan", "none", "-", "0", "nada", "n/a"]: return "Perdido"
    return "Em Andamento"

def get_historico():
    client = conectar_google()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("BI_Historico")
        ws = sh.worksheet("db_snapshots")
        lista_dados = ws.get_all_values()
        if len(lista_dados) < 2: return pd.DataFrame()
        df = pd.DataFrame(lista_dados[1:], columns=lista_dados[0])
        df.columns = df.columns.str.strip()
        if "Status" not in df.columns:
            df["Status"] = df.apply(status_logic, axis=1)
        return df
    except: return pd.DataFrame()

# =========================
# RENDERIZAÇÃO DO DASHBOARD
# =========================
def render_dashboard(df):
    total = len(df)
    if "Status" not in df.columns:
        df["Status"] = df.apply(status_logic, axis=1)
        
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
            # CORREÇÃO: Usando Blues_r para tons de azul/ciano seguros
            fig_pie = px.pie(df_fonte, values=df_fonte.columns[1], names=df_fonte.columns[0], hole=0.6, 
                             color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_pie.update_traces(textposition='inside', textinfo='label+value')
            fig_pie.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_funil:
        subheader_futurista("📉", "FUNIL DE VENDAS")
        ordem_funil = ["Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "negociação", "em aprovação", "faturado"]
        funil_labels = ["TOTAL"] + [e.upper() for e in ordem_funil]
        funil_values = [total]
        for etapa in ordem_funil:
            idx = ordem_funil.index(etapa)
            etapas_futuras = [e.lower() for e in ordem_funil[idx:]]
            qtd = len(df[df["Etapa"].str.lower().isin(etapas_futuras)])
            funil_values.append(qtd)
        
        df_plot = pd.DataFrame({"Etapa": funil_labels, "Qtd": funil_values})
        fig_funil = px.bar(df_plot, y="Etapa", x="Qtd", text="Qtd", orientation="h", color="Qtd", color_continuous_scale="Blues")
        fig_funil.update_layout(template="plotly_dark", showlegend=False, yaxis={'categoryorder':'array', 'categoryarray':funil_labels[::-1]})
        st.plotly_chart(fig_funil, use_container_width=True)

    st.divider()
    subheader_futurista("🚫", "DETALHE DAS PERDAS (MOTIVOS)")
    motivos_reais = perdidos["Motivo de Perda"].unique()
    lista_final = list(set(motivos_reais) | set(MOTIVOS_PERDA_MESTRADOS))
    df_loss = perdidos["Motivo de Perda"].value_counts().reindex(lista_final, fill_value=0).reset_index()
    df_loss.columns = ["Motivo", "Qtd"]
    df_loss = df_loss.sort_values(by="Qtd", ascending=False)
    
    # CORREÇÃO: Consistência visual (Verde para Sem Resposta, Vermelho para os demais)
    df_loss['color'] = df_loss['Motivo'].apply(lambda x: '#10b981' if 'sem resposta' in str(x).lower() else '#ef4444')
    fig_loss = px.bar(df_loss, x="Qtd", y="Motivo", text="Qtd", orientation="h", color="Motivo", color_discrete_map=dict(zip(df_loss['Motivo'], df_loss['color'])))
    fig_loss.update_layout(template="plotly_dark", showlegend=False, height=500, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_loss, use_container_width=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 HISTÓRICO CRM</div>', unsafe_allow_html=True)



df_hist = get_historico()

if not df_hist.empty and 'marca_ref' in df_hist.columns:
    marcas_disponiveis = df_hist['marca_ref'].unique()
    marca_hist = st.sidebar.selectbox("Filtrar Marca", marcas_disponiveis)
    
    df_marca = df_hist[df_hist['marca_ref'] == marca_hist]
    if 'semana_ref' in df_marca.columns:
        semanas_disponiveis = df_marca['semana_ref'].unique()
        semana_hist = st.sidebar.selectbox("Escolher Semana Salva", semanas_disponiveis)
        
        df_view = df_marca[df_marca['semana_ref'] == semana_hist]
        
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Arquivo de Consulta</span><span class="profile-value">{semana_hist}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Marca</span><span class="profile-value">{marca_hist}</span></div>
        </div>""", unsafe_allow_html=True)
        
        render_dashboard(df_view)
else:
    st.warning("⚠️ O histórico está vazio ou os dados salvos não possuem as colunas de referência.")
