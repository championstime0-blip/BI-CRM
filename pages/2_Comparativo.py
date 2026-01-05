import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Comparativo | Battle Mode", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (ADAPTADA PARA COMPARATIVO)
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

.comp-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    padding: 20px; border-radius: 12px; border: 1px solid #334155; text-align: center;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 10px;
}
.comp-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px;
}
.comp-value {
    font-family: 'Orbitron', sans-serif; font-size: 28px; font-weight: 700; color: #f8fafc; margin: 5px 0;
}
.comp-delta-pos { color: #4ade80; font-family: 'Rajdhani', font-weight: bold; font-size: 16px; }
.comp-delta-neg { color: #f87171; font-family: 'Rajdhani', font-weight: bold; font-size: 16px; }
.comp-delta-neutral { color: #94a3b8; font-family: 'Rajdhani', font-weight: bold; font-size: 16px; }

.vs-badge {
    background-color: #334155; color: #22d3ee; padding: 5px 15px; border-radius: 20px;
    font-family: 'Orbitron'; font-weight: bold; font-size: 12px; margin: 0 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO E UTILS
# =========================
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        if not creds_json: 
             creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
             return gspread.authorize(creds)
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except:
        return None

def processar_df(df):
    def status(row):
        etapa = str(row.get("Etapa", "")).lower()
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        if motivo not in ["", "nan", "none", "-", "nan", "0", "nada", "n/a"]: return "Perdido"
        return "Em Andamento"
    
    if "Status" not in df.columns:
        df["Status"] = df.apply(status, axis=1)
    
    # Tratamento de Fonte
    if "Fonte" in df.columns:
        df["Fonte"] = df["Fonte"].fillna("N/A").astype(str)
        
    return df

# Função para Card com Delta
def card_comparativo(titulo, valor_a, valor_b, formato="num"):
    delta = valor_a - valor_b
    if valor_b > 0:
        pct = (delta / valor_b) * 100
    else:
        pct = 0 if delta == 0 else 100

    sinal = "+" if delta > 0 else ""
    classe = "comp-delta-pos" if delta > 0 else ("comp-delta-neg" if delta < 0 else "comp-delta-neutral")
    icone = "▲" if delta > 0 else ("▼" if delta < 0 else "=")
    
    if formato == "pct":
        val_str = f"{valor_a:.1f}%"
        delta_str = f"{icone} {delta:.1f} p.p."
    else:
        val_str = f"{int(valor_a)}"
        delta_str = f"{icone} {int(delta)} ({sinal}{pct:.1f}%)"

    st.markdown(f"""
    <div class="comp-card">
        <div class="comp-title">{titulo}</div>
        <div class="comp-value">{val_str}</div>
        <div class="{classe}">{delta_str}</div>
    </div>
    """, unsafe_allow_html=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">⚔️ Arena Comparativa</div>', unsafe_allow_html=True)

# 1. Carregar Dados
with st.spinner("Carregando Dados..."):
    client = conectar_google()
    df_db = pd.DataFrame()
    if client:
        try:
            sh = client.open("BI_Historico")
            ws = sh.worksheet("db_snapshots")
            dados = ws.get_all_values()
            if len(dados) > 1:
                df_db = pd.DataFrame(dados[1:], columns=dados[0])
        except: pass

if df_db.empty:
    st.warning("Sem dados para comparar. Salve arquivos na Home primeiro.")
    st.stop()

# 2. Configurar Filtros
df_db['Label'] = df_db['semana_ref'] + " | " + df_db['marca_ref'] + " (" + df_db['data_salvamento'] + ")"
opcoes = df_db[['snapshot_id', 'Label']].drop_duplicates().sort_values('snapshot_id', ascending=False)
lista_opcoes = opcoes['Label'].tolist()

# Layout de Seleção
st.sidebar.header("🎛️ Configuração do Duelo")
sel_a = st.sidebar.selectbox("Periodo A (Principal)", lista_opcoes, index=0)
sel_b = st.sidebar.selectbox("Periodo B (Referência)", lista_opcoes, index=1 if len(lista_opcoes) > 1 else 0)

if sel_a and sel_b:
    id_a = opcoes[opcoes['Label'] == sel_a]['snapshot_id'].values[0]
    id_b = opcoes[opcoes['Label'] == sel_b]['snapshot_id'].values[0]

    # Filtrar Dataframes
    df_a = processar_df(df_db[df_db['snapshot_id'] == id_a].copy())
    df_b = processar_df(df_db[df_db['snapshot_id'] == id_b].copy())

    st.divider()
    
    # Header do Duelo
    col_h1, col_h2, col_h3 = st.columns([1, 0.2, 1])
    with col_h1: 
        st.markdown(f"<h3 style='text-align:right; color:#22d3ee'>{sel_a}</h3>", unsafe_allow_html=True)
    with col_h2:
        st.markdown("<h3 style='text-align:center; color:#e0e0e0'>VS</h3>", unsafe_allow_html=True)
    with col_h3:
        st.markdown(f"<h3 style='text-align:left; color:#94a3b8'>{sel_b}</h3>", unsafe_allow_html=True)

    st.write("")

    # --- 1. CARDS DE KPI ---
    # Calculos
    total_a, total_b = len(df_a), len(df_b)
    
    andamento_a = len(df_a[df_a['Status'] == 'Em Andamento'])
    andamento_b = len(df_b[df_b['Status'] == 'Em Andamento'])
    
    perdidos_a = len(df_a[df_a['Status'] == 'Perdido'])
    perdidos_b = len(df_b[df_b['Status'] == 'Perdido'])
    
    # Conversão (Estimada)
    # Consideramos "Venda/Ganho" qualquer coisa que não seja "Perdido" ou "Em Andamento" se existir status explicito
    # Ou usamos uma lógica de funil. Vamos usar a quantidade de leads qualificados/faturados
    vendas_a = len(df_a[df_a['Status'] == 'Ganho'])
    vendas_b = len(df_b[df_b['Status'] == 'Ganho'])
    
    # Render Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1: card_comparativo("Total Leads", total_a, total_b)
    with c2: card_comparativo("Em Andamento", andamento_a, andamento_b)
    with c3: card_comparativo("Perdidos", perdidos_a, perdidos_b)
    with c4: card_comparativo("Vendas/Ganhos", vendas_a, vendas_b)
    
    st.divider()

    # --- 2. GRÁFICO COMPARATIVO DE FUNIL ---
    st.subheader("📊 Comparativo de Funil")
    
    # Agrupar Dados
    ETAPAS = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
    
    funil_a = df_a.groupby("Etapa").size().reindex(ETAPAS).fillna(0).reset_index(name="Qtd_A")
    funil_b = df_b.groupby("Etapa").size().reindex(ETAPAS).fillna(0).reset_index(name="Qtd_B")
    
    df_funil_comp = pd.merge(funil_a, funil_b, on="Etapa")
    
    # Plotly Graph Objects para Barras Agrupadas
    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_funil_comp['Etapa'], x=df_funil_comp['Qtd_A'],
        name='Atual', orientation='h', marker_color='#22d3ee'
    ))
    fig.add_trace(go.Bar(
        y=df_funil_comp['Etapa'], x=df_funil_comp['Qtd_B'],
        name='Anterior', orientation='h', marker_color='#475569'
    ))
    
    fig.update_layout(
        barmode='group', 
        template="plotly_dark", 
        paper_bgcolor="rgba(0,0,0,0)", 
        plot_bgcolor="rgba(0,0,0,0)",
        height=500,
        legend=dict(orientation="h", y=1.1)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 3. COMPARATIVO DE FONTES ---
    st.subheader("📡 Variação de Fontes")
    
    top_fontes = df_a['Fonte'].value_counts().head(5).index.tolist()
    
    # Filtrar apenas top 5 fontes do período atual para não poluir
    df_fonte_a = df_a[df_a['Fonte'].isin(top_fontes)].groupby('Fonte').size().reset_index(name='Qtd_A')
    df_fonte_b = df_b[df_b['Fonte'].isin(top_fontes)].groupby('Fonte').size().reset_index(name='Qtd_B')
    
    df_fonte_comp = pd.merge(df_fonte_a, df_fonte_b, on="Fonte", how='outer').fillna(0)
    
    col_gf1, col_gf2 = st.columns(2)
    
    with col_gf1:
        fig_f = go.Figure()
        fig_f.add_trace(go.Bar(
            x=df_fonte_comp['Fonte'], y=df_fonte_comp['Qtd_A'],
            name='Atual', marker_color='#818cf8'
        ))
        fig_f.add_trace(go.Bar(
            x=df_fonte_comp['Fonte'], y=df_fonte_comp['Qtd_B'],
            name='Anterior', marker_color='#475569'
        ))
        fig_f.update_layout(barmode='group', template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_f, use_container_width=True)
        
    with col_gf2:
        # Tabela de Delta
        df_fonte_comp['Delta'] = df_fonte_comp['Qtd_A'] - df_fonte_comp['Qtd_B']
        df_fonte_comp['Status'] = df_fonte_comp['Delta'].apply(lambda x: "🟢 Cresceu" if x > 0 else ("🔴 Caiu" if x < 0 else "🟡 Igual"))
        st.dataframe(df_fonte_comp[['Fonte', 'Qtd_A', 'Qtd_B', 'Delta', 'Status']], use_container_width=True, hide_index=True)
