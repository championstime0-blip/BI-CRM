import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import matplotlib.pyplot as plt 
import time

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
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE CARREGAMENTO ---
@st.cache_data(show_spinner=False) # Desativa o spinner padrão para usarmos o nosso st.status
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
    # 1. Converter Datas
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

    # 2. Padronizar Cidades
    if 'Cidade Interesse' in df.columns:
        df['Cidade_Clean'] = df['Cidade Interesse'].astype(str).apply(lambda x: x.split('-')[0].split('(')[0].strip().title())
        df = df[df['Cidade_Clean'] != 'Nan']
    else: df['Cidade_Clean'] = 'Não Informado'
    
    # 3. Status Inteligente
    def deduzir_status(row):
        motivo = str(row.get('Motivo de Perda', ''))
        if motivo != '' and motivo.lower() != 'nan' and motivo.lower() != 'nat': return 'Perdido'
        etapa = str(row.get('Etapa', '')).lower()
        if 'venda' in etapa or 'fechamento' in etapa or 'matricula' in etapa: return 'Ganho'
        return 'Em Aberto'

    df['Status_Calc'] = df.apply(deduzir_status, axis=1)
    return df

# --- INTERFACE PRINCIPAL ---
st.title("📊 BI Corporativo - Gestão de Marcas")

# --- 1. FILTROS ANTES DO UPLOAD (Barra Lateral) ---
st.sidebar.header("🎯 Configuração da Análise")

opcoes_marca = [
    "Todas as Marcas",
    "Prepara IA", 
    "Microlins", 
    "Ensina Mais TM Pedro", 
    "Ensina Mais TM Luciana"
]
# O selectbox agora vem PRIMEIRO
marca_selecionada = st.sidebar.selectbox("1º Selecione a Operação:", opcoes_marca)

st.sidebar.divider()

# O upload vem DEPOIS
uploaded_file = st.sidebar.file_uploader("2º Carregar Planilha CSV", type=['csv'])

if uploaded_file is not None:
    # --- 2. LOADING COM ST.STATUS ---
    with st.status("Iniciando processamento de dados...", expanded=True) as status:
        st.write("📂 Lendo arquivo CSV...")
        time.sleep(0.5) # Pequena pausa estética
        df_raw = load_data(uploaded_file)
        
        st.write("🛠️ Padronizando datas e colunas...")
        df = process_data(df_raw)
        
        st.write("🔍 Aplicando filtros de consultor...")
        
        # Lógica de Filtro (Aplicada aqui dentro do processamento)
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
        
        status.update(label="Dados Carregados com Sucesso!", state="complete", expanded=False)

    # --- 3. RECORTE SIMPLIFICADO (SOLICITAÇÃO) ---
    if pd.notna(df_filtered['Data_Criacao_DT']).any():
        d_min = df_filtered['Data_Criacao_DT'].min()
        d_max = df_filtered['Data_Criacao_DT'].max()
        # Formato Simples: "Recorte: dd/mm a dd/mm"
        st.markdown(f"**📅 Recorte Analisado:** de {d_min.strftime('%d/%m')} a {d_max.strftime('%d/%m')}")
    
    # --- VERIFICAÇÃO DE SEGURANÇA ---
    if 'Etapa' not in df.columns:
        st.error("Erro: O arquivo não possui a coluna 'Etapa'.")
        st.stop()

    # --- KPIS PRINCIPAIS ---
    total = len(df_filtered)
    vendas = len(df_filtered[df_filtered['Status_Calc'] == 'Ganho'])
    perdidos = len(df_filtered[df_filtered['Status_Calc'] == 'Perdido'])
    ativos = total - vendas - perdidos
    conversao = (vendas / total * 100) if total > 0 else 0

    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Filtrados", total)
    c2.metric("Vendas (Ganhos)", vendas, delta=f"{conversao:.1f}% Conv.")
    c3.metric("Em Aberto", ativos)
    c4.metric("Perdidos", perdidos, delta_color="inverse")
    
    # --- ABAS ---
    tab1, tab2, tab3 = st.tabs(["📢 Fonte & Campanha", "📉 Funil", "🚫 Detalhe de Perdas"])

    # TAB 1: FONTE E CAMPANHA
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
            try:
                st.dataframe(pivot_camp.style.background_gradient(cmap="Blues"), use_container_width=True)
            except:
                st.dataframe(pivot_camp, use_container_width=True)

    # TAB 2: FUNIL
    with tab2:
        st.subheader("Funil de Vendas")
        df_funil = df_filtered['Etapa'].value_counts().reset_index()
        df_funil.columns = ['Etapa', 'Volume']
        ordem_ideal = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
        # Ordenação customizada se as etapas existirem
        df_funil['Etapa'] = pd.Categorical(df_funil['Etapa'], categories=[c for c in ordem_ideal if c in df_funil['Etapa'].values], ordered=True)
        df_funil = df_funil.sort_values('Etapa')
        
        fig_funnel = px.funnel(df_funil, x='Volume', y='Etapa', text='Volume')
        st.plotly_chart(fig_funnel, use_container_width=True)

    # TAB 3: PERDAS
    with tab3:
        st.subheader("Análise de Perdas")
        if 'Motivo de Perda' in df_filtered.columns:
            df_lost = df_filtered[df_filtered['Status_Calc'] == 'Perdido'].copy()
            
            if not df_lost.empty:
                c_loss1, c_loss2 = st.columns([2, 1])
                with c_loss1:
                    motivos = df_lost['Motivo de Perda'].value_counts().reset_index()
                    motivos.columns = ['Motivo', 'Qtd']
                    fig_bar = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text='Qtd', title="Principais Motivos")
                    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_bar, use_container_width=True)

                with c_loss2:
                    st.write("### ⏱️ Ciclo de Perda")
                    if pd.notna(df_lost['Data_Fechamento_DT']).any() and pd.notna(df_lost['Data_Criacao_DT']).any():
                        df_lost['Dias_Ate_Perda'] = (df_lost['Data_Fechamento_DT'] - df_lost['Data_Criacao_DT']).dt.days
                        media_dias = df_lost['Dias_Ate_Perda'].mean()
                        st.metric("Tempo Médio", f"{media_dias:.1f} dias")
                    
                    st.write("**Amostra Recente:**")
                    cols_show = [c for c in ['Etapa', 'Motivo de Perda', 'Data_Criacao_DT'] if c in df_lost.columns]
                    st.dataframe(df_lost[cols_show].head(5), use_container_width=True)
            else:
                st.success("Sem perdas registradas.")
        else:
            st.warning("Coluna 'Motivo de Perda' não encontrada.")

else:
    # Mensagem de espera inicial (Bonita e limpa)
    st.info("👈 Selecione a Operação e faça o Upload do CSV na barra lateral.")
