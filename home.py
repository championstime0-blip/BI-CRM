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
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (COMPLETA)
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
.top-item {
    border-left: 3px solid #22d3ee; padding: 12px 15px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: space-between;
    transition: transform 0.2s; border: 1px solid rgba(34, 211, 238, 0.1); border-left-width: 3px; background: rgba(30, 41, 59, 0.5);
}
.top-rank { font-family: 'Orbitron', sans-serif; font-weight: 900; color: #22d3ee; font-size: 16px; margin-right: 12px; }
.top-name { font-family: 'Rajdhani', sans-serif; color: #f1f5f9; font-weight: 600; font-size: 14px; flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.top-val-abs { font-family: 'Orbitron', sans-serif; color: #fff; font-weight: bold; font-size: 14px; margin-left: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES & CONEXÃO
# =========================
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]

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

def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    if raw.strip().startswith("sep="):
        raw = "\n".join(raw.splitlines()[1:])
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
        elif "equipes do respons" in c_lower or "equipe" in c_lower: cols_map[c] = "Equipe"
        elif "motivo de perda" in c_lower: cols_map[c] = "Motivo de Perda"
        elif "etapa" in c_lower: cols_map[c] = "Etapa"
        elif "campanha" in c_lower: cols_map[c] = "Campanha"

    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()]

    colunas_texto = ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte", "Campanha"]
    for col in colunas_texto:
        if col in df.columns:
            if isinstance(df[col], pd.DataFrame): df[col] = df[col].iloc[:, 0]
            df[col] = df[col].astype(str).str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável").fillna("N/A").str.strip()
        else:
            df[col] = "N/A"

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status_func(row):
        etapa_lower = str(row["Etapa"]).lower()
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status_func, axis=1)
    return df

# =========================
# DASHBOARD LOGIC
# =========================
def render_dashboard(df, marca):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    c1, c2 = st.columns(2)
    with c1: card("Leads Totais", total)
    with c2: card("Leads em Andamento", len(em_andamento))
    st.divider()

    col_mkt, col_funil = st.columns(2)
    
    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            
            # Gráfico de Pizza com Nome e Número
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, 
                             color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2', '#1e293b'])
            fig_pie.update_traces(textposition='inside', textinfo='label+value')
            fig_pie.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)

        # SEÇÃO TOP CAMPANHAS
        if "Campanha" in df.columns:
            st.markdown('<div class="futuristic-sub" style="font-size:18px; margin-top:20px; border:none;"><span class="sub-icon">🚀</span>TOP 3 CAMPANHAS</div>', unsafe_allow_html=True)
            df_camp = df[df["Campanha"] != "N/A"]["Campanha"].value_counts().reset_index()
            df_camp.columns = ["Campanha", "Qtd"]
            top3_c = df_camp.head(3)
            
            if not top3_c.empty:
                for i, row in top3_c.iterrows():
                    st.markdown(f"""
                    <div class="top-item">
                        <span class="top-rank">#{i+1}</span>
                        <span class="top-name">{row['Campanha']}</span>
                        <span class="top-val-abs">{row['Qtd']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Nenhuma campanha identificada.")

    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL (ACUMULADO)")
        ordem_funil = ["Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "negociação", "em aprovação", "faturado"]
        funil_labels = ["TOTAL DE LEADS"]
        funil_values = [total]
        
        for etapa in ordem_funil:
            idx = ordem_funil.index(etapa)
            etapas_alvo = ordem_funil[idx:]
            qtd = len(df[df["Etapa"].isin(etapas_alvo)])
            funil_labels.append(etapa.upper())
            funil_values.append(qtd)

        df_plot = pd.DataFrame({"Etapa": funil_labels, "Quantidade": funil_values})
        df_plot["Percentual"] = (df_plot["Quantidade"] / total * 100).round(1) if total > 0 else 0
        df_plot["Label"] = df_plot.apply(lambda x: f"{int(x['Quantidade'])} ({x['Percentual']}%)", axis=1)

        fig_funil = px.bar(df_plot, y="Etapa", x="Quantidade", text="Label", orientation="h",
                          color="Quantidade", color_continuous_scale="Blues")
        fig_funil.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
                                yaxis={'categoryorder':'array', 'categoryarray':funil_labels[::-1]})
        st.plotly_chart(fig_funil, use_container_width=True)
        
        c_fun1, c_fun2 = st.columns(2)
        reuniao_realizada_plus = len(df[df["Etapa"].isin(["Reunião Realizada", "negociação", "em aprovação", "faturado"])])
        leads_sem_contato_count = len(perdidos[(perdidos["Etapa"].str.contains("Aguardando Resposta", na=False)) & 
                                        (perdidos["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))])
        
        with c_fun1: card("Reunião Realizada (+)", reuniao_realizada_plus)
        with c_fun2: card("Leads sem contato", leads_sem_contato_count)

    st.divider()
    subheader_futurista("🚫", "DETALHE DAS PERDAS (MOTIVOS)")
    if not perdidos.empty:
        perdas_validas = perdidos[~perdidos["Motivo de Perda"].isin(["", "nan", "N/A", "None"])]
        df_loss = perdas_validas["Motivo de Perda"].value_counts().reset_index()
        df_loss.columns = ["Motivo", "Qtd"]
        df_loss = df_loss.sort_values(by="Qtd", ascending=False).head(15)
        df_loss['color'] = df_loss['Motivo'].apply(lambda x: '#4ade80' if 'sem resposta' in str(x).lower() else '#ef4444')
        fig_loss = px.bar(df_loss, x="Qtd", y="Motivo", text="Qtd", orientation="h",
                          color="Motivo", color_discrete_map=dict(zip(df_loss['Motivo'], df_loss['color'])))
        fig_loss.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)", yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_loss, use_container_width=True)
        k1, k2 = st.columns(2)
        with k1: card("Total Perdido", len(perdidos))
        with k2: card("Leads sem contato", leads_sem_contato_count)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

st.sidebar.header("Painel de Carga")
marca_sel = st.sidebar.selectbox("Marca", MARCAS)
semana_sel = st.sidebar.selectbox("Semana Ref.", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"])
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = load_csv(arquivo)
        df = processar(df)
        resp = df["Responsável"].mode()[0] if not df["Responsável"].empty else "N/A"
        equipe = f"Expansão {marca_sel}"
        
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe}</span></div>
        </div>""", unsafe_allow_html=True)
        
        render_dashboard(df, marca_sel)
        
        if st.sidebar.button(f"🚀 SALVAR HISTÓRICO: {semana_sel}"):
            client = conectar_google()
            if client:
                sh = client.open("BI_Historico")
                try: ws = sh.worksheet("db_snapshots")
                except: ws = sh.add_worksheet(title="db_snapshots", rows="1000", cols="20")
                df_save = df.copy()
                df_save['snapshot_id'] = datetime.now().strftime("%Y%m%d_%H%M%S")
                df_save['data_salvamento'] = datetime.now().strftime('%d/%m/%Y %H:%M')
                df_save['semana_ref'] = semana_sel
                df_save['marca_ref'] = marca_sel
                ws.append_rows(df_save.astype(str).values.tolist())
                st.sidebar.success("Snapshot salvo!")
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
