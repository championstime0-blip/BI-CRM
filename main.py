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

# --- ESTILIZAÇÃO CSS (CORREÇÃO DE CONTRASTE E CORES) ---
st.markdown("""
<style>
    /* Ajuste global para garantir textos escuros em áreas claras */
    .stApp {
        color: #2c3e50;
    }

    /* Métricas Principais */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricValue"] {
        font-size: 30px;
        color: #2c3e50 !important;
        font-weight: bold;
    }
    [data-testid="stMetricLabel"] {
        color: #57606f !important;
        font-size: 16px;
    }

    /* Cards de Campanha (Contraste Total) */
    .campaign-card {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        padding: 20px;
        border-radius: 15px;
        border-top: 6px solid #1abc9c;
        text-align: center;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.08);
        height: 100%;
    }
    .campaign-card b {
        color: #1e272e !important; /* Azul quase preto */
        font-size: 18px;
        display: block;
        margin-bottom: 5px;
    }
    .campaign-card small {
        color: #7f8c8d !important; /* Cinza escuro */
        font-weight: 700;
        text-transform: uppercase;
    }
    .campaign-card .val {
        font-size: 32px;
        color: #16a085;
        font-weight: 800;
    }

    /* Barra de Recorte de Data */
    .date-range-box {
        background-color: #2c3e50;
        color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        font-weight: 600;
        font-size: 18px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
            sheet.append_rows(df_save.fillna('-').astype(str).values.tolist())
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
    total_leads = len(df)
    vendas = len(df[df['Status_Calc'] == 'Ganho'])
    conv_final = (vendas / total_leads * 100) if total_leads > 0 else 0

    # --- BARRA DE RECORTE ---
    if 'Data_Criacao_DT' in df.columns and not df['Data_Criacao_DT'].isnull().all():
        st.markdown(f'''<div class="date-range-box">📅 PERÍODO ANALISADO: {df["Data_Criacao_DT"].min().strftime("%d/%m/%Y")} ATÉ {df["Data_Criacao_DT"].max().strftime("%d/%m/%Y")}</div>''', unsafe_allow_html=True)

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", total_leads)
    c2.metric("Conversão Geral", f"{conv_final:.1f}%")
    
    inalc = len(df[(df['Motivo de Perda'].str.lower() == 'sem resposta') & (df['Etapa'].str.lower() == 'aguardando resposta')])
    ind_alcance = 100 - (inalc / total_leads * 100) if total_leads > 0 else 100
    c3.metric("Índice de Contato", f"{ind_alcance:.1f}%")
    
    avancados = len(df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])])
    eficiencia = (avancados / total_leads * 100) if total_leads > 0 else 0
    c4.metric("Qualificação Funil", f"{eficiencia:.1f}%")

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📢 Estratégia Marketing", "📈 Eficiência Comercial", "🚫 Motivos de Perda"])
    
    with tab1:
        col_utm = next((c for c in df.columns if 'utm_source' in c.lower()), 'Fonte')
        st.subheader(f"🏆 Top 3 Fontes de Avanço")
        
        df_top = df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])]
        if not df_top.empty:
            ranking = df_top[col_utm].value_counts().head(3).reset_index()
            cols = st.columns(3)
            for i, row in ranking.iterrows():
                with cols[i]:
                    st.markdown(f'''
                    <div class="campaign-card">
                        <small>RANKING TOP {i+1}</small>
                        <b>{row.iloc[0]}</b>
                        <div class="val">{row.iloc[1]}</div>
                        <small style="color:#2c3e50 !important;">LEADS QUALIFICADOS</small>
                    </div>
                    ''', unsafe_allow_html=True)
        
        st.write("")
        cl, cr = st.columns(2)
        with cl:
            st.plotly_chart(px.pie(df, names=col_utm, hole=0.5, title="Mix de Marketing"), use_container_width=True)
        with cr:
            df_c = df['Campanha'].value_counts().head(10).reset_index()
            fig_c = px.bar(df_c, x='count', y='Campanha', orientation='h', title="Top 10 Campanhas", color='count', color_continuous_scale='Blues')
            fig_c.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_c, use_container_width=True)

    with tab2:
        st.subheader("Saúde Comercial do Funil")
        ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
        df_f = df['Etapa'].value_counts().reindex(ordem).fillna(0).reset_index()
        fig_fun = go.Figure(go.Funnel(y=df_f['Etapa'], x=df_f['count'], textinfo="value+percent initial",
                                     marker={"color": ["#34495e", "#2980b9", "#3498db", "#1abc9c", "#16a085", "#27ae60"]}))
        st.plotly_chart(fig_fun, use_container_width=True)
        

    with tab3:
        st.subheader("🚫 Análise Estratégica de Motivos de Perda")
        st.write("Impacto dos motivos sobre os leads totais.")
        
        df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
        if not df_lost.empty:
            mask = (df_lost['Motivo de Perda'].str.lower() != 'sem resposta') | (df_lost['Etapa'].str.lower() == 'aguardando resposta')
            motivos = df_lost[mask]['Motivo de Perda'].value_counts().head(10).reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            motivos['Perc'] = (motivos['Qtd'] / total_leads * 100).round(1)
            motivos['Label'] = motivos.apply(lambda x: f"<b>{int(x['Qtd'])}</b><br>{x['Perc']}%", axis=1)

            # GRÁFICO DE POLOS VERTICAIS (SOLICITADO)
            fig_loss = go.Figure(data=[go.Bar(
                x=motivos['Motivo'], 
                y=motivos['Qtd'], 
                text=motivos['Label'], 
                textposition='outside',
                marker_color='#e74c3c', 
                opacity=0.9
            )])
            
            fig_loss.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=60, b=20),
                height=550,
                xaxis=dict(showgrid=False, tickfont=dict(size=12, color='#2c3e50')),
                yaxis=dict(showticklabels=False, showgrid=True, gridcolor='#f0f2f6')
            )
            st.plotly_chart(fig_loss, use_container_width=True)
        else: st.success("Excelente! Nenhuma perda registrada.")

# ==============================================================================
# 4. INTERFACE
# ==============================================================================
st.title("🚀 BI Expansão Performance")
modo = st.radio("Selecione o Modo:", ["📥 Importar Planilha", "🗄️ Histórico Gerencial"], horizontal=True)

if modo == "📥 Importar Planilha":
    marca_sel = st.sidebar.selectbox("Marca/Operação:", ["Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    file = st.sidebar.file_uploader("Subir Pedro.csv", type=['csv'])
    if file:
        df_raw = process_data(load_data(file))
        termo = marca_sel.split(' ')[-1]
        col_resp = next((c for c in df_raw.columns if any(x in c for x in ['Proprietário', 'Responsável'])), None)
        if col_resp: df_raw = df_raw[df_raw[col_resp].astype(str).str.contains(termo, case=False, na=False)]
        
        semana = st.sidebar.selectbox("Semana:", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
        if st.sidebar.button("💾 Salvar no GSheets"):
            if salvar_no_gsheets(df_raw, semana, marca_sel): st.sidebar.success("Dados salvos!")
        renderizar_dashboard_completo(df_raw)
else:
    df_h = carregar_historico_gsheets()
    if not df_h.empty:
        df_h['Data_Criacao_DT'] = pd.to_datetime(df_h['data_upload'], errors='coerce')
        renderizar_dashboard_completo(df_h, "Visão Histórica Consolidada")
