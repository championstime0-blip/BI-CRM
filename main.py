import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
# Bibliotecas do Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Google Sheets", layout="wide", initial_sidebar_state="expanded")

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

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_gsheets():
    """Conecta ao Google Sheets usando as credenciais dos Secrets"""
    try:
        # Define o escopo de permissão
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # Pega as credenciais direto dos segredos do Streamlit (.streamlit/secrets.toml)
        creds_dict = dict(st.secrets["gsheets"])
        
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Abre a planilha pelo nome (tem que ser EXATAMENTE igual)
        sheet = client.open("BI_Historico").sheet1
        return sheet
    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None

def salvar_no_gsheets(df, semana, marca):
    """Salva os dados na nuvem"""
    sheet = conectar_gsheets()
    if sheet:
        # Prepara os dados
        df_save = df[['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']].copy()
        df_save['semana_ref'] = semana
        df_save['marca_ref'] = marca
        df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Renomeia colunas para ordem certa (Atenção à ordem da planilha!)
        # Ordem: data_upload, semana_ref, marca_ref, etapa, status, cidade, motivo_perda
        df_save = df_save[['data_upload', 'semana_ref', 'marca_ref', 'Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']]
        
        # Converte para lista de listas (formato que o Google aceita)
        dados_lista = df_save.values.tolist()
        
        # Adiciona no final da planilha
        sheet.append_rows(dados_lista)
        return True
    return False

def carregar_historico_gsheets():
    """Lê os dados da nuvem"""
    sheet = conectar_gsheets()
    if sheet:
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    return pd.DataFrame()

def limpar_historico_gsheets():
    """Apaga tudo (mantém o cabeçalho)"""
    sheet = conectar_gsheets()
    if sheet:
        # Apaga da linha 2 até a 10000
        sheet.delete_rows(2, 10000) 
        return True
    return False

# --- FUNÇÕES DE ARQUIVO (LOCAL) ---
@st.cache_data(show_spinner=False)
def load_data(file):
    try:
        file.seek(0)
        df = pd.read_csv(file, sep=';')
        if len(df.columns) > 0 and 'sep=' in str(df.columns[0]):
            file.seek(0)
            df = pd.read_csv(file, sep=';', skiprows=1)
        if df.shape[1] < 2: raise ValueError
    except:
        file.seek(0)
        df = pd.read_csv(file, sep=',')
        if len(df.columns) > 0 and 'sep=' in str(df.columns[0]):
            file.seek(0)
            df = pd.read_csv(file, sep=',', skiprows=1)
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
    else:
        df['Data_Criacao_DT'] = pd.NaT

    if col_fechamento:
        df['Data_Fechamento_DT'] = pd.to_datetime(df[col_fechamento], dayfirst=True, errors='coerce')
    else:
        df['Data_Fechamento_DT'] = pd.NaT

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

# --- INTERFACE PRINCIPAL ---
st.title("📊 BI Corporativo - Nuvem (Google Sheets)")

modo_view = st.radio("Selecione o Modo:", ["📥 Importar Planilha (Operacional)", "🗄️ Histórico Salvo (Gerencial)"], horizontal=True)
st.divider()

# ==============================================================================
# MODO 1: IMPORTAR E SALVAR
# ==============================================================================
if modo_view == "📥 Importar Planilha (Operacional)":
    
    st.sidebar.header("1º Configuração")
    opcoes_marca = ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"]
    marca_selecionada = st.sidebar.selectbox("Operação/Consultor:", opcoes_marca)

    if marca_selecionada == "Selecione...":
        st.info("👋 Selecione uma **Operação** ou **Consultor** na barra lateral.")
        st.stop()

    st.sidebar.divider()
    st.sidebar.header("2º Importação")
    uploaded_file = st.sidebar.file_uploader("Carregar CSV", type=['csv'])

    if uploaded_file is not None:
        with st.status("Processando dados...", expanded=True) as status:
            df_raw = load_data(uploaded_file)
            df = process_data(df_raw)
            
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
                    if not matches.empty:
                        df_filtered = matches
            
            status.update(label="Análise Pronta!", state="complete", expanded=False)

        if 'Etapa' not in df.columns:
            st.error("Erro: Coluna 'Etapa' ausente.")
            st.stop()

        # --- BOTÃO DE SALVAR NA NUVEM ---
        st.sidebar.divider()
        st.sidebar.header("☁️ Salvar na Nuvem")
        semana_ref = st.sidebar.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
        
        if st.sidebar.button("💾 Enviar p/ Google Sheets"):
            with st.spinner("Enviando dados para o Google..."):
                sucesso = salvar_no_gsheets(df_filtered, semana_ref, marca_selecionada)
                if sucesso:
                    st.sidebar.success("✅ Dados salvos com sucesso na Planilha!")
                    time.sleep(2)
                else:
                    st.sidebar.error("❌ Erro ao salvar. Verifique a conexão.")

        # --- DASHBOARD ---
        if pd.notna(df_filtered['Data_Criacao_DT']).any():
            d_min = df_filtered['Data_Criacao_DT'].min()
            d_max = df_filtered['Data_Criacao_DT'].max()
            st.markdown(f"**📅 Recorte:** {d_min.strftime('%d/%m')} a {d_max.strftime('%d/%m')}")

        total = len(df_filtered)
        vendas = len(df_filtered[df_filtered['Status_Calc'] == 'Ganho'])
        perdidos = len(df_filtered[df_filtered['Status_Calc'] == 'Perdido'])
        em_andamento = len(df_filtered[df_filtered['Status_Calc'] == 'Em Andamento'])
        conversao = (vendas / total * 100) if total > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads", total)
        c2.metric("Vendas", vendas, delta=f"{conversao:.1f}%")
        c3.metric("Andamento", em_andamento)
        c4.metric("Perdidos", perdidos, delta_color="inverse")
        
        st.divider()

        tab1, tab2, tab3 = st.tabs(["📢 Fonte", "📉 Funil", "🚫 Perdas"])

        with tab1:
            col_camp1, col_camp2 = st.columns(2)
            with col_camp1:
                st.subheader("Fonte")
                if 'Fonte' in df_filtered.columns:
                    df_fonte = df_filtered['Fonte'].value_counts().reset_index()
                    df_fonte.columns = ['Fonte', 'Leads']
                    fig_fonte = px.pie(df_fonte, values='Leads', names='Fonte', hole=0.4)
                    st.plotly_chart(fig_fonte, use_container_width=True)
            with col_camp2:
                st.subheader("Campanha")
                if 'Campanha' in df_filtered.columns:
                    df_camp = df_filtered['Campanha'].value_counts().head(10).reset_index()
                    df_camp.columns = ['Campanha', 'Leads']
                    fig_camp = px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads')
                    st.plotly_chart(fig_camp, use_container_width=True)

        with tab2:
            st.subheader("Funil")
            df_funil = df_filtered['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=[c for c in ordem if c in df_funil['Etapa'].values], ordered=True)
            df_funil = df_funil.sort_values('Etapa')
            fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa')
            fig_funnel.update_traces(texttemplate='%{value}', textposition='inside')
            st.plotly_chart(fig_funnel, use_container_width=True)

        with tab3:
            st.subheader("Perdas (Filtro Sem Resposta)")
            if 'Motivo de Perda' in df_filtered.columns:
                df_lost = df_filtered[df_filtered['Status_Calc'] == 'Perdido'].copy()
                if not df_lost.empty:
                    mask = (df_lost['Motivo de Perda'] != 'Sem Resposta') | \
                           ((df_lost['Motivo de Perda'] == 'Sem Resposta') & (df_lost['Etapa'] == 'Aguardando Resposta'))
                    df_lost_chart = df_lost[mask]
                    
                    c_l1, c_l2 = st.columns([2,1])
                    with c_l1:
                        motivos = df_lost_chart['Motivo de Perda'].value_counts().reset_index()
                        motivos.columns = ['Motivo', 'Qtd']
                        motivos['Txt'] = motivos.apply(lambda x: f"{x['Qtd']} ({round(x['Qtd']/total*100,1)}%)", axis=1)
                        fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Txt')
                        st.plotly_chart(fig_bar, use_container_width=True)
                    with c_l2:
                        cols = [c for c in ['Etapa', 'Motivo de Perda'] if c in df_lost.columns]
                        st.dataframe(df_lost_chart[cols].head())

# ==============================================================================
# MODO 2: HISTÓRICO GOOGLE SHEETS
# ==============================================================================
elif modo_view == "🗄️ Histórico Salvo (Gerencial)":
    st.markdown("### ☁️ Dados Conectados ao Google Sheets")
    
    with st.spinner("Baixando dados da nuvem..."):
        df_hist = carregar_historico_gsheets()

    if df_hist.empty:
        st.warning("A planilha do Google está vazia ou não foi possível conectar.")
    else:
        # Filtros
        col1, col2 = st.columns(2)
        marcas = ["Todas"] + list(df_hist['marca_ref'].unique())
        f_marca = col1.selectbox("Marca:", marcas)
        
        semanas = ["Todas"] + list(df_hist['semana_ref'].unique())
        f_semana = col2.selectbox("Semana:", semanas)

        df_view = df_hist.copy()
        if f_marca != "Todas": df_view = df_view[df_view['marca_ref'] == f_marca]
        if f_semana != "Todas": df_view = df_view[df_view['semana_ref'] == f_semana]

        st.divider()
        k1, k2, k3 = st.columns(3)
        k1.metric("Total Salvo", len(df_view))
        k2.metric("Vendas", len(df_view[df_view['status'] == 'Ganho']))
        k3.metric("Perdidos", len(df_view[df_view['status'] == 'Perdido']))

        st.subheader("Comparativo Semanal")
        df_evol = df_view.groupby(['semana_ref', 'status']).size().reset_index(name='Qtd')
        fig_evol = px.bar(df_evol, x="semana_ref", y="Qtd", color="status", barmode='group', text='Qtd')
        st.plotly_chart(fig_evol, use_container_width=True)

        with st.expander("Ver Planilha Completa"):
            st.dataframe(df_view)
        
        if st.button("⚠️ Apagar TUDO da Planilha"):
            limpar_historico_gsheets()
            st.success("Planilha limpa!")
            st.rerun()
