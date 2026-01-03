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
            st.error("ERRO: Credenciais não encontradas no Render ou Local.")
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
            
            # Ordem padronizada
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
                'etapa': 'Etapa', 'cidade': 'Cidade_Clean', 'Cidade': 'Cidade_Clean',
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
# 3. PROCESSAMENTO E MOTOR DE VISUALIZAÇÃO
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
    possiveis_criacao = ['Data de criação', 'Created at', 'Data Criação', 'Data']
    for col in df.columns:
        if col in possiveis_criacao: col_criacao = col
    
    if col_criacao:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_criacao], dayfirst=True, errors='coerce')
    else: 
        df['Data_Criacao_DT'] = pd.NaT

    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: 
        df['Cidade_Clean'] = 'Não Informado'
    
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
        with col_m2:
            st.subheader("Campanha")
            if 'Campanha' in df.columns and df['Campanha'].notna().any():
                df_camp = df['Campanha'].value_counts().head(10).reset_index()
                df_camp.columns = ['Campanha', 'Leads']
                fig_camp = px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads')
                st.plotly_chart(fig_camp, use_container_width=True)

    with tab2:
        st.subheader("Funil de Conversão Profissional")
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
                marker = {"color": ["#3498db", "#2980b9", "#1abc9c", "#16a085", "#2ecc71", "#27ae60"]}
            ))
            fig_funnel.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_funnel, use_container_width=True)

    with tab3:
        st.subheader("Motivos de Perda")
        if 'Motivo de Perda' in df.columns:
            df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
            if not df_lost.empty:
                # Regra Sem Resposta
                mask = (df_lost['Motivo de Perda'] != 'Sem Resposta') | \
                       ((df_lost['Motivo de Perda'] == 'Sem Resposta') & (df_lost['Etapa'] == 'Aguardando Resposta'))
                df_l_chart = df_lost[mask]
                
                c_l1, c_l2 = st.columns([2, 1])
                with c_l1:
                    motivos = df_l_chart['Motivo de Perda'].value_counts().reset_index()
                    motivos.columns = ['Motivo', 'Qtd']
                    motivos['Txt'] = motivos.apply(lambda x: f"{x['Qtd']} ({round(x['Qtd']/total*100,1)}%)", axis=1)
                    fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Txt')
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)
                with c_l2:
                    st.write("**Amostra Detalhada:**")
                    st.dataframe(df_l_chart[['Etapa', 'Motivo de Perda']].head(10), use_container_width=True)
            else: 
                st.success("Nenhuma perda registrada neste período.")

# ==============================================================================
# 4. INTERFACE
# ==============================================================================
st.title("📊 BI Corporativo Inteligente")
modo_view = st.radio("Selecione o Modo:", ["📥 Importar Planilha (Operacional)", "🗄️ Histórico Salvo (Gerencial)"], horizontal=True)
st.divider()

if modo_view == "📥 Importar Planilha (Operacional)":
    st.sidebar.header("1º Configuração")
    opcoes_marca = ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"]
    marca_selecionada = st.sidebar.selectbox("Operação/Consultor:", opcoes_marca)
    
    if marca_selecionada == "Selecione...":
        st.info("👋 Selecione a Operação na barra lateral para começar.")
        st.stop()
    
    st.sidebar.divider()
    uploaded_file = st.sidebar.file_uploader("2º Carregar CSV", type=['csv'])
    
    if uploaded_file is not None:
        with st.status("Processando dados...", expanded=True) as status:
            df_raw = load_data(uploaded_file)
            df_p = process_data(df_raw)
            df_f = df_p.copy()
            
            # Filtro de Responsável
            col_resp = next((c for c in df_p.columns if c in ['Proprietário', 'Responsável', 'Consultor', 'Dono do lead']), None)
            if marca_selecionada != "Todas as Marcas" and col_resp:
                termo = marca_selecionada.split(' ')[-1]
                df_f = df_f[df_f[col_resp].astype(str).str.contains(termo, case=False, na=False)]
            
            status.update(label="Processamento Concluído!", state="complete", expanded=False)
        
        st.sidebar.divider()
        semana_ref = st.sidebar.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
        if st.sidebar.button("💾 Enviar p/ Google Sheets"):
            if salvar_no_gsheets(df_f, semana_ref, marca_selecionada):
                st.sidebar.success(f"✅ Dados salvos: {marca_selecionada}!")
        
        renderizar_dashboard_completo(df_f)

elif modo_view == "🗄️ Histórico Salvo (Gerencial)":
    with st.spinner("Conectando ao banco de dados..."):
        df_hist = carregar_historico_gsheets()
    
    if df_hist.empty:
        st.warning("O banco de dados está vazio.")
    else:
        # Preparação de Datas para Filtros
        df_hist['dt'] = pd.to_datetime(df_hist['data_upload'], errors='coerce')
        df_hist['Ano'] = df_hist['dt'].dt.year
        ms_pt = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
        df_hist['M_Num'] = df_hist['dt'].dt.month
        df_hist['M_Nome'] = df_hist['M_Num'].map(ms_pt)
        
        # --- FILTROS EM CASCATA ---
        df_v = df_hist.copy()
        
        # 1. Marca
        marcas = ["Todas"] + sorted(list(df_hist['marca_ref'].unique()))
        sel_m = st.sidebar.selectbox("1. Filtrar Marca:", marcas)
        if sel_m != "Todas": 
            df_v = df_v[df_v['marca_ref'] == sel_m]
        
        # 2. Ano
        anos = sorted(list(df_v['Ano'].dropna().unique()), reverse=True)
        if not anos:
            st.info("Sem dados temporais para esta marca.")
        else:
            sel_a = st.sidebar.selectbox("2. Filtrar Ano:", anos)
            df_v = df_v[df_v['Ano'] == sel_a]
            
            # 3. Mês
            meses_num = sorted(list(df_v['M_Num'].dropna().unique()))
            nomes_m = [ms_pt[m] for m in meses_num]
            if nomes_m:
                sel_mes = st.sidebar.selectbox("3. Filtrar Mês:", nomes_m)
                n_m = [k for k,v in ms_pt.items() if v == sel_mes][0]
                df_v = df_v[df_v['M_Num'] == n_m]
                
                # 4. Semana
                semanas = ["Todas"] + sorted(list(df_v['semana_ref'].unique()))
                sel_s = st.sidebar.selectbox("4. Filtrar Semana:", semanas)
                if sel_s != "Todas": 
                    df_v = df_v[df_v['semana_ref'] == sel_s]
                
                renderizar_dashboard_completo(df_v, titulo_recorte=f"Visão Gerencial: {sel_m} | {sel_mes}/{sel_a}")
        
        st.divider()
        if st.button("⚠️ Limpar Histórico Completo"):
            if limpar_historico_gsheets():
                st.success("Histórico apagado com sucesso!")
                time.sleep(1)
                st.rerun()
