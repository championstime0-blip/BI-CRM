import streamlit as st
import plotly.express as px
from frontend.components import card, subheader_futurista

def dashboard(df, kpis, etapas_funil):
    total = kpis["total"]
    perdidos = kpis["perdidos_df"]
    em_andamento = kpis["em_andamento_df"]
    perda_especifica = kpis["perda_sem_resposta_df"]

    c1, c2 = st.columns(2)
    with c1: card("Leads Totais", total)
    with c2: card("Leads em Andamento", len(em_andamento))

    st.divider()

    col_mkt, col_funil = st.columns(2)

    # MARKETING
    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            fig = px.pie(df_fonte, values="Qtd", names="Fonte", hole=0.6)
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

    # FUNIL
    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL")
        df_funil = df.groupby("Etapa").size().reindex(etapas_funil).fillna(0).reset_index(name="Qtd")
        fig_funil = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h")
        fig_funil.update_layout(template="plotly_dark")
        st.plotly_chart(fig_funil, use_container_width=True)

    st.divider()

    subheader_futurista("🚫", "DETALHE DAS PERDAS")
    c1, c2 = st.columns(2)
    with c1: card("Leads Improdutivos (Total Perdido)", len(perdidos))
    with c2: card("Perda: Aguardando s/ Resp.", len(perda_especifica))
