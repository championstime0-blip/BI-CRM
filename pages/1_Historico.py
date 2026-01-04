import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Histórico | BI Expansão", layout="wide")

# =========================
# ESTILIZAÇÃO CSS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 42px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 20px; text-shadow: 0 0 20px rgba(34, 211, 238, 0.3);
}
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 20px; border-radius: 12px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); height: 100%;
}
.card-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 700;
    color: #22d3ee;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE
# =========================
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        if not creds_json: return None
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Erro de credenciais: {e}")
        return None

# =========================
# FUNÇÃO DE LEITURA (BLINDADA)
# =========================
def carregar_dados(marca):
    client = conectar_google()
    if not client: return pd.DataFrame()
    
    try:
        sh = client.open("BI_Historico")
        ws = sh.worksheet(marca)
        
        # Usa get_all_values para evitar erro de cabeçalho duplicado
        dados_brutos = ws.get_all_values()
        
        if not dados_brutos:
            return pd.DataFrame() 
            
        headers = dados_brutos[0]
        linhas = dados_brutos[1:]
        
        df = pd.DataFrame(linhas, columns=headers)
        
        # Remove colunas vazias geradas pelo Sheets
        cols_validas = [c for c in df.columns if str(c).strip() != ""]
        df = df[cols_validas]
        
        return df
    except Exception as e:
        return pd.DataFrame()

# =========================
# INTERFACE PRINCIPAL
# =========================
st.markdown('<div class="futuristic-title">📜 Histórico de Performance</div>', unsafe_allow_html=True)

# 1. SELEÇÃO DA MARCA
st.sidebar.header("🗂️ Seleção de Base")
marca_sel = st.sidebar.selectbox("Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])

# 2. CARREGAMENTO COM PROTEÇÃO
df = carregar_dados(marca_sel)

if not df.empty:
    # --- PADRONIZAÇÃO DE NOMES ---
    cols_map = {c: c for c in df.columns}
    for c in df.columns:
        c_low = str(c).lower().strip()
        if "top" in c_low and "fonte" in c_low: cols_map[c] = "Top Fonte"
        elif "taxa" in c_low: cols_map[c] = "Taxa"
        elif "respons" in c_low: cols_map[c] = "Responsável"
        elif "semana" in c_low: cols_map[c] = "Semana"
        elif "data" in c_low: cols_map[c] = "Data"
        elif "total" in c_low: cols_map[c] = "Total"
        elif "perdido" in c_low: cols_map[c] = "Perdidos"
    
    df = df.rename(columns=cols_map)
    
    # --- TRATAMENTO DE DADOS (CORREÇÃO DO ERRO) ---
    
    # 1. Data
    if "Data" in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Data'])
    
    # 2. Números Inteiros
    for col_num in ['Total', 'Perdidos']:
        if col_num in df.columns:
            df[col_num] = pd.to_numeric(df[col_num], errors='coerce').fillna(0).astype(int)

    # 3. Taxa (AQUI ESTAVA O ERRO)
    # A correção: usamos 'coerce' para transformar vazios em NaN, e depois fillna(0.0)
    if "Taxa" in df.columns:
        # Primeiro limpa string, depois converte
        clean_taxa = df['Taxa'].astype(str).str.replace('%', '').str.replace(',', '.')
        df['Taxa_Num'] = pd.to_numeric(clean_taxa, errors='coerce').fillna(0.0)
    else:
        df['Taxa_Num'] = 0.0

    # 4. Strings faltantes
    if "Top Fonte" not in df.columns: df["Top Fonte"] = "N/A"
    if "Responsável" not in df.columns: df["Responsável"] = "N/A"
    if "Semana" not in df.columns: df["Semana"] = "N/A"

    # --- FILTROS ---
    st.sidebar.divider()
    st.sidebar.header("🔍 Filtros")
    
    # Filtro Ano
    anos = sorted(df['Data'].dt.year.unique().astype(int)) if "Data" in df.columns else []
    ano_sel = st.sidebar.multiselect("Ano", anos, default=anos)
    
    # Filtro Mês
    if "Data" in df.columns:
        meses_map = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
        df['Mes_Num'] = df['Data'].dt.month
        df['Mes_Nome'] = df['Mes_Num'].map(meses_map)
        meses_disp = df[['Mes_Num', 'Mes_Nome']].drop_duplicates().sort_values('Mes_Num')
        mes_sel = st.sidebar.multiselect("Mês", meses_disp['Mes_Nome'].unique(), default=meses_disp['Mes_Nome'].unique())
    else:
        mes_sel = []

    # Filtro Consultor
    consultores = df['Responsável'].unique()
    consultor_sel = st.sidebar.multiselect("Consultor", consultores, default=consultores)

    # Filtro Semana
    semanas = df['Semana'].unique()
    semana_sel = st.sidebar.multiselect("Semana", semanas, default=semanas)

    # --- APLICAÇÃO DOS FILTROS ---
    mask = pd.Series(True, index=df.index)
    if "Data" in df.columns:
        mask &= df['Data'].dt.year.isin(ano_sel)
        mask &= df['Mes_Nome'].isin(mes_sel)
    mask &= df['Responsável'].isin(consultor_sel)
    mask &= df['Semana'].isin(semana_sel)
    
    df_filtrado = df.loc[mask]

    if not df_filtrado.empty:
        # --- KPIS ---
        total_leads = df_filtrado['Total'].sum()
        total_perdidos = df_filtrado['Perdidos'].sum()
        media_taxa = df_filtrado['Taxa_Num'].mean()
        
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Processados</div><div class="card-value">{total_leads}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Média Taxa Avanço</div><div class="card-value">{media_taxa:.1f}%</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="card"><div class="card-title">Total Perdidos</div><div class="card-value">{total_perdidos}</div></div>', unsafe_allow_html=True)

        st.divider()

        # --- GRÁFICOS ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📈 Evolução da Taxa")
            # Gráfico de Barras com Rótulos
            fig_evo = px.bar(df_filtrado, x="Semana", y="Taxa_Num", color="Responsável", barmode="group", text_auto='.1f')
            fig_evo.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", yaxis_title="Taxa %")
            st.plotly_chart(fig_evo, use_container_width=True)

        with col2:
            st.markdown("### 📡 Top Fontes")
            df_fontes = df_filtrado['Top Fonte'].value_counts().reset_index()
            df_fontes.columns = ['Fonte', 'Qtd']
            fig_pie = px.pie(df_fontes, names='Fonte', values='Qtd', hole=0.5, color_discrete_sequence=px.colors.sequential.Cyan)
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        # Tabela
        st.markdown("### 📋 Registros")
        cols_show = [c for c in ['Data', 'Semana', 'Responsável', 'Total', 'Taxa', 'Top Fonte'] if c in df_filtrado.columns]
        st.dataframe(df_filtrado[cols_show], use_container_width=True, hide_index=True)
        
    else:
        st.warning("⚠️ Nenhum registro encontrado para os filtros selecionados.")

else:
    st.info(f"📂 A base **{marca_sel}** parece vazia ou não foi possível ler os cabeçalhos. Verifique se salvou dados na Home.")
