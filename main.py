import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard de Expansão - BI",
    page_icon="🚀",
    layout="wide"
)

# --- ESTILO CSS PERSONALIZADO (Para o visual "Amigável e Bonito") ---
st.markdown("""
<style>
    .big-font { font-size:20px !important; }
    .metric-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# --- TÍTULO E CABEÇALHO ---
st.title("📊 Monitor de Performance de Franquias")
st.markdown("### Visão de Funil, Qualidade de Mídia e Expansão")
st.markdown("---")

# --- BARRA LATERAL (UPLOAD) ---
st.sidebar.header("📂 Configuração")
uploaded_file = st.sidebar.file_uploader("Carregue seu arquivo CSV aqui", type=['csv'])

if uploaded_file is not None:
    # --- CARREGAMENTO E TRATAMENTO DE DADOS (ETL) ---
    try:
        # Tenta ler com separador padrão, se falhar, tenta pular a linha 'sep='
        try:
            df = pd.read_csv(uploaded_file)
            if 'sep=' in str(df.columns[0]):
                df = pd.read_csv(uploaded_file, skiprows=1)
        except:
            df = pd.read_csv(uploaded_file, skiprows=1)

        # 1. Limpeza de Cidades (Extrair nome limpo)
        def clean_city(city):
            if pd.isna(city): return "Desconhecido"
            return str(city).split('-')[0].split('(')[0].strip().title()
        
        if 'Cidade Interesse' in df.columns:
            df['Cidade_Clean'] = df['Cidade Interesse'].apply(clean_city)
            # Remover ruídos (ex: "Nan")
            df = df[df['Cidade_Clean'] != 'Nan']
        
        # 2. Tratamento de Campanhas
        col_campanha = 'Utm_campaign' if 'Utm_campaign' in df.columns else 'Campanha'
        df['Campanha_Clean'] = df[col_campanha].fillna('Orgânico / Direto')

        # 3. Definição da Ordem do Funil
        ordem_funil = [
            'Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 
            'Reunião Agendada', 'Reunião Realizada', 'Follow-up', 'Venda'
        ]
        # Filtra apenas etapas que existem no arquivo para não quebrar o gráfico
        etapas_reais = [e for e in ordem_funil if e in df['Etapa'].unique()]

    except Exception as e:
        st.error(f"Erro ao processar o arquivo. Verifique o formato CSV. Detalhe: {e}")
        st.stop()

    # --- CÁLCULO DE KPIs (Métricas Principais) ---
    total_leads = len(df)
    leads_perdidos = len(df[df['Estado'] == 'Perdida'])
    leads_ativos = total_leads - leads_perdidos
    taxa_perda = (leads_perdidos / total_leads * 100) if total_leads > 0 else 0
    
    # Leads Qualificados (Assumindo que avançou de "Aguardando Resposta")
    qualificados = len(df[df['Etapa'] != 'Aguardando Resposta'])

    # --- EXIBIÇÃO DOS CARDS (KPIs) ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Leads", f"{total_leads}")
    col2.metric("Leads Ativos", f"{leads_ativos}", delta="Pipeline Atual")
    col3.metric("Leads Qualificados", f"{qualificados}", help="Avançaram da etapa inicial")
    col4.metric("Taxa de Perda", f"{taxa_perda:.1f}%", delta_color="inverse")

    st.markdown("---")

    # --- LINHA 1 DE GRÁFICOS: FUNIL E MOTIVOS DE PERDA ---
    col_g1, col_g2 = st.columns([1, 1])

    with col_g1:
        st.subheader("🔻 Funil de Conversão")
        # Contagem por etapa respeitando a ordem lógica
        funil_data = df['Etapa'].value_counts().reindex(etapas_reais).fillna(0).reset_index()
        funil_data.columns = ['Etapa', 'Quantidade']
        
        fig_funnel = px.funnel(funil_data, x='Quantidade', y='Etapa', color_discrete_sequence=['#3498DB'])
        fig_funnel.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_g2:
        st.subheader("🚫 Principais Motivos de Perda")
        loss_data = df[df['Estado'] == 'Perdida']['Motivo de Perda'].value_counts().head(8).reset_index()
        loss_data.columns = ['Motivo', 'Quantidade']
        
        fig_loss = px.bar(loss_data, x='Quantidade', y='Motivo', orientation='h', 
                          text='Quantidade', color='Quantidade', color_continuous_scale='Reds')
        fig_loss.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_loss, use_container_width=True)

    # --- LINHA 2 DE GRÁFICOS: CAMPANHAS E GEOGRAFIA ---
    col_g3, col_g4 = st.columns([1, 1])

    with col_g3:
        st.subheader("📢 Top Campanhas (Volume)")
        camp_data = df['Campanha_Clean'].value_counts().head(10).reset_index()
        camp_data.columns = ['Campanha', 'Leads']
        
        fig_camp = px.bar(camp_data, x='Leads', y='Campanha', orientation='h',
                          color_discrete_sequence=['#2ECC71'])
        fig_camp.update_layout(yaxis={'categoryorder':'total ascending'}, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_camp, use_container_width=True)

    with col_g4:
        st.subheader("🗺️ Top 10 Cidades de Interesse")
        city_data = df['Cidade_Clean'].value_counts().head(10).reset_index()
        city_data.columns = ['Cidade', 'Leads']
        
        fig_city = px.bar(city_data, x='Cidade', y='Leads', 
                          color_discrete_sequence=['#9B59B6'])
        st.plotly_chart(fig_city, use_container_width=True)

    # --- ANÁLISE DETALHADA (TABELA) ---
    with st.expander("🔎 Explorar Dados Brutos"):
        st.dataframe(df)

else:
    # Tela inicial de boas-vindas
    st.info("👋 Olá! Faça o upload do arquivo CSV na barra lateral para gerar o BI.")
    st.markdown("""
        **Este sistema irá analisar automaticamente:**
        - Gargalos do Funil de Vendas
        - Motivos de Perda (Churn Analysis)
        - ROI de Campanhas (Google/Meta)
        - Mapa de Calor Geográfico
    """)
