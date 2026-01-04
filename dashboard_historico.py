import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Histórico | BI Expansão", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (NEON/DARK - MESMO PADRÃO)
# =========================
st.markdown("""
<style>
/* Importando Fonte Sci-Fi */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');

.stApp { background-color: #0b0f1a; color: #e0e0e0; }

/* TÍTULOS */
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 42px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 3px; margin-bottom: 20px; text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}

.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 22px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px; display: flex; align-items: center;
}
.sub-icon { margin-right: 12px; font-size: 24px; color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.6); }

/* CARDS DE KPI HISTÓRICO */
.card {
    background: linear-gradient(135deg, #111827, #020617); padding: 20px; border-radius: 12px;
    border: 1px solid #1e293b; text-align: center; box-shadow: 0 0 15px rgba(56,189,248,0.05);
    height: 100%; transition: transform 0.3s;
}
.card:hover { transform: translateY(-5px); border-color: #22d3ee; }
.card-label { font-family: 'Rajdhani', sans-serif; font-size: 12px; text-transform: uppercase; color: #94a3b8; letter-spacing: 1px; }
.card-val { font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 700; color: #fff; margin-top: 5px; }

/* CHECKBOX E SELECTBOX */
.stSelectbox label { color: #22d3ee !important; font-family: 'Rajdhani', sans-serif; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================
def conectar_google_sheets():
    # Escopo de acesso
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Busca credenciais nas variáveis de ambiente
    json_creds = os.environ.get("CREDENCIAIS_GOOGLE")
    
    if not json_creds:
        st.error("❌ Erro: Variável de ambiente 'CREDENCIAIS_GOOGLE' não encontrada.")
        st.stop() # Para a execução se não tiver credencial

    try:
        creds_dict = json.loads(json_creds)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Erro na autenticação do Google: {e}")
        return None

# =========================
# CARREGAMENTO DE DADOS
# =========================
def listar_marcas_disponiveis():
    client = conectar_google_sheets()
    if not client: return []
    try:
        # Abre a planilha pelo nome exato
        sh = client.open("BI_Historico")
        # Retorna lista de títulos das abas
        return [ws.title for ws in sh.worksheets()]
    except gspread.SpreadsheetNotFound:
        st.error("Planilha 'BI_Historico' não encontrada.")
        return []
    except Exception as e:
        st.error(f"Erro ao listar marcas: {e}")
        return []

def carregar_dados_marca(marca):
    client = conectar_google_sheets()
    if not client: return pd.DataFrame()
    
    try:
        sh = client.open("BI_Historico")
        ws = sh.worksheet(marca)
        data = ws.get_all_records() # Lê tudo como lista de dicionários
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return df
            
        # --- LIMPEZA E TIPAGEM DE DADOS ---
        # 1. Converter Taxa % (string "15.5%") para float (15.5)
        if 'Taxa Avanço Funil' in df.columns:
            df['Taxa_Num'] = df['Taxa Avanço Funil'].astype(str).str.replace('%', '').str.replace(',', '.').astype(float)
        
        # 2. Garantir que colunas numéricas sejam números
        cols_numericas = ['Total Leads', 'Em Andamento', 'Perdidos', 'Perda s/ Resp']
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
        
        return df
        
    except Exception as e:
        st.error(f"Erro ao ler dados da marca {marca}: {e}")
        return pd.DataFrame()

# =========================
# INTERFACE DO DASHBOARD
# =========================
def main():
    st.markdown('<div class="futuristic-title">💠 Monitoramento Histórico</div>', unsafe_allow_html=True)

    # 1. SIDEBAR: SELEÇÃO DE MARCA
    st.sidebar.header("🎛️ Navegação")
    marcas = listar_marcas_disponiveis()
    
    if not marcas:
        st.warning("⚠️ Nenhuma aba encontrada na planilha 'BI_Historico'. Salve algum dado primeiro.")
        return

    marca_selecionada = st.sidebar.selectbox("Selecione a Marca para Análise", marcas)
    
    if st.sidebar.button("🔄 Atualizar Dados"):
        st.rerun()

    # 2. CARREGA DADOS
    df = carregar_dados_marca(marca_selecionada)

    if df.empty:
        st.info(f"A aba '{marca_selecionada}' existe mas está vazia.")
        return

    # Pega o último registro (mais recente)
    ultimo_registro = df.iloc[-1]
    
    # --- SEÇÃO A: STATUS ATUAL ---
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">⚡</span>Status Recente: {ultimo_registro["Semana Ref"]}</div>', unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    
    def kpi(label, val, suf=""):
        st.markdown(f"""
        <div class="card">
            <div class="card-label">{label}</div>
            <div class="card-val">{val}{suf}</div>
        </div>
        """, unsafe_allow_html=True)

    with c1: kpi("Total Leads", ultimo_registro['Total Leads'])
    with c2: kpi("Em Andamento", ultimo_registro['Em Andamento'])
    with c3: kpi("Perdidos", ultimo_registro['Perdidos'])
    with c4: kpi("Taxa Avanço", ultimo_registro['Taxa Avanço Funil']) # Já vem com % do banco

    # --- SEÇÃO B: GRÁFICOS DE EVOLUÇÃO ---
    st.markdown('<div class="futuristic-sub"><span class="sub-icon">📈</span>Evolução Temporal</div>', unsafe_allow_html=True)
    
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        # GRÁFICO 1: LINHA DO TEMPO (VOLUME)
        # Mostra o crescimento de leads e perdas ao longo das semanas
        fig_vol = go.Figure()
        
        fig_vol.add_trace(go.Scatter(
            x=df['Semana Ref'], y=df['Total Leads'],
            mode='lines+markers', name='Total Leads',
            line=dict(color='#22d3ee', width=3),
            fill='tozeroy', fillcolor='rgba(34, 211, 238, 0.1)'
        ))
        
        fig_vol.add_trace(go.Scatter(
            x=df['Semana Ref'], y=df['Perdidos'],
            mode='lines+markers', name='Perdidos',
            line=dict(color='#ef4444', width=3)
        ))

        fig_vol.update_layout(
            title="Tendência de Volume",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Rajdhani"),
            xaxis_title=None,
            yaxis_title=None,
            hovermode="x unified"
        )
        st.plotly_chart(fig_vol, use_container_width=True)

    with col_chart2:
        # GRÁFICO 2: BARRAS (EFICIÊNCIA)
        # Mostra como a taxa de avanço oscilou
        fig_taxa = px.bar(
            df, x='Semana Ref', y='Taxa_Num',
            title="Evolução da Taxa de Avanço (%)",
            text=df['Taxa_Num'].apply(lambda x: f"{x}%"),
            color='Taxa_Num',
            color_continuous_scale=['#1e293b', '#22d3ee']
        )
        
        fig_taxa.update_traces(
            textposition='outside',
            marker_line_color='#22d3ee',
            marker_line_width=1
        )
        fig_taxa.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Rajdhani"),
            xaxis_title=None,
            yaxis_title=None,
            showlegend=False
        )
        st.plotly_chart(fig_taxa, use_container_width=True)

    # --- SEÇÃO C: TABELA ---
    st.markdown('<div class="futuristic-sub"><span class="sub-icon">📋</span>Base de Dados Completa</div>', unsafe_allow_html=True)
    
    # Mostra tabela sem a coluna auxiliar 'Taxa_Num'
    df_show = df.drop(columns=['Taxa_Num'], errors='ignore')
    st.dataframe(
        df_show, 
        use_container_width=True, 
        hide_index=True
    )

if __name__ == "__main__":
    main()
