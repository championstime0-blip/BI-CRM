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

# =========================
# ESTILIZAÇÃO CSS (MANTIDA)
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
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); transition: all 0.3s ease; height: 100%;
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
ETAPAS_FUNIL = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]

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

# =========================
# FUNÇÕES DE PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

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
        elif c_lower == "motivo de perda": cols_map[c] = "Motivo de Perda"
        elif c_lower == "etapa": cols_map[c] = "Etapa"

    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()]

    colunas_texto = ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte"]
    for col in colunas_texto:
        if col in df.columns:
            if isinstance(df[col], pd.DataFrame): df[col] = df[col].iloc[:, 0]
            df[col] = df[col].astype(str).str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável").fillna("N/A")
        else:
            df[col] = "N/A"

    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status(row):
        etapa_lower = str(row["Etapa"]).lower()
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "nan", "0", "nada"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status, axis=1)
    return df

def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

st.sidebar.header("Painel de Carga")
marca_sel = st.sidebar.selectbox("Marca", MARCAS)
semana_sel = st.sidebar.selectbox("Semana Ref.", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"])

arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = load_csv(arquivo)
        df = processar(df)
        
        # Dashboard básico da Home (simplificado para o exemplo)
        total = len(df)
        perdidos = len(df[df["Status"] == "Perdido"])
        c1, c2 = st.columns(2)
        with c1: card("Leads Totais", total)
        with c2: card("Perdidos", perdidos)
        st.divider()

        # ==========================================================
        # BOTÃO SALVAR CORRIGIDO (FORÇA CABEÇALHO)
        # ==========================================================
        if st.sidebar.button(f"🚀 SALVAR HISTÓRICO: {semana_sel}"):
            with st.spinner("Corrigindo banco de dados e salvando..."):
                client = conectar_google()
                if client:
                    try:
                        sh = client.open("BI_Historico")
                        try:
                            ws = sh.worksheet("db_snapshots")
                        except:
                            ws = sh.add_worksheet(title="db_snapshots", rows="1000", cols="20")
                        
                        # PREPARAÇÃO DOS DADOS
                        df_save = df.copy()
                        agora = datetime.now()
                        id_snap = agora.strftime("%Y%m%d_%H%M%S")
                        
                        # Adiciona colunas de controle
                        df_save['snapshot_id'] = id_snap
                        df_save['data_salvamento'] = agora.strftime('%d/%m/%Y %H:%M')
                        df_save['semana_ref'] = semana_sel
                        df_save['marca_ref'] = marca_sel
                        
                        # Converte tudo para string
                        df_save = df_save.astype(str)
                        
                        # --- CORREÇÃO DO ERRO DA IMAGEM ---
                        # Verifica se a linha 1 realmente é um cabeçalho válido
                        dados_existentes = ws.get_all_values()
                        
                        # Se estiver vazio OU se a primeira célula não for um nome de coluna esperado (ex: não tem 'snapshot_id')
                        precisa_cabecalho = False
                        if not dados_existentes:
                            precisa_cabecalho = True
                        elif 'snapshot_id' not in dados_existentes[0]: 
                            # Aqui detectamos que sua planilha está "suja" com dados mas sem cabeçalho correto
                            precisa_cabecalho = True
                            ws.clear() # Limpa a planilha errada
                        
                        if precisa_cabecalho:
                            # Escreve cabeçalho + dados
                            ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())
                        else:
                            # Apenas adiciona dados (cabeçalho já existe e está correto)
                            ws.append_rows(df_save.values.tolist())
                            
                        st.sidebar.success(f"Salvo com sucesso! ID: {id_snap}")
                        st.balloons()
                    except Exception as e:
                        st.sidebar.error(f"Erro ao salvar: {e}")
                else:
                    st.sidebar.error("Erro de conexão Google.")
                    
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
