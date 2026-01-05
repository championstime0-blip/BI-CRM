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
st.set_page_config(page_title="Histórico | Time Machine", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (CÓPIA EXATA DA HOME)
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
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px; display: flex; align-items: center;
}
.sub-icon { margin-right: 12px; font-size: 24px; color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.6); }
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.profile-group { display: flex; flex-direction: column; }
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); transition: all 0.3s ease; height: 100%;
}
.card:hover { box-shadow: 0 0 25px rgba(56,189,248,0.2); border-color: #38bdf8; transform: translateY(-2px); }
.card-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; min-height: 30px; display: flex; align-items: center; justify-content: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
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
        if not creds_json: 
             creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
             return gspread.authorize(creds)
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

# =========================
# UTILS VISUAIS
# =========================
def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def processar_snapshot(df):
    def status(row):
        etapa_lower = str(row["Etapa"]).lower() if "Etapa" in row else ""
        motivo = str(row["Motivo de Perda"]).strip().lower() if "Motivo de Perda" in row else ""
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        if motivo not in ["", "nan", "none", "-", "nan", "0", "nada", "n/a"]: return "Perdido"
        return "Em Andamento"
    
    if "Status" not in df.columns:
        df["Status"] = df.apply(status, axis=1)
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors='coerce')
    return df

# =========================
# RENDERIZADOR COMPLETO
# =========================
def render_dashboard_completo(df):
    # Header de Perfil
    resp = df["Responsável"].mode()[0] if "Responsável" in df.columns and not df["Responsável"].empty else "N/A"
    equipe = f"Expansão {df['marca_ref'].iloc[0]}" if 'marca_ref' in df.columns else "N/A"

    st.markdown(f"""
    <div class="profile-header">
        <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp}</span></div>
        <div class="profile-divider"></div>
        <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe}</span></div>
    </div>""", unsafe_allow_html=True)
    
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    c1, c2 = st.columns(2)
    with c1: card("Leads Totais (Snapshot)", total)
    with c2: card("Leads em Andamento", len(em_andamento))
    st.divider()

    col_mkt, col_funil = st.columns(2)
    
    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2'])
            fig_pie.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL (ACUMULADO)")
        
        # LÓGICA ACUMULATIVA IDENTICA À HOME
        etapas_invertidas = ["faturado", "em aprovação", "negociação", "Reunião Realizada", "Reunião Agendada", "Qualificado", "Confirmou Interesse"]
        funil_labels = ["TOTAL DE LEADS"]
        funil_values = [total]
        
        for etapa in etapas_invertidas:
            # Soma quem está na etapa ou nas etapas seguintes (mais avançadas)
            qtd = len(df[df["Etapa"].isin(etapas_invertidas[:etapas_invertidas.index(etapa)+1])])
            funil_labels.append(etapa.upper())
            funil_values.append(qtd)

        df_plot = pd.DataFrame({"Etapa": funil_labels, "Quantidade": funil_values})
        df_plot["Percentual"] = (df_plot["Quantidade"] / total * 100).round(1)
        df_plot["Label"] = df_plot.apply(lambda x: f"{int(x['Quantidade'])}<br>{x['Percentual']}%", axis=1)

        # Gráfico de Palos Verticais
        fig_funil = px.bar(df_plot, x="Etapa", y="Quantidade", text="Label", color="Quantidade", color_continuous_scale="Blues")
        fig_funil.update_traces(textposition='outside')
        fig_funil.update_layout(
            template="plotly_dark", showlegend=False, 
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis={'categoryorder':'array', 'categoryarray':funil_labels}
        )
        st.plotly_chart(fig_funil, use_container_width=True)
        
        # CARDS EMBAIXO DO FUNIL (CONFORME SOLICITADO)
        c_fun1, c_fun2 = st.columns(2)
        reuniao_realizada_plus = len(df[df["Etapa"].isin(["Reunião Realizada", "negociação", "em aprovação", "faturado"])])
        aguardando_andamento = len(df[(df["Etapa"] == "Aguardando Resposta") & (df["Status"] == "Em Andamento")])
        
        with c_fun1: card("Reunião Realizada (+)", reuniao_realizada_plus)
        with c_fun2: card("Aguardando Resposta (Ativos)", aguardando_andamento)

    st.divider()
    subheader_futurista("🚫", "DETALHE DAS PERDAS (MOTIVOS)")
    if not perdidos.empty:
        perdas_validas = perdidos[~perdidos["Motivo de Perda"].isin(["", "nan", "N/A", "None"])]
        df_loss = perdas_validas["Motivo de Perda"].value_counts().reset_index().head(15)
        df_loss.columns = ["Motivo", "Qtd"]
        fig_loss = px.bar(df_loss, x="Qtd", y="Motivo", orientation="h", color="Qtd", color_continuous_scale="Reds")
        fig_loss.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_loss, use_container_width=True)

# =========================
# APP MAIN (TIME MACHINE)
# =========================
st.markdown('<div class="futuristic-title">🕰️ Máquina do Tempo</div>', unsafe_allow_html=True)

with st.spinner("Sincronizando com o banco de dados..."):
    client = conectar_google()
    df_db = pd.DataFrame()
    if client:
        try:
            sh = client.open("BI_Historico")
            ws = sh.worksheet("db_snapshots")
            dados = ws.get_all_values()
            if len(dados) > 1:
                df_db = pd.DataFrame(dados[1:], columns=dados[0])
            else:
                st.warning("Banco de dados vazio.")
                st.stop()
        except Exception as e:
            st.error(f"Erro de conexão: {e}")
            st.stop()

if not df_db.empty:
    st.sidebar.header("🗂️ Filtros de Busca")
    df_db['data_dt'] = pd.to_datetime(df_db['data_salvamento'], dayfirst=True, errors='coerce')
    df_db['Ano_Filtro'] = df_db['data_dt'].dt.year.fillna(0).astype(int)
    meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
    df_db['Mes_Filtro'] = df_db['data_dt'].dt.month.map(meses_pt)
    
    marcas_disp = sorted(df_db['marca_ref'].unique())
    f_marca = st.sidebar.selectbox("1. Marca", marcas_disp)
    df_f1 = df_db[df_db['marca_ref'] == f_marca]
    
    anos_disp = sorted(df_f1['Ano_Filtro'].unique(), reverse=True)
    f_ano = st.sidebar.selectbox("2. Ano", anos_disp) if anos_disp else 0
    df_f2 = df_f1[df_f1['Ano_Filtro'] == f_ano] if f_ano else df_f1

    meses_disp = df_f2['Mes_Filtro'].unique()
    f_mes = st.sidebar.selectbox("3. Mês", meses_disp) if len(meses_disp) > 0 else ""
    df_f3 = df_f2[df_f2['Mes_Filtro'] == f_mes] if f_mes else df_f2

    if not df_f3.empty:
        df_f3['Label_Select'] = df_f3['semana_ref'] + " | " + df_f3['data_salvamento']
        opcoes = df_f3[['snapshot_id', 'Label_Select']].drop_duplicates().sort_values('snapshot_id', ascending=False)
        f_arquivo = st.sidebar.selectbox("4. Arquivo (Snapshot)", opcoes['Label_Select'])
        
        if f_arquivo:
            id_snap = opcoes[opcoes['Label_Select'] == f_arquivo]['snapshot_id'].values[0]
            df_recuperado = df_db[df_db['snapshot_id'] == id_snap].copy()
            df_final = processar_snapshot(df_recuperado)
            render_dashboard_completo(df_final)
