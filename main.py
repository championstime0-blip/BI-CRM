# ==============================================================================
# BI CORPORATIVO PRO – STREAMLIT (VERSÃO SÊNIOR RESILIENTE)
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="BI Corporativo Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILO GLOBAL
# ==============================================================================
st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 26px;
    font-weight: bold;
}
.block-container {
    padding-top: 1.5rem;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. FUNÇÃO UTILITÁRIA – MAPEAMENTO DE COLUNAS
# ==============================================================================
def encontrar_coluna(df, possiveis_nomes):
    for col in df.columns:
        col_norm = col.strip().lower()
        for nome in possiveis_nomes:
            if nome in col_norm:
                return col
    return None

# ==============================================================================
# 2. CONEXÃO GOOGLE SHEETS (CACHE)
# ==============================================================================
@st.cache_resource(show_spinner=False)
def conectar_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    if "CREDENCIAIS_GOOGLE" in os.environ:
        creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
    elif "gsheets" in st.secrets:
        creds_dict = dict(st.secrets["gsheets"])
    else:
        raise RuntimeError("Credenciais do Google Sheets não encontradas")

    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("BI_Historico").sheet1

# ==============================================================================
# 3. CARGA DO HISTÓRICO
# ==============================================================================
@st.cache_data(show_spinner=False)
def carregar_historico():
    sheet = conectar_gsheets()
    return pd.DataFrame(sheet.get_all_records())

# ==============================================================================
# 4. PROCESSAMENTO DE DADOS (ETL ROBUSTO)
# ==============================================================================
@st.cache_data(show_spinner=False)
def processar_dados(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df.columns = df.columns.str.strip()

    # 🔎 Detecção dinâmica de colunas
    col_etapa  = encontrar_coluna(df, ['etapa', 'fase', 'stage'])
    col_motivo = encontrar_coluna(df, ['motivo'])
    col_estado = encontrar_coluna(df, ['estado', 'status'])
    col_cidade = encontrar_coluna(df, ['cidade'])
    col_data   = encontrar_coluna(df, ['criacao', 'criação', 'data'])

    etapa  = df[col_etapa].astype(str).str.lower() if col_etapa else ''
    motivo = df[col_motivo].astype(str).str.lower() if col_motivo else ''
    estado = df[col_estado].astype(str).str.lower() if col_estado else ''

    # 🎯 Status semântico
    df['Status_Calc'] = 'Em Andamento'

    if col_etapa:
        df.loc[
            etapa.str.contains('venda|fechamento|matricula|faturado', na=False),
            'Status_Calc'
        ] = 'Ganho'

    if col_estado or col_motivo:
        df.loc[
            (estado == 'perdida') |
            ((motivo != '') & (motivo != 'nan')),
            'Status_Calc'
        ] = 'Perdido'

    # 📅 Data
    if col_data:
        df['Data_Criacao_DT'] = pd.to_datetime(
            df[col_data],
            errors='coerce',
            dayfirst=True
        )

    # 🌍 Cidade
    if col_cidade:
        df['Cidade_Clean'] = (
            df[col_cidade]
            .astype(str)
            .str.split('-').str[0]
            .str.split('(').str[0]
            .str.strip()
            .str.title()
        )
    else:
        df['Cidade_Clean'] = 'Não Informado'

    # Campos padrão BI
    for col in ['Fonte', 'Campanha']:
        if col not in df.columns:
            df[col] = '-'

    return df

# ==============================================================================
# 5. MÉTRICAS (CAMADA SEMÂNTICA)
# ==============================================================================
def calcular_kpis(df: pd.DataFrame) -> dict:
    total = len(df)
    ganhos = (df['Status_Calc'] == 'Ganho').sum()
    perdidos = (df['Status_Calc'] == 'Perdido').sum()
    andamento = (df['Status_Calc'] == 'Em Andamento').sum()

    return {
        "total": total,
        "ganhos": ganhos,
        "perdidos": perdidos,
        "andamento": andamento,
        "conversao": (ganhos / total * 100) if total else 0
    }

# ==============================================================================
# 6. FILTROS (SIDEBAR)
# ==============================================================================
def aplicar_filtros(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🔎 Filtros")

    status = st.sidebar.multiselect(
        "Status",
        options=df['Status_Calc'].unique(),
        default=df['Status_Calc'].unique()
    )

    cidade = st.sidebar.multiselect(
        "Cidade",
        options=sorted(df['Cidade_Clean'].unique())
    )

    if status:
        df = df[df['Status_Calc'].isin(status)]
    if cidade:
        df = df[df['Cidade_Clean'].isin(cidade)]

    return df

# ==============================================================================
# 7. DASHBOARD
# ==============================================================================
def render_dashboard(df: pd.DataFrame):
    if df.empty:
        st.warning("Nenhum dado encontrado para os filtros aplicados.")
        return

    kpis = calcular_kpis(df)

    st.markdown("## 📊 Performance Geral")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads", kpis['total'])
    c2.metric("Vendas", kpis['ganhos'], f"{kpis['conversao']:.1f}%")
    c3.metric("Em Andamento", kpis['andamento'])
    c4.metric("Perdidos", kpis['perdidos'])

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            df,
            names='Status_Calc',
            title='Distribuição de Status',
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        top_cidades = (
            df['Cidade_Clean']
            .value_counts()
            .head(10)
            .reset_index()
        )
        fig = px.bar(
            top_cidades,
            x='index',
            y='Cidade_Clean',
            title='Top 10 Cidades'
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### 📄 Base Analítica")
    st.dataframe(df, use_container_width=True)

# ==============================================================================
# 8. APP PRINCIPAL
# ==============================================================================
def main():
    st.title("📈 BI Corporativo Pro")

    df_raw = carregar_historico()
    df = processar_dados(df_raw)
    df = aplicar_filtros(df)
    render_dashboard(df)

# ==============================================================================
# START
# ==============================================================================
if __name__ == "__main__":
    main()
