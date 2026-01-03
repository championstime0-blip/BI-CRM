import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
import json
import os
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Corporativo Pro", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS AVANÇADA ---
st.markdown("""
<style>
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.02);
    }
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #2c3e50;
    }
    .campaign-card {
        background: linear-gradient(135deg, #ffffff 0%, #f9f9f9 100%);
        border: 1px solid #dcdde1;
        padding: 20px;
        border-radius: 15px;
        border-top: 5px solid #1abc9c;
        text-align: center;
        transition: transform 0.3s;
        height: 100%;
    }
    .campaign-card:hover { transform: translateY(-5px); }
    .date-range-box {
        background-color: #2c3e50;
        color: #ffffff;
        padding: 12px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        font-weight: 500;
        letter-spacing: 1px;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE CONEXÃO
# ==============================================================================
def conectar_gsheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "CREDENCIAIS_GOOGLE" in os.environ:
            creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif "gsheets" in st.secrets:
            creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gsheets"]), scope)
        else: return None
        return gspread.authorize(creds).open("BI_Historico").sheet1
    except: return None

# ==============================================================================
# 2. FUNÇÕES DE DADOS
# ==============================================================================
def salvar_no_gsheets(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet:
        try:
            df_save = df.copy()
            df_save['semana_ref'] = semana
            df_save['marca_ref'] = marca
            df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.append_rows(df_save.fillna('-').values.tolist())
            return True
        except: return False
    return False

def carregar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        try: return pd.DataFrame(sheet.get_all_records())
        except: return pd.DataFrame()
    return pd.DataFrame()

# ==============================================================================
# 3. PROCESSAMENTO E VISUALIZAÇÃO
# ==============================================================================
@st.cache_data(show_spinner=False)
def load_data(file):
    try:
        content = file.getvalue().decode('utf-8-sig')
        sep = ';' if ';' in content.splitlines()[0] else ','
        return pd.read_csv(io.StringIO(content), sep=sep)
    except: return pd.DataFrame()

def process_data(df):
    df.columns = [c.strip() for c in df.columns]
    col_criacao = next((c for c in df.columns if any(x in c.lower() for x in ['criação', 'created', 'data'])), None)
    if col_criacao:
        df['Data_Criacao_DT'] = pd.to_datetime(df[col_criacao], dayfirst=True, errors='coerce')
    
    def deduzir_status(row):
        etapa = str(row.get('Etapa', '')).lower()
        motivo = str(row.get('Motivo de Perda', '')).strip().lower()
        if any(x in etapa for x in ['venda', 'fechamento', 'matricula', 'faturado']): return 'Ganho'
        if motivo in ['nan', '', 'nada', '-']: return 'Em Andamento'
        return 'Perdido'
    
    df['Status_Calc'] = df.apply(deduzir_status, axis=1)
    return df

def renderizar_dashboard_completo(df, titulo_recorte="Análise de Performance"):
    if df.empty: return
    total = len(df)
    vendas = len(df[df['Status_Calc'] == 'Ganho'])
    perdidos = len(df[df['Status_Calc'] == 'Perdido'])
    conversao = (vendas / total * 100) if total > 0 else 0

    if 'Data_Criacao_DT' in df.columns and not df['Data_Criacao_DT'].isnull().all():
        st.markdown(f'<div class="date-range-box">📅 PERÍODO DOS LEADS: {df["Data_Criacao_DT"].min().strftime("%d/%m/%Y")} ATÉ {df["Data_Criacao_DT"].max().strftime("%d/%m/%Y")}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", total)
    c2.metric("Conversão Final", f"{conversao:.1f}%")
    
    inalc = len(df[(df['Motivo de Perda'].str.lower() == 'sem resposta') & (df['Etapa'].str.lower() == 'aguardando resposta')])
    ind_qualidade = 100 - (inalc / total * 100) if total > 0 else 100
    c3.metric("Índice de Alcance", f"{ind_qualidade:.1f}%", help="Leads que atenderam ao menos o 1º contato")
    
    avancados = len(df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])])
    eficiencia = (avancados / total * 100) if total > 0 else 0
    c4.metric("Eficiência Funil", f"{eficiencia:.1f}%", help="Leads que avançaram para etapas decisivas")

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📢 Estratégia Marketing", "📈 Eficiência Comercial", "🚫 Motivos de Perda"])
    
    with tab1:
        col_utm = next((c for c in df.columns if 'utm_source' in c.lower()), 'Fonte')
        st.subheader(f"🏆 Melhores Origens por {col_utm}")
        
        df_top = df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])]
        if not df_top.empty:
            ranking = df_top[col_utm].value_counts().head(3).reset_index()
            cols = st.columns(3)
            for i, row in ranking.iterrows():
                with cols[i]:
                    st.markdown(f'<div class="campaign-card"><small>TOP {i+1} SOURCE</small><br><b>{row.iloc[0]}</b><br><span style="font-size:24px; color:#16a085;">{row.iloc[1]}</span><br><small>Leads Avançados</small></div>', unsafe_allow_html=True)
        
        st.write("")
        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(px.pie(df, names=col_utm, hole=0.5, title="Mix de Marketing", color_discrete_sequence=px.colors.qualitative.Prism), use_container_width=True)
        with col_r:
            df_c = df['Campanha'].value_counts().head(10).reset_index()
            fig_c = px.bar(df_c, x='count', y='Campanha', orientation='h', title="Top 10 Campanhas (Volume Geral)", color='count', color_continuous_scale='Viridis')
            fig_c.update_layout(showlegend=False, coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_c, use_container_width=True)

    with tab2:
        st.subheader("Saúde e Conversão do Funil")
        ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
        df_f = df['Etapa'].value_counts().reindex(ordem).fillna(0).reset_index()
        fig_fun = go.Figure(go.Funnel(y=df_f['Etapa'], x=df_f['count'], textinfo="value+percent initial",
                                     marker={"color": ["#34495e", "#2980b9", "#3498db", "#1abc9c", "#16a085", "#27ae60"]}))
        
        fig_fun.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_fun, use_container_width=True)

    with tab3:
        st.subheader("🚫 Análise Estratégica de Perdas (Polos)")
        df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
        if not df_lost.empty:
            mask = (df_lost['Motivo de Perda'].str.lower() != 'sem resposta') | (df_lost['Etapa'].str.lower() == 'aguardando resposta')
            motivos = df_lost[mask]['Motivo de Perda'].value_counts().head(8).reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            motivos['Perc'] = (motivos['Qtd'] / total * 100).round(1)
            motivos['Label'] = motivos.apply(lambda x: f"<b>{int(x['Qtd'])}</b><br>{x['Perc']}%", axis=1)

            fig_loss = go.Figure(data=[go.Bar(x=motivos['Motivo'], y=motivos['Qtd'], text=motivos['Label'], textposition='outside',
                                             marker_color='#e74c3c', opacity=0.85)])
            fig_loss.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=50), height=500,
                                  yaxis=dict(showgrid=True, gridcolor='#f0f2f6', showticklabels=False), xaxis=dict(showgrid=False))
            st.plotly_chart(fig_loss, use_container_width=True)
            st.info(f"Percentuais baseados no impacto real sobre os {total} leads totais.")
        else: st.success("Nenhuma perda registrada!")

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("🚀 BI Expansão Performance")
modo = st.radio("Selecione o Modo:", ["📥 Importar Planilha", "🗄️ Histórico Gerencial"], horizontal=True)

if modo == "📥 Importar Planilha":
    marca_sel = st.sidebar.selectbox("Operação:", ["Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    file = st.sidebar.file_uploader("Subir Pedro.csv", type=['csv'])
    if file:
        df = process_data(load_data(file))
        termo = marca_sel.split(' ')[-1]
        col_resp = next((c for c in df.columns if any(x in c for x in ['Proprietário', 'Responsável'])), None)
        if col_resp: df = df[df[col_resp].astype(str).str.contains(termo, case=False, na=False)]
        
        semana = st.sidebar.selectbox("Semana:", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
        if st.sidebar.button("💾 Salvar Histórico"):
            if salvar_no_gsheets(df, semana, marca_sel): st.sidebar.success("Salvo!")
        renderizar_dashboard_completo(df)
else:
    df_h = carregar_historico_gsheets()
    if not df_h.empty:
        df_h['Data_Criacao_DT'] = pd.to_datetime(df_h['data_upload'], errors='coerce')
        renderizar_dashboard_completo(df_h, "Visão Consolidada")
