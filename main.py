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
# 1. MOTOR DE CONEXÃO (BLINDADO)
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
            st.error("ERRO: Nenhuma credencial encontrada (Local ou Nuvem).")
            return None
        
        client = gspread.authorize(creds)
        # Tenta abrir a planilha
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
            # Seleciona colunas essenciais + Fonte/Campanha se existirem
            cols_save = ['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']
            
            # Garante que Fonte e Campanha existam no DF, mesmo que vazios
            if 'Fonte' not in df.columns: df['Fonte'] = '-'
            if 'Campanha' not in df.columns: df['Campanha'] = '-'
            cols_save.extend(['Fonte', 'Campanha'])

            df_save = df[cols_save].copy()
            df_save['semana_ref'] = semana
            df_save['marca_ref'] = marca
            df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Reordena para ficar organizado na planilha
            df_save = df_save[['data_upload', 'semana_ref', 'marca_ref', 'Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda', 'Fonte', 'Campanha']]
            
            # Preenche vazios com traço para não quebrar o Google Sheets
            df_save = df_save.fillna('-')
            
            dados_lista = df_save.values.tolist()
            sheet.append_rows(dados_lista)
            return True
        except Exception as e:
            st.error(f"Erro ao gravar dados: {e}")
            return False
    return False

def carregar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            st.warning(f"Planilha vazia ou erro de leitura: {e}")
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
    # Tratamento de Datas
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

    # Tratamento de Cidade
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # Lógica de Status (A Regra de Ouro)
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
# 3. MOTOR DE VISUALIZAÇÃO (O SEGREDO PARA SEREM IGUAIS)
# ==============================================================================
def renderizar_dashboard_completo(df, titulo_recorte="Recorte de Dados"):
    """
    Esta função desenha o dashboard inteiro.
    Usada tanto para o CSV importado quanto para o Histórico.
    """
    # 1. KPIs
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

    # 2. Abas Gráficas
    tab1, tab2, tab3 = st.tabs(["📢 Fonte & Campanha", "📉 Funil de Vendas", "🚫 Análise de Perdas"])

    # --- ABA 1: MARKETING ---
    with tab1:
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.subheader("Fonte")
            if 'Fonte' in df.columns and df['Fonte'].notna().any():
                df_fonte = df['Fonte'].value_counts().reset_index()
                df_fonte.columns = ['Fonte', 'Leads']
                fig_fonte = px.pie(df_fonte, values='Leads', names='Fonte', hole=0.4)
                st.plotly_chart(fig_fonte, use_container_width=True)
            else:
                st.info("Dados de 'Fonte' não disponíveis.")

        with col_m2:
            st.subheader("Campanha")
            if 'Campanha' in df.columns and df['Campanha'].notna().any():
                df_camp = df['Campanha'].value_counts().head(10).reset_index()
                df_camp.columns = ['Campanha', 'Leads']
                fig_camp = px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads')
                st.plotly_chart(fig_camp, use_container_width=True)
            else:
                st.info("Dados de 'Campanha' não disponíveis.")
        
        # Matriz (se houver dados suficientes)
        if 'Fonte' in df.columns and 'Campanha' in df.columns:
            st.caption("Cruzamento Fonte x Campanha")
            try:
                pivot = pd.crosstab(df['Fonte'], df['Campanha'])
                st.dataframe(pivot, use_container_width=True)
            except: pass

    # --- ABA 2: FUNIL ---
    with tab2:
        st.subheader("Funil de Conversão")
        if 'Etapa' in df.columns:
            df_funil = df['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            
            # Ordem lógica sugerida
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            # Cria categoria ordenada apenas com as etapas que existem nos dados
            etapas_existentes = [c for c in ordem if c in df_funil['Etapa'].values]
            # Adiciona etapas extras que não estão na lista padrão no final
            extras = [c for c in df_funil['Etapa'].values if c not in ordem]
            ordem_final = etapas_existentes + extras
            
            df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=ordem_final, ordered=True)
            df_funil = df_funil.sort_values('Etapa')
            
            fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa')
            fig_funnel.update_traces(texttemplate='%{value}', textposition='inside')
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.warning("Coluna 'Etapa' não encontrada.")

    # --- ABA 3: PERDAS (COM REGRA SEM RESPOSTA) ---
    with tab3:
        st.subheader("Motivos de Perda")
        if 'Motivo de Perda' in df.columns:
            df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
            if not df_lost.empty:
                # Regra de Ouro: Sem Resposta só conta se Etapa == Aguardando Resposta
                mask_valido = (df_lost['Motivo de Perda'] != 'Sem Resposta') | \
                              ((df_lost['Motivo de Perda'] == 'Sem Resposta') & (df_lost['Etapa'] == 'Aguardando Resposta'))
                
                df_lost_chart = df_lost[mask_valido]
                
                # Feedback sobre filtro
                ocultos = len(df_lost) - len(df_lost_chart)
                if ocultos > 0:
                    st.caption(f"ℹ️ {ocultos} leads com 'Sem Resposta' em etapas avançadas foram ocultados para limpeza visual.")

                c_loss1, c_loss2 = st.columns([2, 1])
                with c_loss1:
                    motivos = df_lost_chart['Motivo de Perda'].value_counts().reset_index()
                    motivos.columns = ['Motivo', 'Qtd']
                    
                    # Percentual sobre o TOTAL (não só perdidos)
                    motivos['Percent'] = (motivos['Qtd'] / total * 100).round(1)
                    motivos['Texto'] = motivos.apply(lambda x: f"{x['Qtd']} ({x['Percent']}%)", axis=1)
                    
                    fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Texto', title="Top Motivos")
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)
                
                with c_loss2:
                    st.write("**Amostra de Dados:**")
                    cols_ver = [c for c in ['Etapa', 'Motivo de Perda', 'Data_Criacao_DT'] if c in df_lost.columns]
                    st.dataframe(df_lost_chart[cols_ver].head(10), use_container_width=True)
            else:
                st.success("Parabéns! Nenhuma perda registrada neste recorte.")
        else:
            st.warning("Coluna 'Motivo de Perda' ausente.")


# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("📊 BI Corporativo Inteligente")

# Seletor de Modo no Topo
modo_view = st.radio("Selecione o Modo:", ["📥 Importar Planilha (Operacional)", "🗄️ Histórico Salvo (Gerencial)"], horizontal=True)
st.divider()

# ------------------------------------------------------------------------------
# MODO 1: IMPORTAR E SALVAR
# ------------------------------------------------------------------------------
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
        # Processamento
        with st.status("Processando inteligência de dados...", expanded=True) as status:
            df_raw = load_data(uploaded_file)
            df = process_data(df_raw)
            
            # Filtro de Marca Inteligente
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
            
            status.update(label="Pronto!", state="complete", expanded=False)

        if 'Etapa' not in df.columns:
            st.error("Erro: Coluna 'Etapa' ausente.")
            st.stop()

        # Botão de Salvar
        st.sidebar.divider()
        st.sidebar.header("☁️ Salvar na Nuvem")
        semana_ref = st.sidebar.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
        
        if st.sidebar.button("💾 Enviar p/ Google Sheets"):
            with st.spinner("Enviando dados..."):
                if salvar_no_gsheets(df_filtered, semana_ref, marca_selecionada):
                    st.sidebar.success("✅ Salvo com sucesso!")
                    time.sleep(2)
                else:
                    st.sidebar.error("❌ Falha ao salvar.")

        # Recorte de Data (Visual)
        texto_recorte = "Análise Atual"
        if pd.notna(df_filtered['Data_Criacao_DT']).any():
            d_min = df_filtered['Data_Criacao_DT'].min()
            d_max = df_filtered['Data_Criacao_DT'].max()
            texto_recorte = f"Recorte: {d_min.strftime('%d/%m')} a {d_max.strftime('%d/%m')}"

        # === CHAMADA DO MOTOR DE VISUALIZAÇÃO ===
        renderizar_dashboard_completo(df_filtered, titulo_recorte=texto_recorte)


# ------------------------------------------------------------------------------
# MODO 2: HISTÓRICO GERENCIAL (AGORA COM VISUAL IGUAL)
# ------------------------------------------------------------------------------
elif modo_view == "🗄️ Histórico Salvo (Gerencial)":
    
    st.sidebar.header("Filtros do Histórico")
    
    with st.spinner("Conectando ao Google Sheets..."):
        df_hist = carregar_historico_gsheets()

    if df_hist.empty:
        st.warning("O banco de dados (Planilha) está vazio ou inacessível no momento.")
    else:
        # Filtros laterais para o Histórico
        marcas_disp = ["Todas"] + sorted(list(df_hist['marca_ref'].unique()))
        semanas_disp = ["Todas"] + sorted(list(df_hist['semana_ref'].unique()))
        
        f_marca = st.sidebar.selectbox("Filtrar Marca:", marcas_disp)
        f_semana = st.sidebar.selectbox("Filtrar Semana:", semanas_disp)
        
        # Aplicação dos Filtros
        df_view = df_hist.copy()
        if f_marca != "Todas":
            df_view = df_view[df_view['marca_ref'] == f_marca]
        if f_semana != "Todas":
            df_view = df_view[df_view['semana_ref'] == f_semana]
            
        # Título Dinâmico
        titulo = f"Histórico: {f_marca} - {f_semana}"

        # === CHAMADA DO MOTOR DE VISUALIZAÇÃO (A MÁGICA ACONTECE AQUI) ===
        # Passamos o dataframe do histórico filtrado para a mesma função que desenha o dashboard operacional
        renderizar_dashboard_completo(df_view, titulo_recorte=titulo)
        
        st.divider()
        with st.expander("🔎 Ver Tabela Bruta (Dados do Google Sheets)"):
            st.dataframe(df_view)
        
        col_del1, col_del2 = st.columns([4,1])
        with col_del2:
            if st.button("⚠️ Limpar Histórico Completo"):
                if limpar_historico_gsheets():
                    st.success("Histórico apagado!")
                    time.sleep(2)
                    st.rerun()
