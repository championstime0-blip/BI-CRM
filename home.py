import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# (O CSS enviado por você permanece aqui para manter o visual idêntico)
# [Inserir aqui todo o bloco de <style> do seu código original]

# =========================
# FUNÇÕES DE CONEXÃO
# =========================
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # No Render/Cloud use st.secrets. No local, use o caminho do arquivo JSON
    creds_dict = json.loads(st.secrets["gcp_service_account"]) 
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# =========================
# MOTOR DE PROCESSAMENTO (BLINDADO)
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    # Limpeza de nomes de colunas para evitar erros de encoding
    df.columns = [c.encode('latin-1').decode('utf-8', 'ignore') if isinstance(c, str) else c for c in df.columns]
    
    cols_map = {}
    for c in df.columns:
        c_low = str(c).lower()
        if any(x in c_low for x in ["fonte", "origem", "source"]): cols_map[c] = "Fonte"
        if any(x in c_low for x in ["data de cri", "created date"]): cols_map[c] = "Data de Criação"
        if any(x in c_low for x in ["respons", "dono"]): cols_map[c] = "Responsável"
        if any(x in c_low for x in ["equipe", "team"]): cols_map[c] = "Equipe"
    
    df = df.rename(columns=cols_map)
    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str).fillna("")
    
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def definir_status(row):
        etapa = str(row["Etapa"]).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(definir_status, axis=1)
    return df

# =========================
# INTERFACE PRINCIPAL
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações de Carga")
    marca_selecionada = st.selectbox("Selecione a Marca", ["Microlins", "PreparaIA", "Ensina Mais 1", "Ensina Mais 2"])
    semana_referencia = st.selectbox("Semana de Referência", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
    arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    df = processar(load_csv(arquivo))
    
    # [Toda a lógica de geração de KPIs e Gráficos do seu código original aqui]
    # ...
    
    # =========================
    # BOTÃO SALVAR DADOS
    # =========================
    st.divider()
    if st.button("🚀 SALVAR DADOS NO HISTÓRICO"):
        try:
            client = conectar_google()
            sh = client.open("BI_Historico")
            ws = sh.worksheet(marca_selecionada)
            
            # Preparar linha para salvar
            agora = datetime.now()
            # Exemplo de dados: Data, Hora, Semana, Total Leads, Taxa Avanço, Responsável
            nova_linha = [
                agora.strftime("%d/%m/%Y"), 
                agora.strftime("%H:%M:%S"),
                semana_referencia,
                len(df),
                f"{perc_avanco:.2f}%",
                resp_val, # Pego do processamento
                equipe_val
            ]
            ws.append_row(nova_linha)
            st.success(f"✅ Dados de {marca_selecionada} ({semana_referencia}) salvos com sucesso!")
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
