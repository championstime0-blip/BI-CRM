import streamlit as st
from frontend.components import card

def dashboard(kpis, modo):
    if modo == "Diretor":
        c1, c2, c3, c4 = st.columns(4)
        with c1: card("Leads Totais", kpis["total"])
        with c2: card("Perdidos", kpis["perdidos"])
        with c3: card("Em Andamento", kpis["andamento"])
        with c4: card("Aguardando", kpis["aguardando"])

    else:
        c1, c2 = st.columns(2)
        with c1: card("Leads em Andamento", kpis["andamento"])
        with c2: card("Aguardando Retorno", kpis["aguardando"])
