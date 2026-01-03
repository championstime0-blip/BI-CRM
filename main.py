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
st.set_page_config(page_title="BI Corporativo Pro", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: bold;
    }
    .st-emotion-cache-1r6slb0 {
        border: 1px solid #333;
        padding: 15px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CONEXÃO GOOGLE SHEETS
# ==============================================================================
def conectar_gsheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        if "CREDENCIAIS_GOOGLE" in os.environ:
            creds_json = os.environ["CREDENCIAIS_GOOGLE"]
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif "gsheets" in st.secrets:
            creds_dict = dict(st.secrets["gsheets"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        else:
            st.error("ERRO: Credenciais não encontradas.")
            return None
        
        client = gspread.authorize(creds)
        sheet = client.open("BI_Historico").sheet1
        return sheet
    except Exception as e:
        st.error(f"Erro de Conexão: {e}")
        return None

# ==============================================================================
# 2. FUNÇÕES DE BANCO DE DADOS
# ==============================================================================
def salvar_no_gsheets(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet:
        try:
            cols_save = ['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']
            if 'Fonte' not in df.columns: df['Fonte'] = '-'
            if 'Campanha' not in df.columns: df['Campanha'] = '-'
            cols_save.extend(['Fonte', 'Campanha'])

            df_save = df[cols_save].copy()
            df_save['semana_ref'] = semana
            df_save['marca_ref'] = marca
            df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            df_save = df_save[['data_upload', 'semana_ref', 'marca_ref', 'Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda', 'Fonte', 'Campanha']]
            df_save = df_save.fillna('-')
            
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
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame(columns=['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda', 'Fonte', 'Campanha', 'semana_ref', 'marca_ref', 'data_upload'])

            mapa_correcao = {
                'status': 'Status_Calc', 'Status': 'Status_Calc',
                'etapa': 'Etapa',
                'cidade': 'Cidade_Clean', 'Cidade': 'Cidade_Clean',
                'motivo_perda': 'Motivo de Perda', 'motivo': 'Motivo de Perda',
                'fonte': 'Fonte', 'campanha': 'Campanha', 'data_upload': 'data_upload'
            }
            df.rename(columns=mapa_correcao, inplace=True)
            
            required = ['Status_Calc', 'Etapa', 'Motivo de Perda', 'data_upload']
            for col in required:
                if col not in df.columns: df[col] = 'Desconhecido'
            
            return df
        except Exception as e:
            st.warning(f"Erro ao ler histórico: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def limpar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        try:
            sheet.delete_rows(2, 10000) 
            return True
        except: return False
    return False

# ==============================================================================
# 3. PROCESSAMENTO E VISUALIZAÇÃO
# ==============================================================================
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
    col_criacao = None
    col_fechamento = None
    possiveis_criacao = ['Data de criação', 'Created at', 'Data Criação', 'Data']
    possiveis_fechamento = ['Data de fechamento', 'Closed at', 'Data Fechamento', 'Data da perda']

    for col in df.columns:
        if col in possiveis_criacao: col_criacao = col
        if col in possiveis_fechamento: col_fechamento = col
    
    if col_criacao:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_criacao], dayfirst=True, errors='coerce')
    else: df['Data_Criacao_DT'] = pd.NaT

    if col_fechamento:
        df['Data_Fechamento_DT'] = pd.to_datetime(df[col_fechamento], dayfirst=True, errors='coerce')
    else: df['Data_Fechamento_DT'] = pd.NaT

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
    return df

def renderizar_dashboard_completo(df, titulo_recorte="Recorte de Dados"):
    total = len(df)
    vendas = len(df[df['Status_Calc'] == 'Ganho'])
    perdidos = len(df[df['Status_Calc'] == 'Perdido'])
    em_andamento = len(df[df['Status_Calc'] == 'Em Andamento'])
    conversao = (vendas / total * 100) if total > 0 else 0

    st.markdown(f"### {titulo_recorte}")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", total)
    c2.metric("Vendas", vendas, delta=f"{conversao:.1f}% Conv.")
    c3.metric("Em Andamento", em_andamento)
    c4.metric("Perdidos", perdidos, delta_color="inverse")
    
    st.divider()

    tab1, tab2, tab3 = st.tabs(["📢 Marketing", "📉 Funil Pro", "🚫 Perdas"])

    with tab1:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.subheader("Fonte")
            if 'Fonte' in df.columns and df['Fonte'].notna().any():
                df_fonte = df['Fonte'].value_counts().reset_index()
                df_fonte.columns = ['Fonte', 'Leads']
                fig_fonte = px.pie(df_fonte, values='Leads', names='Fonte', hole=0.4)
                st.plotly_chart(fig_fonte, use_container_width=True)
            else: st.info("Sem dados de Fonte.")
        with col_m2:
            st.subheader("Campanha")
            if 'Campanha' in df.columns and df['Campanha'].notna().any():
                df_camp = df['Campanha'].value_counts().head(10).reset_index()
                df_camp.columns = ['Campanha', 'Leads']
                fig_camp = px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads')
                st.plotly_chart(fig_camp, use_container_width=True)
            else: st.info("Sem dados de Campanha.")

    with tab2:
        st.subheader("Funil de Conversão")
        if 'Etapa' in df.columns:
            df_funil = df['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            existentes = [c for c in ordem if c in df_funil['Etapa'].values]
            extras = [c for c in df_funil['Etapa'].values if c not in ordem]
            ordem_final = existentes + extras
            
            df_funil.set_index('Etapa', inplace=True)
            df_funil = df_funil.reindex(ordem_final).reset_index()
            
            fig_funnel = go.Figure(go.Funnel(
                y = df_funil['Etapa'],
                x = df_funil['Volume'],
                textinfo = "value+percent initial",
                opacity = 0.85, 
                marker = {"color": ["#3498db", "#2980b9", "#1abc9c", "#16a085", "#2ecc71", "#27ae60"]},
                connector = {"line": {"color": "royalblue", "dash": "dot", "width": 2}}
            ))
            
            fig_funnel.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                paper_bgcolor="rgba(0,0,0,0)", 
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.warning("Coluna 'Etapa' não encontrada.")

    with tab3:
        st.subheader("Motivos de Perda")
        if 'Motivo de Perda' in df.columns:
            df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
            if not df_lost.empty:
