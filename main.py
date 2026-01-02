import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Avançado - Franquias", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS PROFISSIONAL ---
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
    h3 { padding-top: 10px; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE CARREGAMENTO E LIMPEZA ---
@st.cache_data
def load_data(file):
    try:
        file.seek(0)
        df = pd.read_csv(file, sep=';')
        # Lógica para limpar cabeçalho sujo (sep=)
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
    # 1. Padronizar Colunas
    if 'Utm_campaign' in df.columns: df['Campanha_Clean'] = df['Utm_campaign'].fillna('Orgânico/Desconhecido')
    elif 'Campanha' in df.columns: df['Campanha_Clean'] = df['Campanha'].fillna('Desconhecido')
    else: df['Campanha_Clean'] = 'Não Identificado'

    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # 2. Categorizar Status (Ganho, Perdido, Aberto)
    # Ajuste essa lógica conforme o que está escrito na sua coluna 'Estado'
    def classificar_status(status):
        s = str(status).lower()
        if 'ganh' in s or 'vend' in s or 'matricul' in s: return 'Ganho'
        elif 'perdid' in s or 'cancel' in s: return 'Perdido'
        else: return 'Em Aberto'

    if 'Estado' in df.columns:
        df['Status_Calc'] = df['Estado'].apply(classificar_status)
    else:
        df['Status_Calc'] = 'Em Aberto'
        
    return df

# --- INTERFACE PRINCIPAL ---
st.title("📊 BI Estratégico de Expansão")
st.markdown("Análise detalhada de performance, conversão e qualidade de dados.")

uploaded_file = st.sidebar.file_uploader("📂 Carregar CSV", type=['csv'])

if uploaded_file is not None:
    try:
        df_raw = load_data(uploaded_file)
        
        # Validação Básica
        cols_req = ['Etapa', 'Estado']
        if not all(col in df_raw.columns for col in cols_req):
            st.error(f"Faltam colunas essenciais: {cols_req}")
            st.stop()
            
        df = clean_data(df_raw)

        # --- FILTROS LATERAIS (BI REAL PRECISA DISSO) ---
        st.sidebar.header("Filtros de Análise")
        
        cidades = ['Todas'] + list(df['Cidade_Clean'].unique())
        filtro_cidade = st.sidebar.selectbox("Filtrar por Cidade", cidades)
        
        campanhas = ['Todas'] + list(df['Campanha_Clean'].unique())
        filtro_campanha = st.sidebar.selectbox("Filtrar por Campanha", campanhas)

        # Aplicar Filtros
        df_filtered = df.copy()
        if filtro_cidade != 'Todas':
            df_filtered = df_filtered[df_filtered['Cidade_Clean'] == filtro_cidade]
        if filtro_campanha != 'Todas':
            df_filtered = df_filtered[df_filtered['Campanha_Clean'] == filtro_campanha]

        # --- CÁLCULO DE KPIS GLOBAIS ---
        total = len(df_filtered)
        vendas = len(df_filtered[df_filtered['Status_Calc'] == 'Ganho'])
        perdidos = len(df_filtered[df_filtered['Status_Calc'] == 'Perdido'])
        ativos = total - vendas - perdidos
        conversao_global = (vendas / total * 100) if total > 0 else 0
        taxa_perda = (perdidos / total * 100) if total > 0 else 0

        # KPI ROW
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads Totais", total, help="Volume total no período selecionado")
        c2.metric("Vendas (Ganhos)", vendas, delta=f"{conversao_global:.1f}% Conv.", help="Leads convertidos em venda")
        c3.metric("Em Negociação", ativos, help="Leads ainda ativos no funil")
        c4.metric("Perdidos", perdidos, delta=f"-{taxa_perda:.1f}%", delta_color="inverse")
        
        st.divider()

        # --- TABS PARA ORGANIZAÇÃO LÓGICA ---
        tab1, tab2, tab3 = st.tabs(["📉 Análise de Funil & Eficiência", "📢 Inteligência de Campanhas", "⚠️ Discrepâncias & Perdas"])

        # === TAB 1: FUNIL E CONVERSÃO ===
        with tab1:
            col_f1, col_f2 = st.columns([2, 1])
            
            with col_f1:
                st.subheader("Funil de Vendas")
                # Ordem lógica
                ordem_funil = [
                    'Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 
                    'Reunião Agendada', 'Reunião Realizada', 'Follow-up', 'Venda/Fechamento'
                ]
                # Filtra apenas o que existe no dataframe atual
                etapas_reais = [e for e in ordem_funil if e in df_filtered['Etapa'].unique()]
                
                df_funil = df_filtered['Etapa'].value_counts().reindex(etapas_reais).fillna(0).reset_index()
                df_funil.columns = ['Etapa', 'Volume']
                
                # Cálculo de conversão passo a passo (Drop-off rate)
                df_funil['% do Total'] = (df_funil['Volume'] / total * 100).round(1)
                
                fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa', text='Volume')
                st.plotly_chart(fig_funnel, use_container_width=True)

            with col_f2:
                st.subheader("Eficiência por Etapa")
                st.markdown("Visualização tabular dos dados do funil:")
                # Exibe tabela com gradiente para identificar onde o volume é maior
                st.dataframe(
                    df_funil.set_index('Etapa').style.background_gradient(cmap="Blues", subset=['Volume']),
                    use_container_width=True
                )
                
                if len(df_funil) > 1:
                    # Análise rápida de gargalo (simples)
                    maior_etapa = df_funil.iloc[0]['Etapa']
                    menor_etapa = df_funil.iloc[-1]['Etapa']
                    st.info(f"💡 **Insight:** O funil começa com **{df_funil.iloc[0]['Volume']}** leads em '{maior_etapa}' e termina com **{df_funil.iloc[-1]['Volume']}** em '{menor_etapa}'.")

        # === TAB 2: INTELIGÊNCIA DE CAMPANHA ===
        with tab2:
            st.subheader("Matriz de Qualidade: Volume vs. Conversão")
            st.markdown("Quais campanhas trazem volume mas não vendem? Quais trazem pouca gente mas vendem muito?")

            # Agrupamento para ver conversão por campanha
            df_mkt = df_filtered.groupby('Campanha_Clean').agg(
                Leads=('Etapa', 'count'),
                Vendas=('Status_Calc', lambda x: (x == 'Ganho').sum())
            ).reset_index()
            
            df_mkt['Taxa_Conversao'] = ((df_mkt['Vendas'] / df_mkt['Leads']) * 100).round(1)
            df_mkt = df_mkt.sort_values(by='Leads', ascending=False).head(15) # Top 15 campanhas

            # Scatter Plot: Eixo X = Volume, Eixo Y = Conversão
            fig_matrix = px.scatter(
                df_mkt, x='Leads', y='Taxa_Conversao', 
                size='Leads', color='Campanha_Clean',
                hover_name='Campanha_Clean',
                text='Campanha_Clean',
                title="Quadrante Mágico: Eixo Y (Qualidade) vs Eixo X (Quantidade)",
                labels={'Leads': 'Volume de Leads', 'Taxa_Conversao': 'Taxa de Conversão (%)'}
            )
            # Linha média de conversão
            media_conv = df_mkt['Taxa_Conversao'].mean()
            fig_matrix.add_hline(y=media_conv, line_dash="dot", annotation_text=f"Média: {media_conv:.1f}%", annotation_position="bottom right")
            
            st.plotly_chart(fig_matrix, use_container_width=True)

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.write("**Top Campanhas por Volume**")
                st.dataframe(df_mkt[['Campanha_Clean', 'Leads']].head(), use_container_width=True)
            with col_m2:
                st.write("**Top Campanhas por Eficiência (Conversão)**")
                st.dataframe(df_mkt.sort_values(by='Taxa_Conversao', ascending=False)[['Campanha_Clean', 'Taxa_Conversao', 'Vendas']].head(), use_container_width=True)

        # === TAB 3: DISCREPÂNCIAS E PERDAS ===
        with tab3:
            c_loss1, c_loss2 = st.columns(2)
            
            with c_loss1:
                st.subheader("🚫 Raio-X Detalhado de Perdas")
                if 'Motivo de Perda' in df_filtered.columns:
                    df_lost = df_filtered[df_filtered['Status_Calc'] == 'Perdido']
                    
                    if not df_lost.empty:
                        # Gráfico elaborado com totais na frente (Solução anterior)
                        totals = df_lost.groupby('Etapa').size().reset_index(name='Total')
                        detailed = df_lost.groupby(['Etapa', 'Motivo de Perda']).size().reset_index(name='Qtd')
                        
                        fig_loss = px.bar(detailed, y='Etapa', x='Qtd', color='Motivo de Perda', orientation='h', text_auto=True, title="Motivos de Perda por Etapa")
                        
                        # Adiciona totais ao lado
                        fig_loss.add_trace(go.Scatter(
                            y=totals['Etapa'], x=totals['Total'], text=totals['Total'],
                            mode='text', textposition='middle right', showlegend=False,
                            textfont=dict(color='black')
                        ))
                        fig_loss.update_layout(margin=dict(r=50), barmode='stack')
                        st.plotly_chart(fig_loss, use_container_width=True)
                    else:
                        st.success("Não há leads perdidos na seleção atual.")
                else:
                    st.warning("Coluna 'Motivo de Perda' não encontrada.")

            with c_loss2:
                st.subheader("⚠️ Auditoria de Dados (Discrepâncias)")
                
                # Checagem de Dados Faltantes
                sem_cidade = len(df_filtered[df_filtered['Cidade_Clean'] == 'Não Informado'])
                sem_campanha = len(df_filtered[df_filtered['Campanha_Clean'] == 'Não Identificado'])
                sem_motivo = 0
                if 'Motivo de Perda' in df_filtered.columns:
                    # Leads perdidos SEM motivo preenchido
                    sem_motivo = len(df_filtered[(df_filtered['Status_Calc'] == 'Perdido') & (df_filtered['Motivo de Perda'].isna())])

                st.write("Leads com falha de rastreamento ou preenchimento:")
                
                col_d1, col_d2, col_d3 = st.columns(3)
                col_d1.metric("Sem Cidade", sem_cidade, delta="Correção Necessária" if sem_cidade > 0 else "OK", delta_color="inverse")
                col_d2.metric("Sem Origem (UTM)", sem_campanha, delta="Perda de Rastreio" if sem_campanha > 0 else "OK", delta_color="inverse")
                col_d3.metric("Perdidos s/ Motivo", sem_motivo, delta="Falta Feedback" if sem_motivo > 0 else "OK", delta_color="inverse")

                st.markdown("#### Amostra de Dados Incompletos")
                if sem_cidade > 0:
                    st.caption("Leads sem cidade identificada:")
                    st.dataframe(df_filtered[df_filtered['Cidade_Clean'] == 'Não Informado'][['Etapa', 'Campanha_Clean']].head(), use_container_width=True)

    except Exception as e:
        st.error(f"Erro crítico ao processar o arquivo: {e}")
        st.info("Verifique se o CSV possui as colunas 'Etapa' e 'Estado'.")

else:
    st.info("👋 Olá! Faça o upload do arquivo CSV para ver o Dashboard de BI.")
