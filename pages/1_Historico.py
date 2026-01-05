import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime
import io

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão - Histórico", layout="wide")

# =========================
# ESTILIZAÇÃO CSS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 56px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: 3px; margin-bottom: 10px; text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px; display: flex; align-items: center;
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
}
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
MOTIVOS_PERDA_MESTRADOS = ["Sem Resposta", "Sem Capital", "Desistiu do Negócio", "Outro Investimento", "Fora de Perfil", "Não tem interesse em franquia", "Lead Duplicado", "Dados Inválidos", "Região Indisponível", "Sócio não aprovou"]

# =========================
# CONEXÕES GOOGLE
# =========================
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except: return None

def get_historico():
    client = conectar_google()
    if not client: return pd.DataFrame()
    try:
        sh = client.open("BI_Historico")
        ws = sh.worksheet("db_snapshots")
        # CORREÇÃO: Lê valores brutos para evitar erro de cabeçalhos duplicados
        rows = ws.get_all_values()
        if not rows: return pd.DataFrame()
        # Assume que a primeira linha contém os cabeçalhos salvos pelo script
        df = pd.DataFrame(rows[1:], columns=rows[0])
        return df
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return pd.DataFrame()

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    if raw.strip().startswith("sep="): raw = "\n".join(raw.splitlines()[1:])
    sep = ";" if raw.count(";") > raw.count(",") else ","
    return pd.read_csv(io.StringIO(raw), sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    df = df.loc[:, ~df.columns.duplicated()]
    cols_map = {}
    for c in df.columns:
        c_lower = str(c).lower()
        if "fonte" in c_lower and "utm" not in c_lower: cols_map[c] = "Fonte"
        elif "data de cri" in c_lower: cols_map[c] = "Data de Criação"
        elif "respons" in c_lower and "equipe" not in c_lower: cols_map[c] = "Responsável"
        elif "motivo de perda" in c_lower: cols_map[c] = "Motivo de Perda"
        elif "etapa" in c_lower: cols_map[c] = "Etapa"
        elif "campanha" in c_lower: cols_map[c] = "Campanha"
        elif "estado" in c_lower: cols_map[c] = "Estado"

    df = df.rename(columns=cols_map)
    
    def status_func(row):
        estado_lower = str(row.get("Estado", "")).lower()
        if "perdida" in estado_lower: return "Perdido"
        etapa_lower = str(row.get("Etapa", "")).lower()
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada", "n/a", "null"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status_func, axis=1)
    return df

# =========================
# DASHBOARD RENDERING
# =========================
def render_dashboard(df):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="card"><div class="profile-label">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="profile-label">Leads em Andamento</div><div class="card-value">{len(em_andamento)}</div></div>', unsafe_allow_html=True)
    st.divider()

    col_mkt, col_funil = st.columns(2)
    with col_mkt:
        st.markdown('<div class="futuristic-sub">📡 MARKETING & FONTES</div>', unsafe_allow_html=True)
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            fig_pie = px.pie(df_fonte, values=df_fonte.columns[1], names=df_fonte.columns[0], hole=0.6, color_discrete_sequence=px.colors.sequential.Cyan_r)
            fig_pie.update_traces(textposition='inside', textinfo='label+value')
            fig_pie.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_funil:
        st.markdown('<div class="futuristic-sub">📉 FUNIL DE VENDAS</div>', unsafe_allow_html=True)
        ordem_funil = ["Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "negociação", "em aprovação", "faturado"]
        funil_values = [total]
        for etp in ordem_funil:
            qtd = len(df[df["Etapa"].str.lower().str.contains(etp.lower(), na=False)])
            funil_values.append(qtd)
        
        funil_labels = ["TOTAL"] + [e.upper() for e in ordem_funil]
        df_plot = pd.DataFrame({"Etapa": funil_labels, "Qtd": funil_values})
        fig_funil = px.bar(df_plot, y="Etapa", x="Qtd", text="Qtd", orientation="h", color="Qtd", color_continuous_scale="Blues")
        fig_funil.update_layout(template="plotly_dark", showlegend=False, yaxis={'categoryorder':'array', 'categoryarray':funil_labels[::-1]})
        st.plotly_chart(fig_funil, use_container_width=True)

    st.divider()
    st.markdown('<div class="futuristic-sub">🚫 MOTIVOS DE PERDA</div>', unsafe_allow_html=True)
    df_loss = perdidos["Motivo de Perda"].value_counts().reset_index()
    df_loss.columns = ["Motivo", "Qtd"]
    df_loss = df_loss.sort_values(by="Qtd", ascending=False)
    
    # Destaque para "Sem Resposta"
    df_loss['color'] = df_loss['Motivo'].apply(lambda x: '#10b981' if 'sem resposta' in str(x).lower() else '#334155')
    fig_loss = px.bar(df_loss, x="Qtd", y="Motivo", text="Qtd", orientation="h", color="Motivo", color_discrete_map=dict(zip(df_loss['Motivo'], df_loss['color'])))
    fig_loss.update_layout(template="plotly_dark", showlegend=False, height=500, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_loss, use_container_width=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 CRM EXPANSÃO</div>', unsafe_allow_html=True)

modo = st.sidebar.radio("Selecione o Modo", ["Snapshot Atual (Upload)", "Visão Histórica (Salvos)"])

if modo == "Snapshot Atual (Upload)":
    marca_sel = st.sidebar.selectbox("Marca", MARCAS)
    semana_sel = st.sidebar.selectbox("Semana Ref.", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"])
    arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])
    
    if arquivo:
        df = processar(load_csv(arquivo))
        render_dashboard(df)
        
        if st.sidebar.button("🚀 SALVAR NO HISTÓRICO"):
            client = conectar_google()
            if client:
                sh = client.open("BI_Historico")
                ws = sh.worksheet("db_snapshots")
                df_save = df.copy()
                df_save['snapshot_id'] = datetime.now().strftime("%Y%m%d_%H%M%S")
                df_save['data_salvamento'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                df_save['semana_ref'] = semana_sel
                df_save['marca_ref'] = marca_sel
                
                # Garante que os cabeçalhos existam se a planilha estiver vazia
                if not ws.get_all_values():
                    ws.append_row(df_save.columns.tolist())
                
                ws.append_rows(df_save.astype(str).values.tolist())
                st.sidebar.success("Snapshot salvo!")

else:
    df_hist = get_historico()
    if not df_hist.empty:
        marcas_h = df_hist['marca_ref'].unique()
        m_sel = st.sidebar.selectbox("Filtrar Marca", marcas_h)
        semanas_h = df_hist[df_hist['marca_ref'] == m_sel]['semana_ref'].unique()
        s_sel = st.sidebar.selectbox("Filtrar Semana", semanas_h)
        
        df_view = df_hist[(df_hist['marca_ref'] == m_sel) & (df_hist['semana_ref'] == s_sel)]
        st.markdown(f'<div class="profile-header"><div class="profile-group"><span class="profile-label">Semana</span><span class="profile-value">{s_sel}</span></div><div class="profile-group"><span class="profile-label">Marca</span><span class="profile-value">{m_sel}</span></div></div>', unsafe_allow_html=True)
        render_dashboard(df_view)
    else:
        st.info("Nenhum histórico encontrado na planilha 'BI_Historico'.")
