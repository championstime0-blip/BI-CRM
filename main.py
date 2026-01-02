import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 1. Configuração da Página (DEVE ser o primeiro comando) ---
st.set_page_config(page_title="Franquias BI", layout="wide")

# --- CSS Customizado para Estilo ---
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
    # --- 2. Leitura Inteligente do Arquivo ---
    try:
        # TENTATIVA 1: Separador Ponto e Vírgula (Padrão Excel BR)
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=';')
        
        # Correção para arquivos que começam com "sep=;"
        if len(df.columns) > 0 and 'sep=' in str(df.columns[0]):
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';', skiprows=1)

        # Validação
        if df.shape[1] < 2:
            raise ValueError("Tentando outro separador...")
            
    except Exception:
        # TENTATIVA 2: Separador Vírgula (Padrão Internacional)
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, sep=',')
            if len(df.columns) > 0 and 'sep=' in str(df.columns[0]):
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=',', skiprows=1)
        except Exception as e:
            st.error(f"Não foi possível ler o arquivo. Erro: {e}")
            st.stop()

    # --- 3. Verificação de Colunas Obrigatórias ---
    colunas_necessarias = ['Etapa', 'Estado'] 
    colunas_presentes = [c for c in colunas_necessarias if c in df.columns]
    
    if len(colunas_presentes) != len(colunas_necessarias):
        st.error(f"""
        ❌ **Erro de Colunas:** O arquivo precisa ter as colunas: {colunas_necessarias}.
        **Colunas encontradas:** {list(df.columns)}
        """)
        st.stop()

    # --- 4. Limpeza e Tratamento de Dados (ETL) ---
    ordem_funil = [
        'Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 
        'Reunião Agendada', 'Reunião Realizada', 'Follow-up', 'Venda/Fechamento'
    ]
    etapas_existentes = [e for e in ordem_funil if e in df['Etapa'].unique()]
    
    if 'Utm_campaign' in df.columns:
        df['Campanha_Clean'] = df['Utm_campaign'].fillna('Orgânico/Desconhecido')
    elif 'Campanha' in df.columns:
        df['Campanha_Clean'] = df['Campanha'].fillna('Desconhecido')
    else:
        df['Campanha_Clean'] = 'Não Identificado'

    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(
            lambda x: x.split('-')[0].split('(')[0].strip().title()
        )
        df = df[df['Cidade_Clean'] != 'Nan']
    else:
        df['Cidade_Clean'] = 'Não Informado'

    # --- 5. Cálculo de KPIs ---
    total_leads = len(df)
    leads_ativos = len(df[~df['Estado'].astype(str).str.contains('Perdida', case=False, na=False)])
    leads_perdidos = total_leads - leads_ativos
    taxa_perda = (leads_perdidos / total_leads * 100) if total_leads > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Leads", f"{total_leads}")
    col2.metric("Leads Ativos", f"{leads_ativos}")
    col3.metric("Taxa de Perda", f"{taxa_perda:.1f}%", delta_color="inverse")

    st.markdown("---")

    # --- 6. Gráficos ---
    col_g1, col_g2 = st.columns(2)

    # Gráfico 1: Funil
    with col_g1:
        st.subheader("🔻 Funil de Vendas")
        if etapas_existentes:
            df_funil = df['Etapa'].value_counts().reindex(etapas_existentes).fillna(0).reset_index()
            df_funil.columns = ['Etapa', 'Quantidade']
            fig_funnel = px.funnel(df_funil, x='Quantidade', y='Etapa', color_discrete_sequence=['#2E86C1'])
            # Funil geralmente fica melhor com número dentro, mas podemos forçar se quiser
            fig_funnel.update_traces(textinfo="value+percent initial") 
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.warning("As etapas do funil não correspondem à ordem configurada.")

    # Gráfico 2: Motivos de Perda (COM TOTAL NA FRENTE)
    with col_g2:
        st.subheader("🚫 Raio-X das Perdas (Por Etapa)")
        
        if 'Motivo de Perda' in df.columns and 'Estado' in df.columns:
            df_lost = df[df['Estado'].astype(str).str.contains('Perdida', case=False, na=False)].copy()
            
            if not df_lost.empty:
                # Dados detalhados para as cores (segmentos)
                df_loss_detailed = df_lost.groupby(['Etapa', 'Motivo de Perda']).size().reset_index(name='Quantidade')
                
                # Cálculo do TOTAL por etapa para exibir na frente da barra
                df_loss_totals = df_lost.groupby('Etapa').size().reset_index(name='Total')

                # Cria o gráfico de barras empilhadas
                fig_loss = px.bar(
                    df_loss_detailed, 
                    y='Etapa', 
                    x='Quantidade', 
                    color='Motivo de Perda',
                    orientation='h',
                    text_auto=True, # Números dentro dos segmentos
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                # ADIÇÃO ESPECIAL: Adiciona o número TOTAL na frente da barra usando Scatter plot invisível
                fig_loss.add_trace(go.Scatter(
                    y=df_loss_totals['Etapa'],
                    x=df_loss_totals['Total'],
                    text=df_loss_totals['Total'],
                    mode='text',
                    textposition='middle right',
                    textfont=dict(size=14, color
