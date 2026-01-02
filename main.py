import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
# O matplotlib é usado internamente pelo Pandas para colorir a tabela
import matplotlib.pyplot as plt 

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Avançado - Franquias", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 24px;
        color: #0E1117;
    }
    .st-emotion-cache-1r6slb0 {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO DE DADOS ---
@st.cache_data
def load_data(file):
    try:
        file.seek(0)
        df = pd.read_csv(file, sep=';')
        # Tratamento para separador incorreto
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

def clean_data(df):
    # 1. Padronizar Campanhas
    if 'Utm_campaign' in df.columns: df['Campanha_Clean'] = df['Utm_campaign'].fillna('Orgânico/Desconhecido')
    elif 'Campanha' in df.columns: df['Campanha_Clean'] = df['Campanha'].fillna('Desconhecido')
    else: df['Campanha_Clean'] = 'Não Identificado'

    # 2. Padronizar Cidades
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # 3. Lógica Inteligente de Status (SEM COLUNA ESTADO)
    def deduzir_status(row):
        # Se tem motivo de perda preenchido, é Perdido
        motivo = str(row.get('Motivo de Perda', ''))
        if motivo != '' and motivo.lower() != 'nan' and motivo.lower() != 'nat': 
            return 'Perdido'
        
        # Se a etapa sugere fechamento, é Ganho
        etapa = str(row.get('Etapa', '')).lower()
        if 'venda' in etapa or 'fechamento' in etapa or 'matricula' in etapa:
            return 'Ganho'
            
        return 'Em Aberto'

    df['Status_Calc'] = df.apply(deduzir_status, axis=1)
        
    return df

# --- INTERFACE ---
st.title("📊 BI Estratégico de Expansão")
st.markdown("Análise focada em Cidades de Interesse e Conversão.")

uploaded_file = st.sidebar.file_uploader("📂 Carregar CSV", type=['csv'])

if uploaded_file is not None:
    try:
        df_raw = load_data(uploaded_file)
        
        if 'Etapa' not in df_raw.columns:
            st.error("O arquivo precisa ter pelo menos a coluna 'Etapa'.")
            st.stop()
            
        df = clean_data(df_raw)

        # --- FILTRO PRINCIPAL: CIDADE ---
        st.sidebar.header("Filtros")
        cidades = ['Todas'] + sorted(list(df['Cidade_Clean'].unique()))
        filtro_cidade = st.sidebar.selectbox("Filtrar por Cidade de Interesse", cidades)
        
        # Filtra os dados
        df_filtered = df.copy()
        if filtro_cidade != 'Todas':
            df_filtered = df_filtered[df_filtered['Cidade_Clean'] == filtro_cidade]

        # --- KPIS ---
        total = len(df_filtered)
        vendas = len(df_filtered[df_filtered['Status_Calc'] == 'Ganho'])
        perdidos = len(df_filtered[df_filtered['Status_Calc'] == 'Perdido'])
        ativos = total - vendas - perdidos
        
        conversao = (vendas / total * 100) if total > 0 else 0
        perda_perc = (perdidos / total * 100) if total > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads na Seleção", total)
        c2.metric("Vendas Estimadas", vendas, delta=f"{conversao:.1f}% Conv.")
        c3.metric("Em Andamento", ativos)
        c4.metric("Perdidos (c/ Motivo)", perdidos, delta=f"-{perda_perc:.1f}%", delta_color="inverse")
        
        st.divider()

        # --- ABAS ---
        tab1, tab2, tab3 = st.tabs(["📉 Funil", "📢 Campanhas", "🚫 Perdas"])

        # TAB 1: FUNIL
        with tab1:
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                st.subheader("Volume por Etapa")
                # Defina aqui a ordem correta das suas etapas
                ordem_ideal = [
                    'Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 
                    'Reunião Agendada', 'Reunião Realizada', 'Follow-up', 'Venda/Fechamento'
                ]
                etapas_presentes = [e for e in ordem_ideal if e in df_filtered['Etapa'].unique()]
                
                if not etapas_presentes:
                    etapas_presentes = df_filtered['Etapa'].unique()

                df_funil = df_filtered['Etapa'].value_counts().reindex(etapas_presentes).fillna(0).reset_index()
                df_funil.columns = ['Etapa', 'Volume']
                
                fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa', text='Volume')
                st.plotly_chart(fig_funnel, use_container_width=True)

            with col_f2:
                st.subheader("Dados Detalhados (Heatmap)")
                # RECURSO VISUAL: Tabela com gradiente de cor (Requer Matplotlib)
                try:
                    st.dataframe(
                        df_funil.set_index('Etapa').style.background_gradient(cmap="Blues", subset=['Volume']),
                        use_container_width=True
                    )
                except Exception:
                    # Fallback caso o matplotlib falhe por algum motivo
                    st.dataframe(df_funil, use_container_width=True)

        # TAB 2: CAMPANHAS (MATRIZ)
        with tab2:
            st.subheader("Performance de Campanhas")
            df_mkt = df_filtered.groupby('Campanha_Clean').agg(
                Leads=('Etapa', 'count'),
                Vendas=('Status_Calc', lambda x: (x == 'Ganho').sum())
            ).reset_index()
            
            df_mkt['Conversao'] = ((df_mkt['Vendas'] / df_mkt['Leads']) * 100).round(1)
            
            # Gráfico de Bolhas: Tamanho da bolha = Volume de Leads
            fig_scat = px.scatter(
                df_mkt, x='Leads', y='Conversao', size='Leads', color='Campanha_Clean',
                title="Volume (X) vs Conversão (Y)", hover_name='Campanha_Clean',
                labels={'Leads': 'Volume de Leads', 'Conversao': 'Taxa de Conversão (%)'}
            )
            # Adiciona linha média
            media = df_mkt['Conversao'].mean()
            fig_scat.add_hline(y=media, line_dash="dot", annotation_text="Média Conversão")
            
            st.plotly_chart(fig_scat, use_container_width=True)

        # TAB 3: PERDAS
        with tab3:
            st.subheader("Análise de Motivos de Perda")
            if 'Motivo de Perda' in df_filtered.columns:
                df_lost = df_filtered[df_filtered['Status_Calc'] == 'Perdido']
                
                if not df_lost.empty:
                    loss_data = df_lost['Motivo de Perda'].value_counts().reset_index()
                    loss_data.columns = ['Motivo', 'Qtd']
                    
                    fig_bar = px.bar(loss_data, x='Qtd', y='Motivo', orientation='h', text='Qtd', title="Principais Motivos")
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Nenhum lead com 'Motivo de Perda' preenchido nesta seleção.")
            else:
                st.warning("A coluna 'Motivo de Perda' não foi encontrada no arquivo.")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.info("Aguardando upload do CSV...")
