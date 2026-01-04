import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

st.set_page_config(page_title="Histórico BI", layout="wide")

# (Reutilizar o CSS Futurista aqui para manter padrão...)
st.markdown("""
<style>
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.card { background: #111827; padding: 15px; border-radius: 10px; border: 1px solid #1e293b; text-align: center; }
.card-val { font-size: 24px; font-weight: bold; color: #22d3ee; }
</style>
""", unsafe_allow_html=True)

def carregar_dados_marca(marca):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
    client = gspread.authorize(creds)
    sh = client.open("BI_Historico")
    ws = sh.worksheet(marca)
    return pd.DataFrame(ws.get_all_records())

st.title("📈 Painel Histórico & Consultores")

# Sidebar de Filtros
with st.sidebar:
    st.header("Filtros de Consulta")
    marca_sel = st.selectbox("Selecione a Marca", ["Microlins", "PreparaIA", "Ensina Mais 1", "Ensina Mais 2"])
    
    try:
        df = carregar_dados_marca(marca_sel)
        if not df.empty:
            df['Data'] = pd.to_datetime(df['Data'], dayfirst=True)
            
            # Filtros
            anos = sorted(df['Data'].dt.year.unique())
            ano_sel = st.selectbox("Ano", anos, index=len(anos)-1)
            
            meses = sorted(df[df['Data'].dt.year == ano_sel]['Data'].dt.month.unique())
            mes_sel = st.selectbox("Mês", meses, index=len(meses)-1)
            
            consultores = df['Responsável'].unique()
            consultor_sel = st.multiselect("Filtrar Consultor", consultores, default=consultores)
            
            semanas = df['Semana'].unique()
            semana_sel = st.multiselect("Filtrar Semana", semanas, default=semanas)
            
            # Aplicação dos Filtros
            mask = (
                (df['Data'].dt.year == ano_sel) & 
                (df['Data'].dt.month == mes_sel) &
                (df['Responsável'].isin(consultor_sel)) &
                (df['Semana'].isin(semana_sel))
            )
            df_filtrado = df.loc[mask]
        else:
            st.warning("Sem dados nesta marca.")
            df_filtrado = pd.DataFrame()
            
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        df_filtrado = pd.DataFrame()

# Visualização Principal
if not df_filtrado.empty:
    st.markdown(f"### Resultados: {marca_sel}")
    
    # Tratamento da Taxa para numérico
    if df_filtrado['Taxa Avanço'].dtype == object:
        df_filtrado['Taxa_Num'] = df_filtrado['Taxa Avanço'].astype(str).str.replace('%','').str.replace(',','.').astype(float)
    else:
        df_filtrado['Taxa_Num'] = df_filtrado['Taxa Avanço']

    # KPIs Agregados
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='card'>Total Leads<div class='card-val'>{df_filtrado['Total'].sum()}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='card'>Média Taxa Avanço<div class='card-val'>{df_filtrado['Taxa_Num'].mean():.1f}%</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='card'>Total Perdidos<div class='card-val'>{df_filtrado['Perdidos'].sum()}</div></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # Gráfico de Evolução
    st.subheader("Evolução Semanal por Consultor")
    fig = px.bar(df_filtrado, x="Semana", y="Taxa_Num", color="Responsável", barmode="group", title="Taxa de Avanço por Semana")
    fig.update_layout(template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(df_filtrado, use_container_width=True)
