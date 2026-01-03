import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import io
import time
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="BI Performance Expansão", layout="wide")

# --- ESTILIZAÇÃO CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .st-emotion-cache-1r6slb0 { border: 1px solid #333; padding: 15px; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 1. MOTOR DE PROCESSAMENTO (LISTA CRM vs MATRIZ PAINEL)
# ==============================================================================
def processar_dados_input(uploaded_file, semana_manual):
    try:
        content = uploaded_file.getvalue().decode('utf-8-sig')
        # Tenta detetar o separador do CSV
        sep = ';' if ';' in content.splitlines()[0] else ','
        
        # Leitura inicial para teste de formato
        df_test = pd.read_csv(io.StringIO(content), sep=sep, nrows=10, engine='python')
        
        # --- CASO A: MATRIZ (Painéis Mensais) ---
        if "TOTAL DE LEADS" in content.upper():
            df_raw = pd.read_csv(io.StringIO(content), header=None, sep=sep)
            # Localiza a linha do cabeçalho das semanas
            header_row = 0
            for i, row in df_raw.iterrows():
                if any("SEM" in str(x).upper() for x in row.values):
                    header_row = i
                    break
            
            df = pd.read_csv(io.StringIO(content), skiprows=header_row, sep=sep)
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Valida se a semana escolhida manualmente existe no arquivo
            col_semana = semana_manual.upper()
            if col_semana not in df.columns:
                st.error(f"A coluna {col_semana} não foi encontrada neste arquivo.")
                return pd.DataFrame(), None

            # Transpõe para o formato de BI
            col_desc = df.columns[0]
            df_final = df[[col_desc, col_semana]].copy()
            df_final.columns = ['Descricao', 'Valor']
            df_final['Valor'] = pd.to_numeric(df_final['Valor'], errors='coerce').fillna(0)
            return df_final, "MATRIZ"

        # --- CASO B: LISTA (CRM Pedro.csv) ---
        else:
            df = pd.read_csv(io.StringIO(content), sep=sep)
            # Normalização de Status e Cidade
            df['Status_Calc'] = df.apply(lambda r: 'Ganho' if 'venda' in str(r.get('Etapa', '')).lower() 
                                       else ('Em Andamento' if str(r.get('Motivo de Perda', '')) in ['nan', 'Nada', ''] 
                                       else 'Perdido'), axis=1)
            # Extrai fonte e campanha para o BI
            df['Fonte'] = df['Fonte'].fillna('Não Informado')
            df['Campanha'] = df['Campanha'].fillna('Não Informado')
            return df, "LISTA"

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
        return pd.DataFrame(), None

# ==============================================================================
# 2. DASHBOARD DE PERFORMANCE (FUNIL DE IMPACTO TOTAL)
# ==============================================================================
def renderizar_dashboard_performance(df, tipo, titulo):
    if tipo == "MATRIZ":
        def gv(n): return df[df['Descricao'].str.contains(n, case=False, na=False)]['Valor'].sum()
        leads = gv("TOTAL DE LEADS")
        interesse = gv("CONFIRMOU INTERESSE")
        reuniao = gv("REUNIÃO")
        vendas = gv("FATURADO")
    else:
        leads = len(df)
        interesse = len(df[df['Etapa'] == 'Confirmou Interesse'])
        reuniao = len(df[df['Etapa'].str.contains('Reunião', na=False)])
        vendas = len(df[df['Status_Calc'] == 'Ganho'])

    conv = (vendas / leads * 100) if leads > 0 else 0
    
    st.markdown(f"## {titulo}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Leads Totais (Topo)", int(leads))
    c2.metric("Conversão Real", f"{conv:.1f}%", delta="Conversão Geral", delta_color="normal" if conv > 5 else "inverse")
    c3.metric("Aproveitamento", int(interesse))

    st.divider()

    # FUNIL DE IMPACTO SOBRE O TOTAL
    st.subheader("Funil Profissional (% em relação ao Total de Leads)")
    
    fig = go.Figure(go.Funnel(
        y = ["Total Leads", "Interesse", "Reunião", "Venda"],
        x = [leads, interesse, reuniao, vendas],
        textinfo = "value+percent initial", # Percentual em relação ao TOPO
        marker = {"color": ["#1f77b4", "#3498db", "#1abc9c", "#2ecc71"]},
        connector = {"line": {"color": "#444", "dash": "dot", "width": 1}}
    ))
    
    fig.update_layout(height=450, margin=dict(l=150, r=20, t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)
    
    

    # BI DE CAMPANHA (Se for Lista CRM)
    if tipo == "LISTA":
        st.divider()
        st.subheader("🎯 BI de Campanhas e Origens")
        df_camp = df['Fonte'].value_counts().reset_index()
        fig_pie = px.pie(df_camp, values='count', names='Fonte', hole=0.5, title="Mix de Marketing")
        st.plotly_chart(fig_pie, use_container_width=True)

# ==============================================================================
# 3. INTERFACE E NAVEGAÇÃO
# ==============================================================================
st.title("📊 BI Expansão Performance")

with st.sidebar:
    st.header("Configurações")
    modo = st.radio("Menu", ["📥 Importação Manual", "🗄️ Histórico Gerencial"])
    
    if modo == "📥 Importação Manual":
        marca = st.selectbox("Consultor/Marca", ["Pedro Lima Lima", "Lu", "Prepara IA", "Microlins"])
        file = st.file_uploader("Subir arquivo (CSV)", type=['csv'])
        
        # SELEÇÃO MANUAL DA SEMANA APÓS O INPUT
        st.divider()
        st.subheader("Agendamento")
        semana_manual = st.selectbox("Selecione a Semana p/ Salvar:", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
        
        if file and st.button("💾 Salvar no Histórico"):
            st.warning("Deseja confirmar o salvamento?")
            if st.checkbox("Sim, gravar dados permanentemente."):
                # Aqui entra a chamada para o Google Sheets (salvar_no_gsheets)
                st.success(f"Dados salvos na {semana_manual}!")

if modo == "📥 Importação Manual" and file:
    df_proc, tipo_data = processar_dados_input(file, semana_manual)
    
    if not df_proc.empty:
        renderizar_dashboard_performance(df_proc, tipo_data, f"Preview: {marca} ({semana_manual})")
        
        # Opção de download do arquivo corrigido
        st.sidebar.divider()
        csv_data = df_proc.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.sidebar.download_button("📥 Baixar Planilha Corrigida", csv_data, f"BI_{semana_manual}.csv", "text/csv")
