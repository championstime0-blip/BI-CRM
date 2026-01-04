import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI Histórico | Evolução", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 45px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #c084fc 0%, #818cf8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(192, 132, 252, 0.3); margin-bottom: 20px;
}
.card-hist {
    background: rgba(30, 41, 59, 0.5); padding: 15px; border-radius: 10px;
    border: 1px solid #334155; text-align: center;
}
.val-hist { font-family: 'Orbitron', sans-serif; font-size: 24px; color: #c084fc; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================
def carregar_dados_historicos(marca):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get("CREDENCIAIS_GOOGLE")), scope)
        client = gspread.authorize(creds)
        sh = client.open("BI_Historico")
        ws = sh.worksheet(marca)
        df = pd.DataFrame(ws.get_all_records())
        
        if not df.empty:
            # Limpeza: Transforma "15.5%" em 15.5 (número)
            df['Taxa_Num'] = df['Taxa'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return pd.DataFrame()

# =========================
# INTERFACE
# =========================
st.markdown('<div class="futuristic-title">📈 Evolução Histórica</div>', unsafe_allow_html=True)

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
marca_sel = st.sidebar.selectbox("Selecione a Marca", MARCAS)

df_hist = carregar_dados_historicos(marca_sel)

if not df_hist.empty:
    # --- KPIs ÚLTIMO REGISTRO ---
    ultimo = df_hist.iloc[-1]
    st.markdown(f"### Status Atual: {ultimo['Semana']} ({ultimo['Data']})")
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="card-hist">Total Leads<br><span class="val-hist">{ultimo["Total"]}</span></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card-hist">Andamento<br><span class="val-hist">{ultimo["Andamento"]}</span></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card-hist">Taxa Avanço<br><span class="val-hist">{ultimo["Taxa"]}</span></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card-hist">Principal Fonte<br><span style="color:#818cf8; font-weight:bold;">{ultimo["Top Fonte"]}</span></div>', unsafe_allow_html=True)

    st.divider()

    # --- GRÁFICOS DE EVOLUÇÃO ---
    col_evol1, col_evol2 = st.columns(2)

    with col_evol1:
        st.subheader("📊 Crescimento de Leads")
        fig_vol = px.line(df_hist, x="Semana", y="Total", markers=True, 
                          line_shape="spline", color_discrete_sequence=["#22d3ee"])
        fig_vol.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_evol2:
        st.subheader("🚀 Performance (Taxa de Avanço)")
        fig_tx = px.area(df_hist, x="Semana", y="Taxa_Num", markers=True,
                         color_discrete_sequence=["#c084fc"])
        fig_tx.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_tx, use_container_width=True)

    # --- TABELA DE DADOS ---
    st.subheader("📋 Histórico de Lançamentos")
    st.dataframe(df_hist.drop(columns=['Taxa_Num']), use_container_width=True)

else:
    st.info(f"Ainda não existem dados salvos para a marca {marca_sel}. Vá até a Home e clique em Salvar.")
