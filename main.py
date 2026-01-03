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
# 2. MOTOR DE VISUALIZAÇÃO (FUNIL TOTALIZADOR + SEMÁFORO)
# ==============================================================================
def renderizar_dashboard_pro(df_atual, titulo="BI"):
    total_leads = len(df_atual)
    vendas = len(df_atual[df_atual['Status_Calc'] == 'Ganho'])
    conv_total = (vendas / total_leads * 100) if total_leads > 0 else 0
    
    st.markdown(f"### {titulo}")
    
    # --- LÓGICA DO SEMÁFORO ---
    if conv_total < 3: color_label = "inverse" # Vermelho
    elif conv_total < 7: color_label = "off" # Amarelo/Cinza
    else: color_label = "normal" # Verde
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Volume de Leads", total_leads)
    c2.metric("Conversão Geral", f"{conv_total:.1f}%", delta="Performance", delta_color=color_label)
    
    # Cálculo de Avanço de Funil (Leads que passaram da primeira etapa)
    avanco = (len(df_atual[df_atual['Etapa'] != 'Aguardando Resposta']) / total_leads * 100) if total_leads > 0 else 0
    c3.metric("Aproveitamento de Base", f"{avanco:.1f}%")
    
    st.divider()

    tab1, tab2 = st.tabs(["📉 Funil de Impacto (% Total)", "🚫 Motivos de Perda"])

    with tab1:
        st.subheader("Funil de Conversão Profissional")
        if 'Etapa' in df_atual.columns:
            # Agrupa e ordena conforme o fluxo comercial
            df_funil = df_atual['Etapa'].value_counts().reset_index()
            df_funil.columns = ['Etapa', 'Volume']
            ordem = ['Aguardando Resposta', 'Confirmou Interesse', 'Qualificado', 'Reunião Agendada', 'Reunião Realizada', 'Venda/Fechamento']
            
            existentes = [c for c in ordem if c in df_funil['Etapa'].values]
            df_funil.set_index('Etapa', inplace=True)
            df_funil = df_funil.reindex(existentes).reset_index()

            # Texto customizado: Quantidade + % do Total
            df_funil['Texto_Label'] = df_funil.apply(lambda r: f"{r['Volume']} ({ (r['Volume']/total_leads*100):.1f}%)", axis=1)

            fig_funnel = go.Figure(go.Funnel(
                y = df_funil['Etapa'],
                x = df_funil['Volume'],
                text = df_funil['Texto_Label'],
                textinfo = "text",
                marker = {"color": ["#3498db", "#2980b9", "#1abc9c", "#16a085", "#2ecc71", "#27ae60"]},
                connector = {"line": {"color": "#444", "dash": "dot", "width": 1}}
            ))

            fig_funnel.update_layout(
                margin=dict(l=150, r=20, t=20, b=20),
                height=450,
                # CORREÇÃO DO ERRO: categoryorder agora é 'array'
                yaxis={'categoryorder':'array', 'categoryarray':existentes[::-1]}
            )
            
            st.plotly_chart(fig_funnel, use_container_width=True)
            st.caption(f"ℹ️ Porcentagens calculadas sobre o total de {total_leads} leads.")

    with tab2:
        df_lost = df_atual[df_atual['Status_Calc'] == 'Perdido']
        if not df_lost.empty:
            motivos = df_lost['Motivo de Perda'].value_counts().reset_index()
            motivos.columns = ['Motivo', 'Qtd']
            motivos['Percent_Total'] = motivos['Qtd'].apply(lambda x: (x/total_leads*100))
            
            fig = px.bar(motivos, x='Qtd', y='Motivo', orientation='h', 
                         text=motivos['Percent_Total'].apply(lambda x: f"{x:.1f}% do total"),
                         title="Impacto das Perdas no Volume Total")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Excelente! Sem perdas registradas neste período.")

# ==============================================================================
# 3. INTERFACE E NAVEGAÇÃO
# ==============================================================================
st.title("🚀 BI Alta Performance v7.1")
modo = st.radio("Selecione:", ["📥 Importar Planilha", "🗄️ Histórico & Comparativo"], horizontal=True)

if modo == "📥 Importar Planilha":
    marca = st.sidebar.selectbox("Unidade:", ["Selecione...", "Todas as Marcas", "Prepara IA", "Microlins", "Ensina Mais TM Pedro", "Ensina Mais TM Luciana"])
    if marca != "Selecione...":
        file = st.sidebar.file_uploader("Subir CSV", type='csv')
        if file:
            # Carregamento robusto
            try:
                df_raw = pd.read_csv(file, sep=None, engine='python', on_bad_lines='skip')
                
                # Processamento de Status
                def process_status(row):
                    etapa = str(row.get('Etapa', '')).lower()
                    motivo = str(row.get('Motivo de Perda', '')).lower()
                    if 'venda' in etapa or 'fechamento' in etapa or 'matrícula' in etapa: return 'Ganho'
                    if motivo in ['nan', '', 'none', '-', 'null'] or 'nada' in motivo: return 'Em Andamento'
                    return 'Perdido'
                
                df_raw['Status_Calc'] = df_raw.apply(process_status, axis=1)
                
                # Filtro de Unidade
                df_f = df_raw.copy()
                col_resp = next((c for c in df_f.columns if c in ['Proprietário', 'Responsável', 'Consultor', 'Dono do lead']), None)
                if marca != "Todas as Marcas" and col_resp:
                    termo = marca.split(' ')[-1]
                    df_f = df_f[df_f[col_resp].astype(str).str.contains(termo, case=False, na=False)]

                st.sidebar.divider()
                sem = st.sidebar.selectbox("Semana para Salvar:", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])
                if st.sidebar.button("💾 Enviar p/ Google Sheets"):
                    if salvar_no_gsheets(df_f, sem, marca):
                        st.sidebar.success(f"✅ {marca} Salvo!")
                
                renderizar_dashboard_pro(df_f, titulo=f"Preview Atual: {marca}")
            except Exception as e:
                st.error(f"Erro ao processar arquivo: {e}")

elif modo == "🗄️ Histórico & Comparativo":
    df_h = carregar_historico_gsheets()
    if df_h.empty: 
        st.info("O banco de dados está vazio. Importe uma planilha primeiro.")
    else:
        # Preparação de Filtros
        df_h['dt'] = pd.to_datetime(df_h['data_upload'], errors='coerce')
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
        sem_sel = st.sidebar.selectbox("Semana Analisada:", sem_list, index=len(sem_list)-1)
        
        df_view = df_mes[df_mes['semana_ref'] == sem_sel]
        
        renderizar_dashboard_pro(df_view, titulo=f"Gerencial: {m_sel} ({sem_sel})")

        # --- EXCLUSÃO SEGURA ---
        st.sidebar.divider()
        st.sidebar.subheader("🗑️ Gerenciar")
        if st.sidebar.button(f"Excluir {sem_sel}"):
            st.sidebar.error("Confirme no campo abaixo:")
            if st.sidebar.checkbox("Sim, apagar estes dados permanentemente."):
                if deletar_semana_especifica(m_sel, a_sel, m_num, sem_sel):
                    st.sidebar.success("Excluído!")
                    time.sleep(1)
                    st.rerun()
