import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Google Sheets", layout="wide", initial_sidebar_state="expanded")

# --- CONEXÃO COM GOOGLE SHEETS (COM DIAGNÓSTICO) ---
def conectar_gsheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # --- ÁREA DE DIAGNÓSTICO (DEDO-DURO) ---
        # Verifica se o Render está entregando a chave
        if "CREDENCIAIS_GOOGLE" in os.environ:
            # st.toast("Chave encontrada no Render!", icon="✅") # Feedback visual
            creds_json = os.environ["CREDENCIAIS_GOOGLE"]
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            # st.warning("Chave NÃO encontrada no Render. Tentando local...")
            # Tenta ler localmente (apenas PC)
            # Se falhar aqui, é porque não achou nem no Render nem no PC
            if "gsheets" in st.secrets:
                creds_dict = dict(st.secrets["gsheets"])
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            else:
                st.error("ERRO FATAL: Nenhuma credencial encontrada.")
                st.info("No Render: Verifique se a variável 'CREDENCIAIS_GOOGLE' foi criada em 'Environment'.")
                st.stop()
        
        client = gspread.authorize(creds)
        sheet = client.open("BI_Historico").sheet1
        return sheet
        
    except Exception as e:
        st.error(f"Erro na Conexão: {e}")
        return None

# --- FUNÇÕES AUXILIARES (IGUAIS AO ANTERIOR) ---
def salvar_no_gsheets(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet:
        try:
            df_save = df[['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']].copy()
            df_save['semana_ref'] = semana
            df_save['marca_ref'] = marca
            df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df_save = df_save[['data_upload', 'semana_ref', 'marca_ref', 'Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']]
            dados_lista = df_save.values.tolist()
            sheet.append_rows(dados_lista)
            return True
        except Exception as e:
            st.error(f"Erro ao gravar: {e}")
            return False
    return False

def carregar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            return pd.DataFrame(data)
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def limpar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        sheet.delete_rows(2, 10000)
        return True
    return False

@st.cache_data(show_spinner=False)
def load_data(file):
    try:
        file.seek(0)
        df = pd.read_csv(file, sep=';')
        if len(df.columns) > 0 and 'sep=' in str(df.columns[0]):
            file.seek(0)
            df = pd.read_csv(file, sep=';', skiprows=1)
    except:
        file.seek(0)
        df = pd.read_csv(file, sep=',')
    return df

def process_data(df):
    # Processamento simples para evitar erros
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    def deduzir_status(row):
        raw_motivo = str(row.get('Motivo de Perda', ''))
        motivo = raw_motivo.strip().lower() 
        etapa = str(row.get('Etapa', '')).lower()
        if 'venda' in etapa or 'fechamento' in etapa or 'matricula' in etapa: return 'Ganho'
        valores_vazios = ['nan', 'nat', 'none', '', '-', 'null']
        if 'nada' in motivo or motivo in valores_vazios: return 'Em Andamento'
        return 'Perdido'

    df['Status_Calc'] = df.apply(deduzir_status, axis=1)
    
    # Tratamento de datas (simplificado)
    col_criacao = None
    for col in df.columns:
        if col in ['Data de criação', 'Created at', 'Data Criação', 'Data']: col_criacao = col
    if col_criacao:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_criacao], dayfirst=True, errors='coerce')
    else:
        df['Data_Criacao_DT'] = pd.NaT
        
    return df

# --- INTERFACE ---
st.title("📊 BI Corporativo - Nuvem")

modo_view = st.radio("Modo:", ["📥 Importar", "🗄️ Histórico"], horizontal=True)
st.divider()

if modo_view == "📥 Importar":
    opcoes_marca = ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"]
    marca = st.selectbox("Consultor:", opcoes_marca)

    if marca != "Selecione...":
        uploaded = st.file_uploader("CSV", type=['csv'])
        if uploaded:
            df = process_data(load_data(uploaded))
            
            # Filtro básico
            if marca != "Todas as Marcas":
                termo = marca.split(' ')[-1]
                # Tenta filtrar (lógica simplificada para teste)
                col_resp = next((c for c in df.columns if c in ['Proprietário', 'Responsável', 'Consultor']), None)
                if col_resp:
                    df = df[df[col_resp].astype(str).str.contains(termo, case=False, na=False)]

            st.write(f"Leads carregados: {len(df)}")
            
            semana = st.selectbox("Semana Ref:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4"])
            if st.button("Salvar no Google Sheets"):
                if salvar_no_gsheets(df, semana, marca):
                    st.success("Salvo!")

elif modo_view == "🗄️ Histórico":
    if st.button("Carregar Dados"):
        df_hist = carregar_historico_gsheets()
        if not df_hist.empty:
            st.dataframe(df_hist)
        else:
            st.warning("Sem dados ou erro de conexão.")
