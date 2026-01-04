import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI Histórico | Auditoria", layout="wide")

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
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    padding: 20px; border-radius: 12px;
    border: 1px solid #334155; text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

.label-hist { font-family: 'Rajdhani', sans-serif; font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
.val-hist { font-family: 'Orbitron', sans-serif; font-size: 26px; color: #c084fc; font-weight: 700; margin-top: 5px; }
.val-sub { font-family: 'Rajdhani', sans-serif; font-size: 16px; color: #818cf8; }
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
            # 1. Tratamento da Data para Filtros
            df['Data_DT'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
            df['Ano'] = df['Data_DT'].dt.year.astype(str)
            
            # Meses em Português
            meses_map = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 
                         7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
            df['Mês'] = df['Data_DT'].dt.month.map(meses_map)
            
            # 2. Tratamento da Taxa para Números
            df['Taxa_Num'] = df['Taxa'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
            
        return df
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return pd.DataFrame()

# =========================
# INTERFACE E FILTROS
# =========================
st.markdown('<div class="futuristic-title">📊 Auditoria de Histórico</div>', unsafe_allow_html=True)

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
marca_sel = st.sidebar.selectbox("🎯 Selecione a Marca", MARCAS)

df_base = carregar_dados_historicos(marca_sel)

if not df_base.empty:
    # --- SIDEBAR FILTROS ---
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtros de Tempo")
    
    anos = sorted(df_base['Ano'].unique().tolist(), reverse=True)
    ano_sel = st.sidebar.multiselect("Ano", anos, default=anos)
    
    meses_disp = df_base[df_base['Ano'].isin(ano_sel)]['Mês'].unique().tolist()
    mes_sel = st.sidebar.multiselect("Mês", meses_disp, default=meses_disp)
    
    semanas_disp = df_base[(df_base['Ano'].isin(ano_sel)) & (df_base['Mês'].isin(mes_sel))]['Semana'].unique().tolist()
    semana_sel = st.sidebar.multiselect("Semana", semanas_disp, default=semanas_disp)

    # Aplicação dos Filtros
    df_filtrado = df_base[
        (df_base['Ano'].isin(ano_sel)) & 
        (df_base['Mês'].isin(mes_sel)) & 
        (df_base['Semana'].isin(semana_sel))
    ]

    if df_filtrado.empty:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")
        st.stop()

    # --- KPIs DO ÚLTIMO REGISTRO SELECIONADO ---
    ultimo = df_filtrado.iloc[-1]
    
    st.markdown(f"#### Exibindo: {ultimo['Semana']} | Lançado em: {ultimo['Data']} às {ultimo['Hora']}")
    
    # Grid de 5 Colunas para todos os KPIs salvos
    c1, c2, c3, c4, c5 = st.columns(5)
    
    with c1: st.markdown(f'<div class="card-hist"><div class="label-hist">Total Leads</div><div class="val-hist">{ultimo["Total"]}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card-hist"><div class="label-hist">Andamento</div><div class="val-hist">{ultimo["Andamento"]}</div></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="card-hist"><div class="label-hist">Perdidos</div><div class="val-hist">{ultimo["Perdidos"]}</div></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="card-hist"><div class="label-hist">Sem Resposta</div><div class="val-hist" style="color:#ef4444;">{ultimo["Sem Resposta"]}</div></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="card-hist"><div class="label-hist">Taxa de Avanço</div><div class="val-hist" style="color:#22d3ee;">{ultimo["Taxa"]}</div></div>', unsafe_allow_html=True)

    # Card de Contexto (Responsável e Equipe)
    st.markdown(f"""
    <div style="background: rgba(34, 211, 238, 0.05); padding: 15px; border-radius: 8px; border-left: 4px solid #22d3ee; margin-top: 20px;">
        <span style="color:#94a3b8; text-transform:uppercase; font-size:12px;">Informações de Registro</span><br>
        <b style="color:#e2e8f0;">Responsável:</b> {ultimo["Responsável"]} | <b style="color:#e2e8f0;">Equipe:</b> {ultimo["Equipe"]} | <b style="color:#e2e8f0;">Top Fonte:</b> {ultimo["Top Fonte"]}
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- GRÁFICOS DE EVOLUÇÃO ---
    col_evol1, col_evol2 = st.columns(2)

    with col_evol1:
        st.markdown('<div class="futuristic-sub"><span class="sub-icon">📈</span>Crescimento de Volume</div>', unsafe_allow_html=True)
        # Gráfico comparando Total vs Sem Resposta ao longo do tempo
        fig_evol = go.Figure()
        fig_evol.add_trace(go.Scatter(x=df_filtrado['Semana'], y=df_filtrado['Total'], name='Total Leads', line=dict(color='#818cf8', width=3)))
        fig_evol.add_trace(go.Scatter(x=df_filtrado['Semana'], y=df_filtrado['Sem Resposta'], name='Sem Resposta', line=dict(color='#ef4444', dash='dot')))
        fig_evol.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_evol, use_container_width=True)

    with col_evol2:
        st.markdown('<div class="futuristic-sub"><span class="sub-icon">🚀</span>Evolução da Eficiência</div>', unsafe_allow_html=True)
        fig_tx = px.line(df_filtrado, x="Semana", y="Taxa_Num", markers=True, color_discrete_sequence=["#22d3ee"])
        fig_tx.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Taxa de Avanço (%)")
        st.plotly_chart(fig_tx, use_container_width=True)

    # --- TABELA DE AUDITORIA COMPLETA ---
    st.markdown('<div class="futuristic-sub"><span class="sub-icon">📋</span>Registro Completo de Dados</div>', unsafe_allow_html=True)
    # Remove colunas internas de processamento para mostrar a tabela limpa
    exibir_tabela = df_filtrado.drop(columns=['Data_DT', 'Ano', 'Mês', 'Taxa_Num'])
    st.dataframe(exibir_tabela, use_container_width=True, hide_index=True)

else:
    st.info(f"Ainda não existem dados salvos para a marca {marca_sel}. Vá até a Home, processe um CSV e clique em Salvar Dados.")
