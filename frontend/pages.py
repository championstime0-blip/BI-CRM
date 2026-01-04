import streamlit as st
from frontend.components import card
from backend.metrics import kpis_gerais
from backend.charts import grafico_fontes, grafico_funil
from backend.processor import ETAPAS_FUNIL

def dashboard(df):
    kpi = kpis_gerais(df)

    c1,c2,c3,c4 = st.columns(4)
    with c1: card("Leads Totais", kpi["total"])
    with c2: card("Em Andamento", kpi["andamento"])
    with c3: card("Perdidos", kpi["perdidos"])
    with c4: card("Ganhos", kpi["ganhos"])

    fig = grafico_fontes(df)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    st.plotly_chart(
        grafico_funil(df, [e.lower() for e in ETAPAS_FUNIL]),
        use_container_width=True
    )

