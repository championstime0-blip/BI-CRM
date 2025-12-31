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
        # Se a primeira coluna contiver "sep=", recarrega pulando a primeira linha
        if len(df.columns) > 0 and 'sep=' in str(df.columns[0]):
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=';', skiprows=1)

        # Validação: Se tiver poucas colunas, o separador pode estar errado
        if df.shape[1] < 2:
            raise ValueError("Tentando outro separador...")
            
    except Exception:
        # TENTATIVA 2: Separador Vírgula (Padrão Internacional)
        uploaded_file.seek(0)
        try:
            df = pd.read_csv(uploaded_file, sep=',')
            # Mesma verificação do "sep=" para vírgula
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
        
        *Dica: Verifique se o arquivo exportado possui cabeçalho.*
        """)
        st.stop()

    # --- 4. Limpeza e Tratamento de Dados (ETL) ---
    
    # Definição da Ordem Lógica do Funil
    ordem_funil = [
        'Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 
        'Reunião Agendada', 'Reunião Realizada', 'Follow-up', 'Venda/Fechamento'
    ]
    etapas_existentes = [e for e in ordem_funil if e in df['Etapa'].unique()]
    
    # Tratamento da Coluna de Campanha
    if 'Utm_campaign' in df.columns:
        df['Campanha_
