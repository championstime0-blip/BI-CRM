# Lógica: Loop nas 4 abas -> pd.concat() -> Gráfico de barras comparando Taxa de Avanço por Marca
import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# =========================
# CONFIGURAÇÃO E CSS
# =========================
st.set_page_config(page_title="BI Comparativo | Expansão", layout="wide")

# (Use o mesmo CSS do Home.py para manter a identidade visual)

# =========================
# FUNÇÃO DE LEITURA GLOBAL
# =========================
def carregar_dados_totais():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(st.secrets["gcp_service_account"]), scope)
        client = gspread.authorize(creds)
        sh = client.open("BI_Historico")
        
        full_df = pd.DataFrame()
        marcas = ["Microlins", "PreparaIA", "Ensina Mais 1", "Ensina Mais 2"]
        
        for m in marcas:
            try:
                ws = sh.worksheet(m)
                df_m = pd.DataFrame(ws.get_all_records())
                if not df_m.empty:
                    df_m['Marca_Unificada'] = m
                    full_df = pd.concat([full_df, df_m])
            except:
                continue # Se a aba da marca ainda não existir, ignora
        
        if not full_df.empty:
            full_df['Data_DT'] = pd.to_datetime(full_df['Data'], dayfirst=True)
            full_df['Taxa_Num'] = full_df['Taxa'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        
        return full_df
    except Exception as e:
        st.error(f"Erro na conexão global: {e}")
        return pd.DataFrame()

# =========================
# INTERFACE
# =========================
st.markdown('<div class="futuristic-title">⚔️ Comparativo de Marcas</div>', unsafe_allow_html=True)

df_total = carregar_dados_totais()

if not df_total.empty:
    with st.sidebar:
        st.header("🔍 Filtros de Comparação")
        
        # Filtro de Data Personalizado
        datas = sorted(df_total['Data_DT'].dt.date.unique())
        data_inicio, data_fim = st.select_slider(
            "Selecione o Período",
            options=datas,
            value=(datas[0], datas[-1])
        )
        
        # Filtro de Marca
        marcas_sel = st.multiselect("Selecione as Marcas", df_total['Marca_Unificada'].unique(), default=df_total['Marca_Unificada'].unique())

    # Aplicação dos Filtros
    mask = (df_total['Data_DT'].dt.date >= data_inicio) & \
           (df_total['Data_DT'].dt.date <= data_fim) & \
           (df_total['Marca_Unificada'].isin(marcas_sel))
    
    df_filtrado = df_total.loc[mask]

    # --- GRÁFICOS COMPARATIVOS ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🎯 Taxa de Avanço por Marca (%)")
        fig_taxa = px.bar(df_filtrado, x="Marca_Unificada", y="Taxa_Num", color="Marca_Unificada",
                          barmode="group", text_auto=True, title="Eficiência do Funil")
        fig_taxa.update_layout(template="plotly_dark", showlegend=False)
        st.plotly_chart(fig_taxa, use_container_width=True)

    with col2:
        st.subheader("📦 Volume de Leads Total")
        fig_vol = px.line(df_filtrado, x="Data", y="Total", color="Marca_Unificada",
                          markers=True, title="Entrada de Leads no Período")
        fig_vol.update_layout(template="plotly_dark")
        st.plotly_chart(fig_vol, use_container_width=True)

    st.divider()
    st.subheader("📋 Tabela Comparativa Detalhada")
    st.dataframe(df_filtrado[['Data', 'Semana', 'Marca_Unificada', 'Total', 'Taxa', 'Responsável']], use_container_width=True)
else:
    st.info("Aguardando dados salvos nas planilhas para gerar comparativos.")
