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
st.set_page_config(page_title="Histórico | Time Machine", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (MANTIDA DO SEU CÓDIGO)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 42px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 20px; text-shadow: 0 0 20px rgba(34, 211, 238, 0.3);
}
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 20px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 20px; margin-bottom: 15px;
}
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 20px; border-radius: 12px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); height: 100%;
}
.card-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 700;
    color: #22d3ee;
}
.funnel-card {
    background: rgba(15, 23, 42, 0.6); border-left: 3px solid #22d3ee;
    padding: 10px; margin-bottom: 10px; border-radius: 4px;
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
        # Fallback para arquivo local se não tiver env var
        if not creds_json: 
             creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
             return gspread.authorize(creds)
             
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

# =========================
# LÓGICA DE PROCESSAMENTO (RECRIADA PARA O HISTÓRICO)
# =========================
# Precisamos reprocessar os dados brutos do snapshot para gerar os gráficos
ETAPAS_FUNIL = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]

def processar_snapshot(df):
    # Garante que colunas numéricas voltem a ser números (GSheets devolve tudo como texto)
    # Recalcula Status caso não tenha sido salvo
    def status(row):
        etapa_lower = str(row["Etapa"]).lower() if "Etapa" in row else ""
        motivo = str(row["Motivo de Perda"]).strip().lower() if "Motivo de Perda" in row else ""
        
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        if motivo not in ["", "nan", "none", "-", "nan", "0", "nada", "n/a"]: return "Perdido"
        return "Em Andamento"
    
    if "Status" not in df.columns:
        df["Status"] = df.apply(status, axis=1)
        
    return df

# =========================
# INTERFACE PRINCIPAL
# =========================
st.markdown('<div class="futuristic-title">🕰️ Máquina do Tempo</div>', unsafe_allow_html=True)
st.info("Este painel recupera os dados **exatamente** como estavam no momento do salvamento.")

# 1. CARREGAR O BANCO DE DADOS COMPLETO
with st.spinner("Acessando Banco de Dados de Snapshots..."):
    client = conectar_google()
    df_db = pd.DataFrame()
    
    if client:
        try:
            sh = client.open("BI_Historico") # Nome da Planilha
            ws = sh.worksheet("db_snapshots") # Nome da Aba criada pelo Home.py
            dados = ws.get_all_values()
            
            if len(dados) > 1:
                df_db = pd.DataFrame(dados[1:], columns=dados[0])
            else:
                st.warning("O banco de dados existe, mas está vazio.")
        except Exception as e:
            st.error(f"Erro ao ler banco de dados (Verifique se salvou algo na Home primeiro): {e}")

# 2. SELEÇÃO DO SNAPSHOT
if not df_db.empty:
    st.sidebar.header("🗂️ Selecione a Versão")
    
    # Cria uma coluna combinada para o selectbox ficar informativo
    # Ex: "04/01/2026 | Semana 1 | Expansão Microlins"
    if 'data_salvamento' in df_db.columns and 'semana_ref' in df_db.columns:
        df_db['Label'] = df_db['data_salvamento'] + " | " + df_db['semana_ref'] + " | " + df_db.get('marca_ref', 'Geral')
    else:
        df_db['Label'] = df_db['snapshot_id']

    # Remove duplicatas de IDs (caso haja bug de salvamento)
    opcoes = df_db[['snapshot_id', 'Label']].drop_duplicates().sort_values('snapshot_id', ascending=False)
    
    escolha = st.sidebar.selectbox("Escolha o Ponto de Restauração:", options=opcoes['Label'])
    
    if escolha:
        # Pega o ID correspondente à escolha
        id_snap = opcoes[opcoes['Label'] == escolha]['snapshot_id'].values[0]
        
        # --- FILTRA OS DADOS (A MÁGICA ACONTECE AQUI) ---
        df_recuperado = df_db[df_db['snapshot_id'] == id_snap].copy()
        
        # Remove colunas de controle para não sujar
        meta_cols = ['snapshot_id', 'data_salvamento', 'Label']
        df_clean = df_recuperado.drop(columns=[c for c in meta_cols if c in df_recuperado.columns])
        
        # Processa para garantir tipos corretos
        df_final = processar_snapshot(df_clean)
        
        # --- EXIBIÇÃO DO DASHBOARD (RECRIAÇÃO DO VISUAL DA HOME) ---
        
        # KPIS GERAIS
        total = len(df_final)
        perdidos = df_final[df_final["Status"] == "Perdido"]
        andamento = df_final[df_final["Status"] == "Em Andamento"]
        
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Total no Snapshot</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Em Andamento</div><div class="card-value">{len(andamento)}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="card"><div class="card-title">Perdidos</div><div class="card-value">{len(perdidos)}</div></div>', unsafe_allow_html=True)
        
        st.divider()
        
        col_graf1, col_graf2 = st.columns(2)
        
        # GRÁFICO 1: FONTES (Igual Home)
        with col_graf1:
            st.markdown('<div class="futuristic-sub">📡 Fontes de Tráfego</div>', unsafe_allow_html=True)
            if "Fonte" in df_final.columns:
                df_fonte = df_final["Fonte"].value_counts().reset_index()
                df_fonte.columns = ["Fonte", "Qtd"]
                
                fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, 
                                 color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2', '#155e75'])
                fig_pie.update_traces(textposition='outside', textinfo='percent+label')
                fig_pie.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.warning("Coluna 'Fonte' não encontrada neste snapshot.")

        # GRÁFICO 2: FUNIL (Igual Home)
        with col_graf2:
            st.markdown('<div class="futuristic-sub">📉 Funil do Momento</div>', unsafe_allow_html=True)
            if "Etapa" in df_final.columns:
                df_funil = df_final.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
                df_funil["Percentual"] = (df_funil["Qtd"] / total * 100).round(1) if total > 0 else 0
                
                fig_funil = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h", text=df_funil["Percentual"].astype(str)+"%", 
                                   color="Qtd", color_continuous_scale="Blues")
                fig_funil.update_layout(template="plotly_dark", showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_funil, use_container_width=True)
            else:
                st.warning("Coluna 'Etapa' não encontrada neste snapshot.")

        # TABELA DE DADOS
        with st.expander("📂 Ver Dados Brutos deste Arquivo"):
            st.dataframe(df_final)

else:
    st.info("Nenhum histórico encontrado. Salve um arquivo na página Home primeiro.")
