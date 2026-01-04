import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI Comparativo | Marcas", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 45px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(251, 191, 36, 0.3); margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# FUNÇÃO DE LEITURA GLOBAL
# =========================
def carregar_todas_marcas():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get("CREDENCIAIS_GOOGLE")), scope)
        client = gspread.authorize(creds)
        sh = client.open("BI_Historico")
        
        full_df = pd.DataFrame()
        marcas_disponiveis = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
        
        for m in marcas_disponiveis:
            try:
                ws = sh.worksheet(m)
                df_m = pd.DataFrame(ws.get_all_records())
                if not df_m.empty:
                    df_m['Marca'] = m
                    df_m['Taxa_Num'] = df_m['Taxa'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
                    full_df = pd.concat([full_df, df_m])
            except:
                continue
        return full_df
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()

# =========================
# INTERFACE
# =========================
st.markdown('<div class="futuristic-title">⚔️ Comparativo de Performance</div>', unsafe_allow_html=True)

df_comp = carregar_todas_marcas()

if not df_comp.empty:
    # Filtro de Semana (Multi-seleção)
    semanas_disp = df_comp['Semana'].unique().tolist()
    semanas_sel = st.sidebar.multiselect("Selecione as Semanas", semanas_disp, default=semanas_disp[-1:])

    df_filtrado = df_comp[df_comp['Semana'].isin(semanas_sel)]

    # --- GRÁFICO 1: VOLUME POR MARCA ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 Volume de Leads por Marca")
        fig_vol = px.bar(df_filtrado, x="Marca", y="Total", color="Marca", barmode="group",
                         text_auto=True, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_vol.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_vol, use_container_width=True)

    with col2:
        st.subheader("🎯 Eficiência (Taxa de Avanço %)")
        # Gráfico de Radar ou Barras para Taxa
        fig_taxa = px.bar(df_filtrado, x="Marca", y="Taxa_Num", color="Marca",
                          text=df_filtrado["Taxa_Num"].astype(str) + "%",
                          color_discrete_sequence=px.colors.qualitative.Bold)
        fig_taxa.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_taxa, use_container_width=True)

    st.divider()

    # --- ANÁLISE DE QUALIDADE (SEM RESPOSTA) ---
    st.subheader("📉 Incidência de Leads 'Sem Resposta' por Marca")
    fig_sr = px.line(df_filtrado, x="Marca", y="Sem Resposta", markers=True, 
                     line_shape="linear", color_discrete_sequence=["#ef4444"])
    fig_sr.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_sr, use_container_width=True)

    # --- TABELA COMPARATIVA ---
    st.subheader("📑 Ranking Geral")
    ranking = df_filtrado.sort_values(by="Taxa_Num", ascending=False)
    st.dataframe(ranking[['Marca', 'Semana', 'Total', 'Taxa', 'Top Fonte']], use_container_width=True)

else:
    st.info("Aguardando dados históricos para realizar o comparativo.")
