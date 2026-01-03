# ==============================================================================
# BI PERFORMANCE EXPANSÃO – VERSÃO SÊNIOR
# Streamlit | BI | Franquias | Funil de Impacto Total
# ==============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================================================
st.set_page_config(
    page_title="BI Expansão Pro",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# ESTILO GLOBAL
# ==============================================================================
st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 22px; font-weight: bold; }
.block-container { padding-top: 1.2rem; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. LEITOR DE CSV UNIVERSAL (ROBUSTO)
# ==============================================================================
def ler_csv_universal(file):
    for sep in [';', ',']:
        for enc in ['utf-8-sig', 'latin-1']:
            try:
                return pd.read_csv(file, sep=sep, encoding=enc)
            except:
                pass
    return pd.DataFrame()

# ==============================================================================
# 2. PARSER DE MATRIZ DE FUNIL (LOCALIZA "SEMx")
# ==============================================================================
def parse_funil_expansao(file, semana_alvo):
    try:
        df_raw = pd.read_csv(file, header=None, sep=None, engine='python')

        header_row = None
        for i, row in df_raw.iterrows():
            if semana_alvo.upper() in row.astype(str).values:
                header_row = i
                break

        if header_row is None:
            st.error(f"Semana {semana_alvo} não encontrada no arquivo.")
            return pd.DataFrame()

        df = pd.read_csv(file, skiprows=header_row, sep=None, engine='python')
        df.columns = df.columns.str.strip().str.upper()

        col_desc = df.columns[0]
        if semana_alvo.upper() not in df.columns:
            st.error(f"Coluna {semana_alvo} não encontrada.")
            return pd.DataFrame()

        df_final = df[[col_desc, semana_alvo.upper()]].copy()
        df_final.columns = ['Descricao', 'Valor']
        df_final['Valor'] = pd.to_numeric(df_final['Valor'], errors='coerce').fillna(0)
        df_final = df_final[df_final['Descricao'].notna()]

        return df_final

    except Exception as e:
        st.error(f"Erro no processamento do CSV: {e}")
        return pd.DataFrame()

# ==============================================================================
# 3. MOTOR DE BI – FUNIL DE IMPACTO TOTAL
# ==============================================================================
def renderizar_bi_profissional(df, titulo):
    def get_val(termo):
        res = df[df['Descricao'].str.contains(termo, case=False, na=False)]
        return res['Valor'].sum() if not res.empty else 0

    # KPIs PRINCIPAIS
    leads = get_val("TOTAL DE LEADS")
    interesse = get_val("CONFIRMOU INTERESSE")
    reuniao = get_val("REUNIÃO")
    vendas = get_val("FATURADO")

    conv_total = (vendas / leads * 100) if leads else 0
    aproveitamento = (interesse / leads * 100) if leads else 0

    st.markdown(f"## {titulo}")

    # SEMÁFORO EXECUTIVO
    delta_color = "normal" if conv_total > 5 else "off" if conv_total > 2 else "inverse"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", int(leads))
    c2.metric("Conversão Final", f"{conv_total:.1f}%", delta_color=delta_color)
    c3.metric("Aproveitamento Base", f"{aproveitamento:.1f}%")
    c4.metric("Vendas (Faturado)", int(vendas))

    st.divider()

    tab1, tab2 = st.tabs([
        "📉 Funil de Conversão (Impacto Total)",
        "🎯 Origem / Campanha"
    ])

    # ---------------- FUNIL ----------------
    with tab1:
        etapas = ["Leads", "Interesse", "Reunião", "Venda"]
        valores = [leads, interesse, reuniao, vendas]

        fig = go.Figure(go.Funnel(
            y=etapas,
            x=valores,
            textinfo="value+percent initial",
            connector={"line": {"color": "#555", "dash": "dot"}}
        ))

        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    # ---------------- MARKETING ----------------
    with tab2:
        canais = [
            'GOOGLE', 'FACEBOOK', 'INSTAGRAM',
            'META', 'TIKTOK', 'INDICAÇÃO', 'ORGÂNICO'
        ]

        df_mkt = df[
            df['Descricao']
            .str.upper()
            .str.contains('|'.join(canais), na=False)
        ]

        if df_mkt.empty:
            st.info("Nenhuma origem de marketing identificada.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(
                    px.pie(df_mkt, values='Valor', names='Descricao', hole=0.5),
                    use_container_width=True
                )
            with c2:
                st.plotly_chart(
                    px.bar(
                        df_mkt.sort_values('Valor'),
                        x='Valor', y='Descricao',
                        orientation='h'
                    ),
                    use_container_width=True
                )

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("🚀 BI Performance Expansão")

modo = st.sidebar.radio(
    "Navegação",
    ["📥 Importação", "🗄️ Histórico (em breve)"]
)

if modo == "📥 Importação":
    marca = st.sidebar.selectbox(
        "Unidade",
        [
            "Selecione...",
            "Prepara IA",
            "Microlins",
            "Ensina Mais TM Pedro",
            "Ensina Mais TM Luciana"
        ]
    )

    if marca != "Selecione...":
        uploaded = st.sidebar.file_uploader(
            "Upload do CSV do Funil",
            type=["csv"]
        )

        if uploaded:
            semana = st.sidebar.selectbox(
                "Semana",
                ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"]
            )

            df_funil = parse_funil_expansao(uploaded, semana)

            if not df_funil.empty:
                renderizar_bi_profissional(
                    df_funil,
                    titulo=f"{marca} • {semana}"
                )

elif modo == "🗄️ Histórico (em breve)":
    st.info(
        "Esta área será usada para comparação entre semanas, meses e marcas.\n\n"
        "Próximo passo natural do projeto."
    )
