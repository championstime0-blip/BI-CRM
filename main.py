import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import sqlite3

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Multi-Marcas SQL", layout="wide", initial_sidebar_state="expanded")

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

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect('bi_historico.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS historico_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            semana_ref TEXT,
            marca_ref TEXT,
            etapa TEXT,
            status TEXT,
            cidade TEXT,
            motivo_perda TEXT
        )
    ''')
    conn.commit()
    conn.close()

def salvar_no_banco(df, semana, marca):
    conn = sqlite3.connect('bi_historico.db')
    df_save = df[['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda']].copy()
    df_save['semana_ref'] = semana
    df_save['marca_ref'] = marca
    df_save.rename(columns={'Status_Calc': 'status', 'Cidade_Clean': 'cidade', 'Motivo de Perda': 'motivo_perda', 'Etapa': 'etapa'}, inplace=True)
    df_save.to_sql('historico_leads', conn, if_exists='append', index=False)
    conn.close()
    return True

def carregar_historico():
    conn = sqlite3.connect('bi_historico.db')
    df = pd.read_sql("SELECT * FROM historico_leads", conn)
    conn.close()
    return df

def limpar_banco():
    conn = sqlite3.connect('bi_historico.db')
    c = conn.cursor()
    c.execute("DELETE FROM historico_leads")
    conn.commit()
    conn.close()

init_db()

# --- CARREGAMENTO DO CSV ---
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
st.title("📊 BI Corporativo - Gestão Integrada")

# MODO DE VISUALIZAÇÃO (NOVO)
modo_view = st.radio("Selecione o Modo de Visão:", ["📥 Importar Planilha (Operacional)", "🗄️ Histórico Salvo (Gerencial)"], horizontal=True)
st.divider()

# ==============================================================================
# MODO 1: IMPORTAR PLANILHA (O CÓDIGO ANTIGO FICA AQUI)
# ==============================================================================
if modo_view == "📥 Importar Planilha (Operacional)":
    
    st.sidebar.header("1º Configuração Inicial")
    opcoes_marca = ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"]
    marca_selecionada = st.sidebar.selectbox("Operação/Consultor:", opcoes_marca)

    if marca_selecionada == "Selecione...":
        st.info("👋 Para começar, selecione uma **Operação** ou **Consultor** na barra lateral.")
        st.stop()

    st.sidebar.divider()
    st.sidebar.header("2º Importação")
    uploaded_file = st.sidebar.file_uploader("Carregar Planilha CSV", type=['csv'])

    if uploaded_file is not None:
        with st.status("Processando inteligência...", expanded=True) as status:
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
            
            status.update(label="Análise Concluída!", state="complete", expanded=False)

        if 'Etapa' not in df.columns:
            st.error("Erro: Coluna 'Etapa' não encontrada.")
            st.stop()

        # BANCO DE DADOS - SAVE
        st.sidebar.divider()
        st.sidebar.header("💾 Salvar Histórico")
        semana_ref = st.sidebar.selectbox("Semana de Referência:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
        
        if st.sidebar.button("💾 Gravar no Banco de Dados"):
            try:
                salvar_no_banco(df_filtered, semana_ref, marca_selecionada)
                st.sidebar.success(f"Dados salvos: {marca_selecionada} | {semana_ref}")
                time.sleep(2)
            except Exception as e:
                st.sidebar.error(f"Erro ao salvar: {e}")

        # DASHBOARD OPERACIONAL
        if pd.notna(df_filtered['Data_Criacao_DT']).any():
            d_min = df_filtered['Data_Criacao_DT'].min()
            d_max = df_filtered['Data_Criacao_DT'].max()
            st.markdown(f"**📅 Recorte Analisado:** de {d_min.strftime('%d/%m')} a {d_max.strftime('%d/%m')}")

        total = len(df_filtered)
        vendas = len(df_filtered[df_filtered['Status_Calc'] == 'Ganho'])
        perdidos = len(df_filtered[df_filtered['Status_Calc'] == 'Perdido'])
        em_andamento = len(df_filtered[df_filtered['Status_Calc'] == 'Em Andamento'])
        conversao = (vendas / total * 100) if total > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads Filtrados", total)
        c2.metric("Vendas (Ganhos)", vendas, delta=f"{conversao:.1f}% Conv.")
        c3.metric("Em Andamento", em_andamento)
        c4.metric("Perdidos", perdidos, delta_color="inverse")
        
        st.divider()

        tab1, tab2, tab3 = st.tabs(["📢 Fonte & Campanha", "📉 Funil", "🚫 Detalhe de Perdas"])

        with tab1:
            col_camp1, col_camp2 = st.columns(2)
            with col_camp1:
                st.subheader("Performance por Fonte")
                if 'Fonte' in df_filtered.columns:
                    df_fonte = df_filtered['Fonte'].value_counts().reset_index()
                    df_fonte.columns = ['Fonte', 'Leads']
                    fig_fonte = px.pie(df_fonte, values='Leads', names='Fonte', hole=0.4)
                    st.plotly_chart(fig_fonte, use_container_width=True)
                else: st.warning("Coluna 'Fonte' ausente.")

            with col_camp2:
                st.subheader("Performance por Campanha")
                if 'Campanha' in df_filtered.columns:
                    df_camp = df_filtered['Campanha'].value_counts().head(10).reset_index()
                    df_camp.columns = ['Campanha', 'Leads']
                    fig_camp = px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads')
                    fig_camp.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_camp, use_container_width=True)
                else: st.warning("Coluna 'Campanha' ausente.")
            
            if 'Fonte' in df_filtered.columns and 'Campanha' in df_filtered.columns:
                st.subheader("Matriz: Fonte vs Campanha")
                pivot_camp = pd.crosstab(df_filtered['Fonte'], df_filtered['Campanha'])
                st.dataframe(pivot_camp, use_container_width=True)

        with tab2:
            st.subheader("Funil de Vendas")
            df_funil = df_filtered['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            ordem_ideal = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=[c for c in ordem_ideal if c in df_funil['Etapa'].values], ordered=True)
            df_funil = df_funil.sort_values('Etapa')
            fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa')
            fig_funnel.update_traces(texttemplate='%{value}', textposition='inside')
            st.plotly_chart(fig_funnel, use_container_width=True)

        with tab3:
            st.subheader("Análise de Perdas (Regra Aplicada)")
            if 'Motivo de Perda' in df_filtered.columns:
                df_lost = df_filtered[df_filtered['Status_Calc'] == 'Perdido'].copy()
                if not df_lost.empty:
                    mask_valido = (df_lost['Motivo de Perda'] != 'Sem Resposta') | \
                                  ((df_lost['Motivo de Perda'] == 'Sem Resposta') & (df_lost['Etapa'] == 'Aguardando Resposta'))
                    df_lost_chart = df_lost[mask_valido]
                    c_loss1, c_loss2 = st.columns([2, 1])
                    with c_loss1:
                        motivos = df_lost_chart['Motivo de Perda'].value_counts().reset_index()
                        motivos.columns = ['Motivo', 'Qtd']
                        motivos['Percent'] = (motivos['Qtd'] / total * 100).round(1)
                        motivos['Texto_Barra'] = motivos.apply(lambda x: f"{x['Qtd']} ({x['Percent']}%)", axis=1)
                        fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Texto_Barra', title="Principais Motivos")
                        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_bar, use_container_width=True)
                    with c_loss2:
                        st.write("**Amostra (Filtrada):**")
                        cols_show = [c for c in ['Etapa', 'Motivo de Perda', 'Data_Criacao_DT'] if c in df_lost.columns]
                        st.dataframe(df_lost_chart[cols_show].head(5), use_container_width=True)
                else: st.success("Sem perdas.")
            else: st.warning("Coluna 'Motivo de Perda' não encontrada.")
    else:
        st.info("👈 Selecione a Operação e faça o Upload do CSV.")

# ==============================================================================
# MODO 2: HISTÓRICO SALVO (NOVO DASHBOARD GERENCIAL)
# ==============================================================================
elif modo_view == "🗄️ Histórico Salvo (Gerencial)":
    
    st.markdown("### 🗄️ Banco de Dados de Leads")
    df_hist = carregar_historico()

    if df_hist.empty:
        st.warning("O banco de dados está vazio. Vá para a aba 'Importar Planilha', carregue um CSV e clique em 'Gravar no Banco'.")
    else:
        # Filtros do Histórico
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            marcas_db = ["Todas"] + list(df_hist['marca_ref'].unique())
            filtro_marca_db = st.selectbox("Filtrar Marca:", marcas_db)
        with col_h2:
            semanas_db = ["Todas"] + list(df_hist['semana_ref'].unique())
            filtro_semana_db = st.selectbox("Filtrar Semana:", semanas_db)

        # Aplica filtros
        df_hist_view = df_hist.copy()
        if filtro_marca_db != "Todas":
            df_hist_view = df_hist_view[df_hist_view['marca_ref'] == filtro_marca_db]
        if filtro_semana_db != "Todas":
            df_hist_view = df_hist_view[df_hist_view['semana_ref'] == filtro_semana_db]

        # KPIs do Banco
        st.divider()
        tot_hist = len(df_hist_view)
        vendas_hist = len(df_hist_view[df_hist_view['status'] == 'Ganho'])
        perdidos_hist = len(df_hist_view[df_hist_view['status'] == 'Perdido'])
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Armazenado", tot_hist)
        c2.metric("Total Vendas", vendas_hist)
        c3.metric("Total Perdidos", perdidos_hist)

        # Visualização Comparativa
        st.subheader("📈 Evolução por Semana")
        
        # Agrupa dados por Semana e Status
        df_evolucao = df_hist_view.groupby(['semana_ref', 'status']).size().reset_index(name='Qtd')
        
        fig_evol = px.bar(df_evolucao, x="semana_ref", y="Qtd", color="status", 
                          title="Comparativo Semanal (Vendas vs Perdas)",
                          barmode='group', text='Qtd')
        st.plotly_chart(fig_evol, use_container_width=True)

        # Visualização da Tabela Bruta
        with st.expander("🔎 Ver Tabela Completa do Banco de Dados"):
            st.dataframe(
