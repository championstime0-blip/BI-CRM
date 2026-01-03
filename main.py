import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
import json
import os
import io
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
# 1. MOTOR DE CONEXÃO (BLINDADO)
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
            st.error("ERRO: Nenhuma credencial encontrada.")
            return None
        client = gspread.authorize(creds)
        sheet = client.open("BI_Historico").sheet1
        return sheet
    except Exception as e:
        st.error(f"Erro de Conexão com Google: {e}")
        return None

# ==============================================================================
# 2. FUNÇÕES DE DADOS E LÓGICA
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
        # Detecta o separador automaticamente (CSV do Pedro usa ;)
        raw_bytes = file.getvalue()
        content = raw_bytes.decode('utf-8-sig')
        sep = ';' if ';' in content.splitlines()[0] else ','
        return pd.read_csv(io.StringIO(content), sep=sep)
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
        return pd.DataFrame()

def process_data(df):
    # Padronização de Colunas
    df.columns = [c.strip() for c in df.columns]
    
    # Datas
    possiveis_criacao = ['Data de criação', 'Created at', 'Data Criação', 'Data']
    col_criacao = next((c for c in df.columns if c in possiveis_criacao), None)
    if col_criacao:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_criacao], dayfirst=True, errors='coerce')
    else:
        df['Data_Criacao_DT'] = pd.NaT

    # Cidade
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # Lógica de Status
    def deduzir_status(row):
        raw_motivo = str(row.get('Motivo de Perda', ''))
        motivo = raw_motivo.strip().lower() 
        etapa = str(row.get('Etapa', '')).lower()
        # No Pedro.csv, o estado 'Perdida' também ajuda
        estado = str(row.get('Estado', '')).lower()
        
        if any(x in etapa for x in ['venda', 'fechamento', 'matricula']): return 'Ganho'
        if estado == 'perdida' or (motivo != 'nan' and motivo != '' and motivo != 'nada'): return 'Perdido'
        return 'Em Andamento'

    df['Status_Calc'] = df.apply(deduzir_status, axis=1)
    return df

# ==============================================================================
# 3. MOTOR DE VISUALIZAÇÃO UNIFICADO
# ==============================================================================
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

    tab1, tab2, tab3 = st.tabs(["📢 Fonte & Campanha", "📉 Funil Profissional", "🚫 Perdas"])

    with tab1:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.subheader("Fonte")
            if 'Fonte' in df.columns:
                df_fonte = df['Fonte'].value_counts().reset_index()
                df_fonte.columns = ['Fonte', 'Leads']
                st.plotly_chart(px.pie(df_fonte, values='Leads', names='Fonte', hole=0.4), use_container_width=True)

        with col_m2:
            st.subheader("Campanha")
            if 'Campanha' in df.columns:
                df_camp = df['Campanha'].value_counts().head(10).reset_index()
                df_camp.columns = ['Campanha', 'Leads']
                st.plotly_chart(px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads'), use_container_width=True)

    with tab2:
        st.subheader("Funil de Conversão (Impacto sobre Total)")
        if 'Etapa' in df.columns:
            df_funil = df['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            existentes = [c for c in ordem if c in df_funil['Etapa'].values]
            df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=existentes + [c for c in df_funil['Etapa'].values if c not in ordem], ordered=True)
            df_funil = df_funil.sort_values('Etapa')
            
            fig = go.Figure(go.Funnel(y=df_funil['Etapa'], x=df_funil['Volume'], textinfo="value+percent initial"))
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("Análise de Perdas")
        if 'Motivo de Perda' in df.columns:
            df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
            if not df_lost.empty:
                # Regra: Sem Resposta só conta se Etapa for inicial
                mask = (df_lost['Motivo de Perda'] != 'Sem Resposta') | (df_lost['Etapa'] == 'Aguardando Resposta')
                df_l = df_lost[mask]
                motivos = df_l['Motivo de Perda'].value_counts().reset_index()
                motivos.columns = ['Motivo', 'Qtd']
                st.plotly_chart(px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Qtd'), use_container_width=True)

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("📊 BI Corporativo Expansão")
modo_view = st.radio("Modo:", ["📥 Importar Planilha", "🗄️ Histórico Gerencial"], horizontal=True)
st.divider()

if modo_view == "📥 Importar Planilha":
    marca_selecionada = st.sidebar.selectbox("Consultor/Marca:", ["Selecione...", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    
    if marca_selecionada != "Selecione...":
        uploaded_file = st.sidebar.file_uploader("Subir Pedro.csv", type=['csv'])
        if uploaded_file:
            df = process_data(load_data(uploaded_file))
            
            # Filtro de Responsável
            col_resp = next((c for c in df.columns if c in ['Responsável', 'Proprietário']), None)
            if col_resp:
                termo = marca_selecionada.split(' ')[-1]
                df = df[df[col_resp].astype(str).str.contains(termo, case=False, na=False)]

            semana = st.sidebar.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
            if st.sidebar.button("💾 Salvar no Google Sheets"):
                if salvar_no_gsheets(df, semana, marca_selecionada):
                    st.sidebar.success("✅ Salvo!")

            renderizar_dashboard_completo(df)

elif modo_view == "🗄️ Histórico Gerencial":
    df_hist = carregar_historico_gsheets()
    if not df_hist.empty:
        f_marca = st.sidebar.selectbox("Marca:", ["Todas"] + sorted(list(df_hist['marca_ref'].unique())))
        f_semana = st.sidebar.selectbox("Semana:", ["Todas"] + sorted(list(df_hist['semana_ref'].unique())))
        
        df_v = df_hist.copy()
        if f_marca != "Todas": df_v = df_v[df_v['marca_ref'] == f_marca]
        if f_semana != "Todas": df_v = df_v[df_v['semana_ref'] == f_semana]
        
        renderizar_dashboard_completo(df_v, f"Histórico: {f_marca}")
        
        if st.sidebar.button("⚠️ Limpar Tudo"):
            if limpar_historico_gsheets(): st.rerun()
