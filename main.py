import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt 
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Multi-Marcas", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 22px;
        color: #0E1117;
    }
    .st-emotion-cache-1r6slb0 {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 8px;
    }
    .highlight-box {
        background-color: #e8f4f8;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #2E86C1;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE CARREGAMENTO E LIMPEZA ---
@st.cache_data
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

def convert_dates(df):
    # Tenta encontrar colunas de data
    col_criacao = None
    col_fechamento = None
    
    # Procura nomes comuns de colunas de data
    possiveis_criacao = ['Data de criação', 'Created at', 'Data Criação', 'Data']
    possiveis_fechamento = ['Data de fechamento', 'Closed at', 'Data Fechamento', 'Data da perda']

    for col in df.columns:
        if col in possiveis_criacao: col_criacao = col
        if col in possiveis_fechamento: col_fechamento = col
    
    # Converte para Datetime
    if col_criacao:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_criacao], dayfirst=True, errors='coerce')
    else:
        df['Data_Criacao_DT'] = pd.NaT

    if col_fechamento:
        df['Data_Fechamento_DT'] = pd.to_datetime(df[col_fechamento], dayfirst=True, errors='coerce')
    else:
        df['Data_Fechamento_DT'] = pd.NaT
        
    return df

def clean_data(df):
    # 1. Padronizar Cidades
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # 2. Status Inteligente
    def deduzir_status(row):
        motivo = str(row.get('Motivo de Perda', ''))
        if motivo != '' and motivo.lower() != 'nan' and motivo.lower() != 'nat': return 'Perdido'
        etapa = str(row.get('Etapa', '')).lower()
        if 'venda' in etapa or 'fechamento' in etapa or 'matricula' in etapa: return 'Ganho'
        return 'Em Aberto'

    if 'Status_Calc' not in df.columns:
        df['Status_Calc'] = df.apply(deduzir_status, axis=1)
        
    return df

# --- INTERFACE PRINCIPAL ---
st.title("📊 BI Corporativo - Gestão de Marcas")
st.markdown("Controle de Leads: Prepara IA, Microlins e Ensina Mais.")

uploaded_file = st.sidebar.file_uploader("📂 Carregar CSV", type=['csv'])

if uploaded_file is not None:
    try:
        df_raw = load_data(uploaded_file)
        
        if 'Etapa' not in df_raw.columns:
            st.error("O arquivo precisa ter a coluna 'Etapa'.")
            st.stop()
            
        df = convert_dates(df_raw)
        df = clean_data(df)

        # --- SELETOR DE MARCA / CONSULTOR (O QUE VOCÊ PEDIU) ---
        st.sidebar.divider()
        st.sidebar.header("🎯 Filtro de Marca/Consultor")
        
        opcoes_marca = [
            "Todas as Marcas",
            "Prepara IA", 
            "Microlins", 
            "Ensina Mais TM Pedro", 
            "Ensina Mais TM Luciana"
        ]
        marca_selecionada = st.sidebar.selectbox("Selecione a Operação:", opcoes_marca)

        # Tenta filtrar automaticamente se houver coluna de proprietário
        df_filtered = df.copy()
        col_responsavel = None
        for col in ['Proprietário', 'Responsável', 'Dono do lead', 'Consultor']:
            if col in df.columns:
                col_responsavel = col
                break
        
        # Lógica de Filtro
        if marca_selecionada != "Todas as Marcas":
            if col_responsavel:
                # Filtra se o nome da marca estiver contido no nome do responsável
                # Ex: Selecionou "Pedro", filtra linhas onde Responsável contém "Pedro"
                termo_busca = marca_selecionada.split(' ')[-1] # Pega o último nome (Pedro, Luciana, IA, Microlins)
                if "Ensina Mais" in marca_selecionada:
                    df_filtered = df_filtered[df_filtered[col_responsavel].astype(str).str.contains(termo_busca, case=False, na=False)]
                else:
                    # Para Microlins e Prepara, tenta filtrar, mas se não achar, avisa
                    matches = df_filtered[df_filtered[col_responsavel].astype(str).str.contains(marca_selecionada, case=False, na=False)]
                    if not matches.empty:
                        df_filtered = matches
            else:
                st.warning(f"⚠️ Não encontrei uma coluna de 'Responsável' no CSV. Mostrando dados gerais sob a ótica de: **{marca_selecionada}**")

        # --- ANÁLISE DO RECORTE (DATA E HORA) ---
        st.markdown(f"### 🗓️ Análise do Recorte: {marca_selecionada}")
        
        if pd.notna(df_filtered['Data_Criacao_DT']).any():
            data_min = df_filtered['Data_Criacao_DT'].min()
            data_max = df_filtered['Data_Criacao_DT'].max()
            dias_corridos = (data_max - data_min).days
            
            st.markdown(f"""
            <div class="highlight-box">
                <b>⏱️ Período Analisado (Corte da Planilha):</b><br>
                De: <b>{data_min.strftime('%d/%m/%Y às %H:%M')}</b> <br>
                Até: <b>{data_max.strftime('%d/%m/%Y às %H:%M')}</b> <br>
                Duração do Recorte: <b>{dias_corridos} dias</b>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Colunas de data de criação não detectadas para cálculo do recorte.")

        # --- KPIS PRINCIPAIS ---
        total = len(df_filtered)
        vendas = len(df_filtered[df_filtered['Status_Calc'] == 'Ganho'])
        perdidos = len(df_filtered[df_filtered['Status_Calc'] == 'Perdido'])
        ativos = total - vendas - perdidos
        conversao = (vendas / total * 100) if total > 0 else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Leads Selecionados", total)
        c2.metric("Vendas (Ganhos)", vendas, delta=f"{conversao:.1f}% Conv.")
        c3.metric("Em Aberto", ativos)
        c4.metric("Perdidos", perdidos, delta_color="inverse")
        
        st.divider()

        # --- ABAS ---
        tab1, tab2, tab3 = st.tabs(["📢 Fonte & Campanha", "📉 Funil", "🚫 Detalhe de Perdas"])

        # TAB 1: FONTE E CAMPANHA (SOLICITAÇÃO ESPECÍFICA)
        with tab1:
            col_camp1, col_camp2 = st.columns(2)
            
            with col_camp1:
                st.subheader("Performance por Fonte")
                if 'Fonte' in df_filtered.columns:
                    df_fonte = df_filtered['Fonte'].value_counts().reset_index()
                    df_fonte.columns = ['Fonte', 'Leads']
                    fig_fonte = px.pie(df_fonte, values='Leads', names='Fonte', hole=0.4)
                    st.plotly_chart(fig_fonte, use_container_width=True)
                else:
                    st.warning("Coluna 'Fonte' não encontrada.")

            with col_camp2:
                st.subheader("Performance por Campanha")
                if 'Campanha' in df_filtered.columns:
                    df_camp = df_filtered['Campanha'].value_counts().head(10).reset_index()
                    df_camp.columns = ['Campanha', 'Leads']
                    fig_camp = px.bar(df_camp, x='Leads', y='Campanha', orientation='h', text='Leads')
                    fig_camp.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_camp, use_container_width=True)
                else:
                    st.warning("Coluna 'Campanha' não encontrada.")
            
            # Cruzamento Fonte x Campanha (Tabela Térmica)
            if 'Fonte' in df_filtered.columns and 'Campanha' in df_filtered.columns:
                st.subheader("Matriz: Fonte vs Campanha")
                pivot_camp = pd.crosstab(df_filtered['Fonte'], df_filtered['Campanha'])
                try:
                    st.dataframe(pivot_camp.style.background_gradient(cmap="Blues"), use_container_width=True)
                except:
                    st.dataframe(pivot_camp, use_container_width=True)

        # TAB 2: FUNIL
        with tab2:
            st.subheader("Funil de Vendas")
            df_funil = df_filtered['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            # Tenta ordenar se tiver lista definida, senão usa ordem de volume
            ordem_ideal = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=ordem_ideal, ordered=True)
            df_funil = df_funil.sort_values('Etapa')
            
            fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa', text='Volume')
            st.plotly_chart(fig_funnel, use_container_width=True)

        # TAB 3: DETALHE DE PERDAS (DATA E HORA)
        with tab3:
            st.subheader("Análise de Perdas e Tempos")
            
            if 'Motivo de Perda' in df_filtered.columns:
                # Filtra perdidos
                df_lost = df_filtered[df_filtered['Status_Calc'] == 'Perdido'].copy()
                
                if not df_lost.empty:
                    # Gráfico de Motivos
                    c_loss1, c_loss2 = st.columns([2, 1])
                    
                    with c_loss1:
                        motivos = df_lost['Motivo de Perda'].value_counts().reset_index()
                        motivos.columns = ['Motivo', 'Qtd']
                        fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Qtd', title="Motivos")
                        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                        st.plotly_chart(fig_bar, use_container_width=True)

                    with c_loss2:
                        st.write("### ⏱️ Ciclo de Perda")
                        # Calcula tempo entre criação e fechamento (se existir data)
                        if pd.notna(df_lost['Data_Fechamento_DT']).any() and pd.notna(df_lost['Data_Criacao_DT']).any():
                            df_lost['Dias_Ate_Perda'] = (df_lost['Data_Fechamento_DT'] - df_lost['Data_Criacao_DT']).dt.days
                            media_dias = df_lost['Dias_Ate_Perda'].mean()
                            st.metric("Tempo Médio até Perda", f"{media_dias:.1f} dias")
                            
                            st.write("**Amostra de Leads Perdidos:**")
                            # Mostra tabela com datas formatadas
                            cols_show = ['Etapa', 'Motivo de Perda', 'Data_Criacao_DT', 'Data_Fechamento_DT']
                            # Filtra colunas que existem
                            cols_show = [c for c in cols_show if c in df_lost.columns]
                            
                            st.dataframe(
                                df_lost[cols_show].sort_values('Data_Criacao_DT', ascending=False).head(10),
                                use_container_width=True
                            )
                        else:
                            st.info("Não foi possível calcular o tempo exato (faltam colunas de data de fechamento).")
                else:
                    st.success("Sem perdas registradas nesta seleção.")
            else:
                st.warning("Coluna 'Motivo de Perda' inexistente.")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
else:
    st.info("Aguardando arquivo CSV...")
