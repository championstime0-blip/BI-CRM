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
# 1. MOTOR DE CONEXÃO (BLINDADO HÍBRIDO)
# ==============================================================================
def conectar_gsheets():
    """Conecta ao Google Sheets (Híbrido: Render ou Local)"""
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # 1. Tenta ler do Render (Variável de Ambiente)
        if "CREDENCIAIS_GOOGLE" in os.environ:
            creds_json = os.environ["CREDENCIAIS_GOOGLE"]
            creds_dict = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        # 2. Tenta ler localmente (PC)
        elif "gsheets" in st.secrets:
            creds_dict = dict(st.secrets["gsheets"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        
        else:
            st.error("ERRO: Nenhuma credencial encontrada (Local ou Nuvem). Verifique 'CREDENCIAIS_GOOGLE' no Render.")
            return None
        
        client = gspread.authorize(creds)
        # Tenta abrir a planilha
        sheet = client.open("BI_Historico").sheet1
        return sheet
        
    except Exception as e:
        st.error(f"Erro de Conexão com Google: {e}")
        return None

# ==============================================================================
# 2. FUNÇÕES DE BANCO DE DADOS (COM CORREÇÃO DE COLUNAS)
# ==============================================================================
def salvar_no_gsheets(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet:
        try:
            # Seleciona colunas essenciais + Fonte/Campanha se existirem
            cols_save = ['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']
            
            if 'Fonte' not in df.columns: df['Fonte'] = '-'
            if 'Campanha' not in df.columns: df['Campanha'] = '-'
            cols_save.extend(['Fonte', 'Campanha'])

            df_save = df[cols_save].copy()
            df_save['semana_ref'] = semana
            df_save['marca_ref'] = marca
            df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Reordena para ficar organizado na planilha
            df_save = df_save[['data_upload', 'semana_ref', 'marca_ref', 'Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda', 'Fonte', 'Campanha']]
            
            df_save = df_save.fillna('-')
            
            dados_lista = df_save.values.tolist()
            sheet.append_rows(dados_lista)
            return True
        except Exception as e:
            st.error(f"Erro ao gravar dados: {e}")
            return False
    return False

def carregar_historico_gsheets():
    """Lê o histórico e corrige os nomes das colunas automaticamente"""
    sheet = conectar_gsheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            df = pd.DataFrame(data)
            
            if df.empty:
                return pd.DataFrame(columns=['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda', 'Fonte', 'Campanha', 'semana_ref', 'marca_ref'])

            # --- MAPA DE CORREÇÃO (O Pulo do Gato para evitar KeyError) ---
            # Padroniza nomes vindos da planilha (minúsculo -> Maiúsculo Correto)
            mapa_correcao = {
                'status': 'Status_Calc', 'Status': 'Status_Calc',
                'etapa': 'Etapa',
                'cidade': 'Cidade_Clean', 'Cidade': 'Cidade_Clean',
                'motivo_perda': 'Motivo de Perda', 'motivo': 'Motivo de Perda',
                'fonte': 'Fonte',
                'campanha': 'Campanha'
            }
            df.rename(columns=mapa_correcao, inplace=True)
            
            # Garante colunas obrigatórias
            required = ['Status_Calc', 'Etapa', 'Motivo de Perda']
            for col in required:
                if col not in df.columns: df[col] = 'Desconhecido'
            
            return df
        except Exception as e:
            st.warning(f"Aviso ao ler histórico: {e}")
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
# 3. PROCESSAMENTO DE DADOS (LÓGICA OPERACIONAL)
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
    # Datas
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

    # Cidade
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # Lógica de Status (Regra do Nada = Em Andamento)
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

# ==============================================================================
# 4. MOTOR DE VISUALIZAÇÃO (DASHBOARD UNIFICADO)
# ==============================================================================
def renderizar_dashboard_completo(df, titulo_recorte="Recorte de Dados"):
    """Renderiza o dashboard identico para CSV ou Histórico"""
    
    # KPIs
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

    tab1, tab2, tab3 = st.tabs(["📢 Fonte & Campanha", "📉 Funil de Vendas", "🚫 Análise de Perdas"])

    # ABA 1: MKT
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

    # ABA 2: FUNIL
    with tab2:
        st.subheader("Funil de Conversão")
        if 'Etapa' in df.columns:
            df_funil = df['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            existentes = [c for c in ordem if c in df_funil['Etapa'].values]
            extras = [c for c in df_funil['Etapa'].values if c not in ordem]
            ordem_final = existentes + extras
            
            df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=ordem_final, ordered=True)
            df_funil = df_funil.sort_values('Etapa')
            
            fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa')
            fig_funnel.update_traces(texttemplate='%{value}', textposition='inside')
            st.plotly_chart(fig_funnel, use_container_width=True)

    # ABA 3: PERDAS (FILTRO INTELIGENTE)
    with tab3:
        st.subheader("Motivos de Perda")
        if 'Motivo de Perda' in df.columns:
            df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
            if not df_lost.empty:
                # Filtra Sem Resposta se não for do começo do funil
                mask_valido = (df_lost['Motivo de Perda'] != 'Sem Resposta') | \
                              ((df_lost['Motivo de Perda'] == 'Sem Resposta') & (df_lost['Etapa'] == 'Aguardando Resposta'))
                
                df_lost_chart = df_lost[mask_valido]
                
                excluidos = len(df_lost) - len(df_lost_chart)
                if excluidos > 0:
                    st.caption(f"ℹ️ {excluidos} leads com 'Sem Resposta' em etapas avançadas foram ocultados.")

                c_loss1, c_loss2 = st.columns([2, 1])
                with c_loss1:
                    motivos = df_lost_chart['Motivo de Perda'].value_counts().reset_index()
                    motivos.columns = ['Motivo', 'Qtd']
                    
                    # Percentual sobre o TOTAL (Visão de Impacto Global)
                    motivos['Percent'] = (motivos['Qtd'] / total * 100).round(1)
                    motivos['Texto'] = motivos.apply(lambda x: f"{x['Qtd']} ({x['Percent']}%)", axis=1)
                    
                    fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Texto', title="Principais Motivos")
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                with c_loss2:
                    st.write("**Amostra:**")
                    cols_ver = [c for c in ['Etapa', 'Motivo de Perda', 'Data_Criacao_DT'] if c in df_lost.columns]
                    st.dataframe(df_lost_chart[cols_ver].head(10), use_container_width=True)
            else: st.success("Sem perdas registradas.")

# ==============================================================================
# 5. INTERFACE PRINCIPAL (MAIN)
# ==============================================================================
st.title("📊 BI Corporativo Inteligente")

modo_view = st.radio("Modo:", ["📥 Importar Planilha (Operacional)", "🗄️ Histórico Salvo (Gerencial)"], horizontal=True)
st.divider()

# --- MODO 1: OPERACIONAL ---
if modo_view == "📥 Importar Planilha (Operacional)":
    
    st.sidebar.header("1º Configuração")
    opcoes_marca = ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"]
    marca_selecionada = st.sidebar.selectbox("Operação/Consultor:", opcoes_marca)

    if marca_selecionada == "Selecione...":
        st.info("👋 Selecione uma **Operação** ou **Consultor** na barra lateral para começar.")
        st.stop()

    st.sidebar.divider()
    st.sidebar.header("2º Importação")
    uploaded_file = st.sidebar.file_uploader("Carregar CSV", type=['csv'])

    if uploaded_file is not None:
        with st.status("Processando dados...", expanded=True) as status:
            df_raw = load_data(uploaded_file)
            df = process_data(df_raw)
            
            # Filtro de Marca
            df_filtered = df.copy()
            col_responsavel = None
            for col in ['Proprietário', 'Responsável', 'Dono do lead', 'Consultor']:
                if col in df.columns:
                    col_responsavel = col
                    break
            
            if marca_selecionada != "Todas as Marcas" and col_responsavel:
                termo_busca = marca_selecionada.split(' ')[-1]
                if "Ensina Mais" in marca_selecionada:
                    df_filtered = df_filtered[df_filtered[col_responsavel].astype(str).str.contains(termo_busca, case=False, na=False)]
                else:
                    matches = df_filtered[df_filtered[col_responsavel].astype(str).str.contains(marca_selecionada, case=False, na=False)]
                    if not matches.empty: df_filtered = matches
            
            status.update(label="Pronto!", state="complete", expanded=False)

        if 'Etapa' not in df.columns:
            st.error("Erro: Coluna 'Etapa' ausente.")
            st.stop()

        # Salvar
        st.sidebar.divider()
        st.sidebar.header("☁️ Salvar na Nuvem")
        semana_ref = st.sidebar.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
        
        if st.sidebar.button("💾 Enviar p/ Google Sheets"):
            with st.spinner("Enviando..."):
                if salvar_no_gsheets(df_filtered, semana_ref, marca_selecionada):
                    st.sidebar.success("✅ Salvo!")
                    time.sleep(2)
                else: st.sidebar.error("❌ Erro ao salvar.")

        # Data
        txt_data = "Dados Importados"
        if pd.notna(df_filtered['Data_Criacao_DT']).any():
            d_min = df_filtered['Data_Criacao_DT'].min()
            d_max = df_filtered['Data_Criacao_DT'].max()
            txt_data = f"Recorte: {d_min.strftime('%d/%m')} a {d_max.strftime('%d/%m')}"

        # RENDERIZA O DASHBOARD
        renderizar_dashboard_completo(df_filtered, titulo_recorte=txt_data)

# --- MODO 2: GERENCIAL (HISTÓRICO) ---
elif modo_view == "🗄️ Histórico Salvo (Gerencial)":
    
    st.sidebar.header("Filtros do Histórico")
    
    with st.spinner("Baixando dados da nuvem..."):
        df_hist = carregar_historico_gsheets()

    if df_hist.empty:
        st.warning("Histórico vazio ou erro de conexão com a planilha.")
    else:
        # Filtros
        marcas = ["Todas"] + sorted(list(df_hist['marca_ref'].unique())) if 'marca_ref' in df_hist.columns else []
        semanas = ["Todas"] + sorted(list(df_hist['semana_ref'].unique())) if 'semana_ref' in df_hist.columns else []
        
        f_marca = st.sidebar.selectbox("Filtrar Marca:", marcas)
        f_semana = st.sidebar.selectbox("Filtrar Semana:", semanas)
        
        df_view = df_hist.copy()
        if f_marca != "Todas" and 'marca_ref' in df_view.columns:
            df_view = df_view[df_view['marca_ref'] == f_marca]
        if f_semana != "Todas" and 'semana_ref' in df_view.columns:
            df_view = df_view[df_view['semana_ref'] == f_semana]
            
        titulo = f"Histórico: {f_marca} | {f_semana}"

        # RENDERIZA O DASHBOARD (IGUAL AO OPERACIONAL)
        renderizar_dashboard_completo(df_view, titulo_recorte=titulo)
        
        st.divider()
        with st.expander("🔎 Ver Dados Brutos"):
            st.dataframe(df_view)
        
        if st.button("⚠️ Limpar Planilha Completa"):
            limpar_historico_gsheets()
            st.success("Limpeza concluída!")
            time.sleep(2)
            st.rerun()
