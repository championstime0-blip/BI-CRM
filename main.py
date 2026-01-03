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

# --- ESTILIZAÇÃO CSS (PADRONIZAÇÃO DE LAYOUT) ---
st.markdown("""
<style>
    .stApp { color: #2c3e50; }
    
    /* Remove o estilo padrão de métricas do Streamlit para usarmos o nosso personalizado */
    [data-testid="stMetric"] { display: none; }

    /* Layout do Card Premium (Igual à imagem 2) */
    .kpi-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .card-blue { border-left: 6px solid #3498db; background-color: #f0f7ff; }
    .card-green { border-left: 6px solid #27ae60; background-color: #f0fff4; }
    .card-orange { border-left: 6px solid #f39c12; background-color: #fff9f0; }
    .card-teal { border-left: 6px solid #1abc9c; background-color: #f0fdfa; }
    .card-red { border-left: 6px solid #ff4b4b; background-color: #fff3f3; }

    .card-label { color: #7f8c8d; font-size: 14px; font-weight: bold; text-transform: uppercase; display: block; }
    .card-value { font-size: 28px; font-weight: bold; color: #2c3e50; display: block; }
    .card-sub { color: #95a5a6; font-size: 12px; }

    /* Cards de Campanha Marketing */
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
    .campaign-card b { color: #1e272e !important; font-size: 18px; display: block; margin-bottom: 5px; }
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
# 1. MOTOR DE CONEXÃO E DADOS
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

def load_data(file):
    raw_data = file.getvalue()
    for encoding in ['utf-8-sig', 'iso-8859-1', 'latin-1', 'cp1252']:
        try:
            content = raw_data.decode(encoding)
            sep = ';' if ';' in content.splitlines()[0] else ','
            return pd.read_csv(io.StringIO(content), sep=sep)
        except: continue
    return pd.DataFrame()

def process_data(df):
    if df.empty: return df
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

# ==============================================================================
# 2. FUNÇÃO AUXILIAR DE CARD CUSTOMIZADO
# ==============================================================================
def metric_card(label, value, subtext, style_class):
    st.markdown(f'''
        <div class="kpi-card {style_class}">
            <span class="card-label">{label}</span>
            <span class="card-value">{value}</span>
            <span class="card-sub">{subtext}</span>
        </div>
    ''', unsafe_allow_html=True)

# ==============================================================================
# 3. DASHBOARD
# ==============================================================================
def renderizar_dashboard_completo(df, titulo_recorte="Análise de Performance"):
    if df.empty: return
    total_leads = len(df)
    vendas = len(df[df['Status_Calc'] == 'Ganho'])
    conv_final = (vendas / total_leads * 100) if total_leads > 0 else 0

    if 'Data_Criacao_DT' in df.columns and not df['Data_Criacao_DT'].isnull().all():
        st.markdown(f'''<div class="date-range-box">📅 PERÍODO ANALISADO: {df["Data_Criacao_DT"].min().strftime("%d/%m/%Y")} ATÉ {df["Data_Criacao_DT"].max().strftime("%d/%m/%Y")}</div>''', unsafe_allow_html=True)

    # --- KPIs DE TOPO (PADRONIZADOS COM O LAYOUT DA IMAGEM 2) ---
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Leads Totais", f"{total_leads}", "Volume total na base", "card-blue")
    with c2:
        metric_card("Conversão Geral", f"{conv_final:.1f}%", "Percentual de vendas", "card-green")
    with c3:
        inalc = len(df[(df['Motivo de Perda'].astype(str).str.lower() == 'sem resposta') & (df['Etapa'].astype(str).str.lower() == 'aguardando resposta')])
        ind_alcance = 100 - (inalc / total_leads * 100) if total_leads > 0 else 100
        metric_card("Índice de Contato", f"{ind_alcance:.1f}%", "Aproveitamento inicial", "card-orange")
    with c4:
        avancados = len(df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])])
        eficiencia = (avancados / total_leads * 100) if total_leads > 0 else 0
        metric_card("Eficiência Funil", f"{eficiencia:.1f}%", "Leads que avançaram", "card-teal")

    st.divider()
    tab1, tab2, tab3 = st.tabs(["📢 Estratégia Marketing", "📈 Saúde Comercial", "🚫 Motivos de Perda"])
    
    with tab1:
        col_utm = next((c for c in df.columns if 'utm_source' in c.lower()), 'Fonte')
        st.subheader(f"🏆 Top 3 Fontes de Avanço")
        df_top = df[df['Etapa'].isin(['Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento'])]
        if not df_top.empty:
            ranking = df_top[col_utm].value_counts().head(3).reset_index()
            cols = st.columns(3)
            for i, row in ranking.iterrows():
                with cols[i]:
                    st.markdown(f'<div class="campaign-card"><small>TOP {i+1}</small><b>{row.iloc[0]}</b><div class="val">{row.iloc[1]}</div><small>Leads Avançados</small></div>', unsafe_allow_html=True)
        st.write("")
        cl, cr = st.columns(2)
        with cl: st.plotly_chart(px.pie(df, names=col_utm, hole=0.5, title="Mix de Marketing"), use_container_width=True)
        with cr:
            df_c = df['Campanha'].value_counts().head(10).reset_index()
            fig_c = px.bar(df_c, x='count', y='Campanha', orientation='h', title="Top 10 Campanhas", color='count', color_continuous_scale='Blues')
            fig_c.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_c, use_container_width=True)

    with tab2:
        st.subheader("📊 Saúde Comercial do Funil")
        
        ck1, ck2 = st.columns(2)
        with ck1:
            metric_card("🚫 Descarte na Entrada", f"{inalc} Leads", f"({(inalc/total_leads*100):.1f}%) Perdidos sem contato", "card-red")
        with ck2:
            metric_card("✅ Leads Alcançados", f"{total_leads - inalc} Leads", f"({(100-(inalc/total_leads*100)):.1f}%) Iniciaram conversa", "card-green")

        st.write("")
        ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
        df_f = df['Etapa'].value_counts().reindex(ordem).fillna(0).reset_index()
        fig_fun = go.Figure(go.Funnel(y=df_f['Etapa'], x=df_f['count'], textinfo="value+percent initial", marker={"color": ["#34495e", "#2980b9", "#3498db", "#1abc9c", "#16a085", "#27ae60"]}))
        
        st.plotly_chart(fig_fun, use_container_width=True)

    with tab3:
        st.subheader("🚫 Motivos de Perda (Polos)")
        df_lost = df[df['Status_Calc'] == 'Perdido'].copy()
        if not df_lost.empty:
            mask = (df_lost['Motivo de Perda'].str.lower() != 'sem resposta') | (df_lost['Etapa'].str.lower() == 'aguardando resposta')
            motivos = df_lost[mask]['Motivo de Perda'].value_counts().head(10).reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            motivos['Perc'] = (motivos['Qtd'] / total_leads * 100).round(1)
            motivos['Label'] = motivos.apply(lambda x: f"<b>{int(x['Qtd'])}</b><br>{x['Perc']}%", axis=1)
            fig_loss = go.Figure(data=[go.Bar(x=motivos['Motivo'], y=motivos['Qtd'], text=motivos['Label'], textposition='outside', marker_color='#e74c3c', opacity=0.9)])
            fig_loss.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', margin=dict(t=60, b=20), height=550, xaxis=dict(showgrid=False, tickfont=dict(size=12, color='#2c3e50')), yaxis=dict(showticklabels=False, showgrid=True, gridcolor='#f0f2f6'))
            st.plotly_chart(fig_loss, use_container_width=True)
        else: st.success("Nenhuma perda registrada.")

# ==============================================================================
# 4. INTERFACE PRINCIPAL
# ==============================================================================
st.title("🚀 BI Expansão Performance")
modo = st.radio("Selecione o Modo:", ["📥 Importar Planilha", "🗄️ Histórico Gerencial"], horizontal=True)

if modo == "📥 Importar Planilha":
    mapeamento = {"Prepara IA": "Prepara", "Microlins": "Microlins", "Ensina Mais TM Pedro": "Pedro", "Ensina Mais TM Luciana": "Luciana"}
    marca_sel = st.sidebar.selectbox("Marca / Consultor:", list(mapeamento.keys()))
    file = st.sidebar.file_uploader("Subir arquivo .csv", type=['csv'])
    if file:
        df_raw = process_data(load_data(file))
        if not df_raw.empty:
            termo = mapeamento[marca_sel]
            col_resp = next((c for c in df_raw.columns if any(x in c for x in ['Proprietário', 'Responsável', 'Consultor'])), None)
            if col_resp:
                df_filtrado = df_raw[df_raw[col_resp].astype(str).str.contains(termo, case=False, na=False)].copy()
                semana = st.sidebar.selectbox("Semana:", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
                if st.sidebar.button("💾 Salvar Histórico"):
                    if salvar_no_gsheets(df_filtrado, semana, marca_sel): st.sidebar.success("✅ Salvo!")
                renderizar_dashboard_completo(df_filtrado, f"Análise: {marca_sel}")

else:
    df_h = carregar_historico_gsheets()
    if not df_h.empty:
        f_marca = st.sidebar.selectbox("Filtrar Marca / Consultor:", ["Todas"] + list(df_h['marca_ref'].unique()))
        df_v = df_h[df_h['marca_ref'] == f_marca] if f_marca != "Todas" else df_h
        renderizar_dashboard_completo(df_v, f"Histórico: {f_marca}")
    else: st.warning("Banco de dados vazio.")
