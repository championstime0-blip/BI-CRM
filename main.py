import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Performance Pro", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .st-emotion-cache-1r6slb0 { border: 1px solid #333; padding: 15px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. CONEXÃO E BANCO DE DADOS
# ==============================================================================
def conectar_gsheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if "CREDENCIAIS_GOOGLE" in os.environ:
            creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
        elif "gsheets" in st.secrets:
            creds_dict = dict(st.secrets["gsheets"])
        else: return None
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds).open("BI_Historico").sheet1
    except: return None

def salvar_no_gsheets(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet:
        cols_essenciais = ['Etapa', 'Status_Calc', 'Cidade_Clean', 'Motivo de Perda', 'Fonte', 'Campanha']
        for c in cols_essenciais: 
            if c not in df.columns: df[c] = '-'
        df_save = df[cols_essenciais].copy()
        df_save['semana_ref'] = semana
        df_save['marca_ref'] = marca
        df_save['data_upload'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_save = df_save[['data_upload', 'semana_ref', 'marca_ref'] + cols_essenciais].fillna('-')
        sheet.append_rows(df_save.values.tolist())
        return True
    return False

def carregar_historico_gsheets():
    sheet = conectar_gsheets()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            mapa = {'status': 'Status_Calc', 'etapa': 'Etapa', 'cidade': 'Cidade_Clean', 'motivo_perda': 'Motivo de Perda'}
            df.rename(columns=mapa, inplace=True)
            required = ['Status_Calc', 'Etapa', 'Motivo de Perda', 'data_upload']
            for col in required:
                if col not in df.columns: df[col] = 'Não Informado'
        return df
    return pd.DataFrame()

def deletar_semana_especifica(marca, ano, mes_num, semana):
    sheet = conectar_gsheets()
    if sheet:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        df['dt'] = pd.to_datetime(df['data_upload'], errors='coerce')
        mask_manter = ~((df['marca_ref'] == marca) & (df['dt'].dt.year == ano) & (df['dt'].dt.month == mes_num) & (df['semana_ref'] == semana))
        df_novo = df[mask_manter].drop(columns=['dt'])
        sheet.clear()
        sheet.append_row(list(df_novo.columns))
        if not df_novo.empty: sheet.append_rows(df_novo.values.tolist())
        return True
    return False

# ==============================================================================
# 2. MOTOR DE VISUALIZAÇÃO (FUNIL TOTALIZADOR)
# ==============================================================================
def renderizar_dashboard_pro(df_atual, df_anterior=pd.DataFrame(), titulo="BI"):
    total_leads = len(df_atual)
    vendas = len(df_atual[df_atual['Status_Calc'] == 'Ganho'])
    conv_total = (vendas / total_leads * 100) if total_leads > 0 else 0
    
    st.markdown(f"### {titulo}")
    
    # KPIs principais
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume de Leads", total_leads)
    c2.metric("Conversão Geral", f"{conv_total:.1f}%")
    c3.metric("Ticket Médio (Estimado)", "R$ --") # Placeholder para futura integração
    
    st.divider()

    tab1, tab2 = st.tabs(["📉 Funil Profissional (% Total)", "🚫 Motivos de Perda"])

    with tab1:
        st.subheader("Funil de Impacto sobre Leads Totais")
        if 'Etapa' in df_atual.columns:
            # Agrupa e ordena
            df_funil = df_atual['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            
            existentes = [c for c in ordem if c in df_funil['Etapa'].values]
            df_funil.set_index('Etapa', inplace=True)
            df_funil = df_funil.reindex(existentes).reset_index()

            # Cálculo do percentual em relação ao TOTAL de leads
            df_funil['Percentual_Total'] = df_funil['Volume'].apply(lambda x: (x / total_leads * 100) if total_leads > 0 else 0)
            
            # Formatação de texto para o gráfico: "Volume (Percentual%)"
            df_funil['Texto_Label'] = df_funil.apply(lambda row: f"{row['Volume']} ({row['Percentual_Total']:.1f}%)", axis=1)

            # Criando o Funil Profissional
            fig_funnel = go.Figure(go.Funnel(
                y = df_funil['Etapa'],
                x = df_funil['Volume'],
                text = df_funil['Texto_Label'],
                textinfo = "text", # Força a exibir nosso label personalizado
                hoverinfo = "y+x+percent initial+percent previous",
                marker = {"color": ["#3498db", "#2980b9", "#1abc9c", "#16a085", "#2ecc71", "#27ae60"]},
                connector = {"line": {"color": "#444", "dash": "dot", "width": 1}}
            ))

            fig_funnel.update_layout(
                margin=dict(l=150, r=20, t=20, b=20),
                height=450,
                yaxis={'categoryorder':'manual', 'categoryarray':existentes[::-1]}
            )
            
            st.plotly_chart(fig_funnel, use_container_width=True)
            st.info(f"💡 Todas as porcentagens acima são relativas ao volume total de **{total_leads} leads**.")

    with tab2:
        df_lost = df_atual[df_atual['Status_Calc'] == 'Perdido']
        if not df_lost.empty:
            motivos = df_lost['Motivo de Perda'].value_counts().reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            motivos['Percent_Global'] = motivos['Qtd'].apply(lambda x: (x/total_leads*100))
            fig = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', text=motivos['Percent_Global'].apply(lambda x: f"{x:.1f}% do total"))
            st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# 3. INTERFACE E NAVEGAÇÃO
# ==============================================================================
st.title("🚀 BI Alta Performance v7.0")
modo = st.radio("Selecione:", ["📥 Importar Planilha", "🗄️ Histórico & Comparativo"], horizontal=True)

if modo == "📥 Importar Planilha":
    marca = st.sidebar.selectbox("Unidade:", ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    if marca != "Selecione...":
        file = st.sidebar.file_uploader("Subir CSV", type='csv')
        if file:
            df_raw = pd.read_csv(file, sep=None, engine='python')
            
            # Lógica de processamento básica para o upload
            def quick_proc(df):
                # Status inteligente
                def get_status(row):
                    etapa = str(row.get('Etapa', '')).lower()
                    motivo = str(row.get('Motivo de Perda', '')).lower()
                    if 'venda' in etapa or 'fechamento' in etapa: return 'Ganho'
                    if motivo in ['nan', '', 'none', '-'] or 'nada' in motivo: return 'Em Andamento'
                    return 'Perdido'
                df['Status_Calc'] = df.apply(get_status, axis=1)
                return df
            
            df_proc = quick_proc(df_raw)
            
            # Filtro de marca no upload
            col_resp = next((c for c in df_proc.columns if c in ['Proprietário', 'Responsável', 'Consultor']), None)
            if marca != "Todas as Marcas" and col_resp:
                termo = marca.split(' ')[-1]
                df_proc = df_proc[df_proc[col_resp].astype(str).str.contains(termo, case=False, na=False)]

            sem = st.sidebar.selectbox("Semana:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
            if st.sidebar.button("💾 Enviar p/ Google Sheets"):
                if salvar_no_gsheets(df_proc, sem, marca): st.sidebar.success("✅ Sucesso!")

            renderizar_dashboard_pro(df_proc, titulo=f"Preview: {marca}")

elif modo == "🗄️ Histórico & Comparativo":
    df_h = carregar_historico_gsheets()
    if df_h.empty: st.info("O banco de dados está vazio.")
    else:
        df_h['dt'] = pd.to_datetime(df_h['data_upload'])
        df_h['Ano'] = df_h['dt'].dt.year
        df_h['M_N'] = df_h['dt'].dt.month
        ms = {1:'Jan', 2:'Fev', 3:'Mar', 4:'Abr', 5:'Mai', 6:'Jun', 7:'Jul', 8:'Ago', 9:'Set', 10:'Out', 11:'Nov', 12:'Dez'}

        m_sel = st.sidebar.selectbox("Marca:", sorted(df_h['marca_ref'].unique()))
        df_m = df_h[df_h['marca_ref'] == m_sel]
        
        a_sel = st.sidebar.selectbox("Ano:", sorted(df_m['Ano'].unique(), reverse=True))
        df_a = df_m[df_m['Ano'] == a_sel]
        
        mes_sel = st.sidebar.selectbox("Mês:", [ms[m] for m in sorted(df_a['M_N'].unique())])
        m_num = [k for k,v in ms.items() if v == mes_sel][0]
        df_mes = df_a[df_a['M_N'] == m_num]
        
        sem_list = sorted(df_mes['semana_ref'].unique())
        sem_sel = st.sidebar.selectbox("Semana:", sem_list, index=len(sem_list)-1)
        
        df_atual = df_mes[df_mes['semana_ref'] == sem_sel]
        
        renderizar_dashboard_pro(df_atual, titulo=f"Análise Gerencial: {m_sel}")

        # --- SISTEMA DE LIMPEZA SELETIVA ---
        st.sidebar.divider()
        st.sidebar.subheader("🗑️ Gerenciar Dados")
        if st.sidebar.button(f"Excluir {sem_sel}"):
            st.sidebar.warning("Confirme a exclusão:")
            if st.sidebar.checkbox("Sim, apagar esta semana."):
                if deletar_semana_especifica(m_sel, a_sel, m_num, sem_sel):
                    st.sidebar.success("Apagado!")
                    time.sleep(1)
                    st.rerun()
