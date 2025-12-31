import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. Configuração da Página (DEVE ser o primeiro comando) ---
st.set_page_config(page_title="Franquias BI", layout="wide")

# --- CSS Customizado ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    h1, h2, h3 { color: #0E1117; }
</style>
""", unsafe_allow_html=True)

# --- Título e Upload ---
st.title("🚀 Dashboard de Inteligência Comercial")
st.markdown("### Análise de Funil e Performance de Marketing")

uploaded_file = st.sidebar.file_uploader("Carregar Base de Dados (CSV)", type=['csv'])

if uploaded_file is not None:
    # --- 2. Leitura Robusta do Arquivo (Correção do Erro de Parser) ---
    try:
        # TENTATIVA 1: Padrão Brasileiro (Ponto e Vírgula)
        uploaded_file.seek(0) # Garante que está no início do arquivo
        df = pd.read_csv(uploaded_file, sep=';')
        
        # Validação: Se criou apenas 1 coluna, provavelmente o separador está errado
        if df.shape[1] < 2:
            raise ValueError("Separador incorreto detectado")
            
    except Exception:
        # TENTATIVA 2: Padrão Internacional (Vírgula)
        uploaded_file.seek(0) # Reseta o ponteiro para o início (CRUCIAL)
        df = pd.read_csv(uploaded_file, sep=',')

    # --- 3. Verificação de Colunas Obrigatórias ---
    # Adapte esta lista conforme os nomes exatos do seu CSV
    colunas_necessarias = ['Etapa', 'Estado'] 
    colunas_presentes = [c for c in colunas_necessarias if c in df.columns]
    
    if len(colunas_presentes) != len(colunas_necessarias):
        st.error(f"O arquivo CSV precisa ter as colunas: {colunas_necessarias}. Colunas encontradas: {list(df.columns)}")
        st.stop()

    # --- 4. Limpeza e Tratamento (ETL) ---
    
    # Ordem Lógica do Funil
    ordem_funil = [
        'Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 
        'Reunião Agendada', 'Reunião Realizada', 'Follow-up', 'Venda/Fechamento'
    ]
    # Filtra apenas etapas que existem no dataset
    etapas_existentes = [e for e in ordem_funil if e in df['Etapa'].unique()]
    
    # Tratamento de Campanhas (Verifica qual coluna existe)
    if 'Utm_campaign' in df.columns:
        df['Campanha_Clean'] = df['Utm_campaign'].fillna('Orgânico/Desconhecido')
    elif 'Campanha' in df.columns:
        df['Campanha_Clean'] = df['Campanha'].fillna('Desconhecido')
    else:
        df['Campanha_Clean'] = 'Não Identificado'

    # Tratamento de Cidades
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(
            lambda x: x.split('-')[0].split('(')[0].strip().title()
        )
        df = df[df['Cidade_Clean'] != 'Nan'] # Remove strings NaN literais
    else:
        df['Cidade_Clean'] = 'Não Informado'

    # --- 5. Cálculo de KPIs ---
    total_leads = len(df)
    # Verifica se existe coluna Estado para calcular ativos/perdidos
    if 'Estado' in df.columns:
        leads_ativos = len(df[~df['Estado'].astype(str).str.contains('Perdida', case=False, na=False)])
        leads_perdidos = total_leads - leads_ativos
        taxa_perda = (leads_perdidos / total_leads * 100) if total_leads > 0 else 0
    else:
        leads_ativos = total_leads
        taxa_perda = 0

    # --- Exibição dos KPIs ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Leads", f"{total_leads}")
    col2.metric("Leads Ativos", f"{leads_ativos}")
    col3.metric("Taxa de Perda", f"{taxa_perda:.1f}%", delta_color="inverse")

    st.markdown("---")

    # --- 6. Gráficos ---
    
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("🔻 Funil de Vendas")
        if etapas_existentes:
            df_funil = df['Etapa'].value_counts().reindex(etapas_existentes).fillna(0).reset_index()
            df_funil.columns = ['Etapa', 'Quantidade']
            fig_funnel = px.funnel(df_funil, x='Quantidade', y='Etapa', color_discrete_sequence=['#2E86C1'])
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.warning("As etapas do funil não correspondem à ordem configurada.")

    with col_g2:
        st.subheader("🚫 Motivos de Perda")
        if 'Motivo de Perda' in df.columns and 'Estado' in df.columns:
            df_loss = df[df['Estado'] == 'Perdida']['Motivo de Perda'].value_counts().reset_index().head(10)
            df_loss.columns = ['Motivo', 'Quantidade']
            fig_loss = px.bar(df_loss, x='Quantidade', y='Motivo', orientation='h', color='Quantidade', color_continuous_scale='Reds')
            fig_loss.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_loss, use_container_width=
