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

# --- ESTILIZAÇÃO CSS (Contraste e Cards) ---
st.markdown("""
<style>
    .stApp { color: #2c3e50; }
    [data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricValue"] { font-size: 30px; color: #2c3e50 !important; font-weight: bold; }
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
    .campaign-card b { color: #1e272e !important; font-size: 18px; display: block; }
    .val { font-size: 32px; color: #16a085; font-weight: 800; }
    .date-range-box {
        background-color: #2c3e50;
        color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 30px;
        font-weight: 600;
        font-size: 18px;
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
            # Converte colunas de data para string antes de enviar para evitar erro de JSON
            for col in df_save.select_dtypes(include=['datetime64']).columns:
                df_save[col] = df_save[col].dt.strftime('%d/%m/%Y')
            sheet.append_rows(df_save.fillna('-').astype(str).values.tolist())
            return True
        except Exception as e:
            st.error(f"Erro ao salvar: {e}")
            return False
    return False

def carregar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        try:
            data = sheet.get_all_records()
            return pd.DataFrame(data)
        except: return pd.DataFrame()
    return pd.DataFrame()

def limpar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        try:
            sheet.delete_rows(2, 10000)
            return True
        except: return False
    return False

# ==============================================================================
# 3. PROCESSAMENTO E DASHBOARD
# ==============================================================================
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

def renderizar_dashboard_completo(df, titulo_recorte="Dashboard"):
    if df.empty:
        st.info("Nenhum dado encontrado para os filtros selecionados.")
        return
    
    total_leads = len(df)
    vendas = len(df[df['Status_Calc'] == 'Ganho'])
    conv_final = (vendas / total_leads * 100) if total_leads > 0 else 0

    # --- INDICADORES ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Leads Totais", total_leads)
    c2.metric("Conversão Geral", f"{conv_final:.1f}%")
    
    inalc = len(df[(df['Motivo de Perda'].str.lower() == 'sem resposta') & (df['Etapa'].str.lower() == 'aguardando resposta')])
    c3.metric("Alcance Inicial", f"{100-(inalc/total_leads*100):.1f}%" if total_leads > 0 else "0%")
    
    avancados = len(df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])])
    c4.metric("Qualificação Funil", f"{(avancados/total_leads*100):.1f}%" if total_leads > 0 else "0%")

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📢 Marketing", "📈 Comercial", "🚫 Perdas"])
    
    with tab1:
        col_utm = next((c for c in df.columns if 'utm_source' in c.lower()), 'Fonte')
        cl, cr = st.columns(2)
        with cl: st.plotly_chart(px.pie(df, names=col_utm, hole=0.5, title="Canais"), use_container_width=True)
        with cr:
            df_c = df['Campanha'].value_counts().head(10).reset_index()
            st.plotly_chart(px.bar(df_c, x='count', y='Campanha', orientation='h', title="Top Campanhas", color='count', color_continuous_scale='Blues'), use_container_width=True)

    with tab2:
        ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
        df_f = df['Etapa'].value_counts().reindex(ordem).fillna(0).reset_index()
        
        st.plotly_chart(go.Figure(go.Funnel(y=df_f['Etapa'], x=df_f['count'], textinfo="value+percent initial")), use_container_width=True)

    with tab3:
        df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
        if not df_lost.empty:
            motivos = df_lost['Motivo de Perda'].value_counts().head(10).reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            motivos['Label'] = motivos.apply(lambda x: f"<b>{int(x['Qtd'])}</b><br>{round(x['Qtd']/total_leads*100,1)}%", axis=1)
            fig_loss = go.Figure(data=[go.Bar(x=motivos['Motivo'], y=motivos['Qtd'], text=motivos['Label'], textposition='outside', marker_color='#e74c3c')])
            fig_loss.update_layout(plot_bgcolor='rgba(0,0,0,0)', yaxis(showticklabels=False))
            st.plotly_chart(fig_loss, use_container_width=True)

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("🚀 BI Expansão Performance")
modo = st.radio("Selecione o Modo:", ["📥 Importar Planilha", "🗄️ Histórico Gerencial"], horizontal=True)

if modo == "📥 Importar Planilha":
    marca_sel = st.sidebar.selectbox("Operação:", ["Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    file = st.sidebar.file_uploader("Subir Pedro.csv", type=['csv'])
    if file:
        df_raw = process_data(pd.read_csv(io.StringIO(file.getvalue().decode('utf-8-sig')), sep=None, engine='python'))
        termo = marca_sel.split(' ')[-1]
        col_resp = next((c for c in df_raw.columns if any(x in c for x in ['Proprietário', 'Responsável'])), None)
        if col_resp: df_raw = df_raw[df_raw[col_resp].astype(str).str.contains(termo, case=False, na=False)]
        
        semana = st.sidebar.selectbox("Salvar em qual Semana?", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
        if st.sidebar.button("💾 Confirmar e Salvar no Histórico"):
            if salvar_no_gsheets(df_raw, semana, marca_sel):
                st.sidebar.success("✅ Dados arquivados com sucesso!")
        renderizar_dashboard_completo(df_raw, f"Análise Atual: {marca_sel}")

else:
    df_h = carregar_historico_gsheets()
    if not df_h.empty:
        # --- FILTROS GERENCIAIS ---
        st.sidebar.header("🔍 Filtros do Histórico")
        
        # Filtro de Marca
        marcas_disponiveis = ["Todas"] + list(df_h['marca_ref'].unique())
        f_marca = st.sidebar.selectbox("Filtrar por Marca:", marcas_disponiveis)
        
        # Filtro de Semana
        semanas_disponiveis = ["Todas"] + sorted(list(df_h['semana_ref'].unique()))
        f_semana = st.sidebar.selectbox("Filtrar por Semana:", semanas_disponiveis)
        
        # Aplicação dos Filtros
        df_v = df_h.copy()
        if f_marca != "Todas": df_v = df_v[df_v['marca_ref'] == f_marca]
        if f_semana != "Todas": df_v = df_v[df_v['semana_ref'] == f_semana]
        
        # Botão de Limpeza
        st.sidebar.divider()
        if st.sidebar.button("⚠️ Limpar Todo o Histórico"):
            if limpar_historico_gsheets():
                st.sidebar.warning("Histórico apagado. Reiniciando...")
                time.sleep(1)
                st.rerun()

        renderizar_dashboard_completo(df_v, f"Visão Gerencial: {f_marca} ({f_semana})")
    else:
        st.warning("O Histórico está vazio. Importe uma planilha primeiro.")
