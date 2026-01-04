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
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

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

.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }

.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); height: 100%;
}
.card-title { font-family: 'Rajdhani', sans-serif; font-size: 14px; color: #94a3b8; text-transform: uppercase; }
.card-value { font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }

.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px; display: flex; align-items: center;
}
.sub-icon { margin-right: 12px; font-size: 24px; color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.6); }
.funnel-card { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border-top: 2px solid #22d3ee; border-radius: 0 0 12px 12px; padding: 15px; text-align: center; }
.funnel-percent { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #22d3ee; margin: 5px 0; }
.top-item { border-left: 3px solid #22d3ee; padding: 12px 15px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: space-between; background: rgba(34, 211, 238, 0.05); }
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
ETAPAS_FUNIL = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
SEMANAS = ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"]

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    # Remove colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Mapeamento robusto de colunas
    cols_map = {}
    for c in df.columns:
        c_clean = str(c).strip()
        c_low = c_clean.lower()
        
        if any(x in c_low for x in ["fonte", "origem", "source", "conversion origin"]): cols_map[c] = "Fonte"
        elif any(x in c_low for x in ["data de cri", "data da cri", "created date"]): cols_map[c] = "Data de Criação"
        elif any(x in c_low for x in ["dono", "respons", "owner"]): cols_map[c] = "Responsável"
        # MAPEAMENTO ESPECÍFICO PARA A COLUNA COM ERRO DE ENCODING
        elif "equipes do respons" in c_low or "equipe" in c_low: cols_map[c] = "Equipe"
        elif c_low == "etapa": cols_map[c] = "Etapa"
        elif "motivo" in c_low: cols_map[c] = "Motivo de Perda"
    
    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Limpeza de valores
    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str).fillna("")
    if "Equipe" in df.columns:
        df["Equipe"] = df["Equipe"].astype(str).str.strip()

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status_func(row):
        etapa = str(row["Etapa"]).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0"]: return "Perdido"
        return "Em Andamento"
        
    df["Status"] = df.apply(status_func, axis=1)
    return df

# =========================
# DASHBOARD
# =========================
def dashboard(df):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    mask_sr = (df["Etapa"].astype(str).str.contains("Aguardando Resposta", case=False, na=False)) & \
              (df["Motivo de Perda"].astype(str).str.contains("sem resposta", case=False, na=False))
    perda_sr = df[mask_sr]

    # KPIs
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="card"><div class="card-title">Leads em Andamento</div><div class="card-value">{len(em_andamento)}</div></div>', unsafe_allow_html=True)

    st.divider()

    col_mkt, col_funil = st.columns(2)
    with col_mkt:
        st.markdown('<div class="futuristic-sub"><span class="sub-icon">📡</span>MARKETING & FONTES</div>', unsafe_allow_html=True)
        df_f = df["Fonte"].value_counts().reset_index()
        df_f.columns = ["Fonte", "Qtd"]
        fig_pie = px.pie(df_f, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2', '#164e63'])
        fig_pie.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)
        
        for i, row in df_f.head(3).iterrows():
            st.markdown(f'<div class="top-item"><span>#{i+1} {row["Fonte"]}</span><b>{row["Qtd"]}</b></div>', unsafe_allow_html=True)

    with col_funil:
        st.markdown('<div class="futuristic-sub"><span class="sub-icon">📉</span>DESCIDA DE FUNIL</div>', unsafe_allow_html=True)
        df_fn = df.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
        df_fn["Pct"] = (df_fn["Qtd"] / total * 100).round(1)
        fig_fn = px.bar(df_fn, x="Qtd", y="Etapa", orientation="h", text=df_fn["Pct"].astype(str) + "%", color="Qtd", color_continuous_scale="Blues")
        fig_fn.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_fn, use_container_width=True)
        
        et_ok = ["Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
        qtd_ok = len(df[df['Etapa'].isin(et_ok)])
        tx = (qtd_ok / (total - len(perda_sr)) * 100) if (total - len(perda_sr)) > 0 else 0
        st.markdown(f'<div class="funnel-card"><div style="color:#94a3b8; font-size:14px; text-transform:uppercase;">Taxa de Avanço Real</div><div class="funnel-percent">{tx:.1f}%</div></div>', unsafe_allow_html=True)

    st.divider()
    st.markdown('<div class="futuristic-sub"><span class="sub-icon">🚫</span>DETALHE DAS PERDAS</div>', unsafe_allow_html=True)
    l1, l2 = st.columns(2)
    with l1: st.markdown(f'<div class="card"><div class="card-title">Perdidos (Total)</div><div class="card-value">{len(perdidos)}</div></div>', unsafe_allow_html=True)
    with l2: st.markdown(f'<div class="card"><div class="card-title">Sem Resposta</div><div class="card-value">{len(perda_sr)}</div></div>', unsafe_allow_html=True)

    df_ls = perdidos.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
    fig_ls = px.bar(df_ls, x="Etapa", y="Qtd", color="Qtd", color_continuous_scale="Purples", text_auto=True)
    fig_ls.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_ls, use_container_width=True)
    
    return {"total": total, "and": len(em_andamento), "perd": len(perdidos), "sr": len(perda_sr), "tx": tx, "top": df_f.iloc[0]['Fonte'] if not df_f.empty else "N/A"}

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.sidebar.selectbox("Selecione a Marca", MARCAS)
semana_ref = st.sidebar.selectbox("Semana de Referência", SEMANAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(load_csv(arquivo))
        
        # IDENTIFICAÇÃO DOS CARDS SUPERIORES
        resp_v = df["Responsável"].mode()[0] if "Responsável" in df.columns and not df["Responsável"].empty else "N/A"
        equipe_v = df["Equipe"].mode()[0] if "Equipe" in df.columns and not df["Equipe"].empty else "Não Definida"
        
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_v}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_v}</span></div>
        </div>
        """, unsafe_allow_html=True)

        kpis = dashboard(df)

        if st.sidebar.button(f"💾 SALVAR DADOS: {semana_ref}"):
            with st.spinner("Salvando..."):
                try:
                    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get("CREDENCIAIS_GOOGLE")), scope)
                    client = gspread.authorize(creds)
                    sh = client.open("BI_Historico")
                    try: ws = sh.worksheet(marca)
                    except:
                        ws = sh.add_worksheet(title=marca, rows="1000", cols="20")
                        ws.append_row(["Data", "Hora", "Semana", "Responsável", "Equipe", "Total", "Andamento", "Perdidos", "Sem Resposta", "Taxa", "Top Fonte"])
                    
                    agora = datetime.now()
                    ws.append_row([agora.strftime('%d/%m/%Y'), agora.strftime('%H:%M:%S'), semana_ref, resp_v, equipe_v, kpis['total'], kpis['and'], kpis['perd'], kpis['sr'], f"{kpis['tx']:.1f}%", kpis['top']])
                    st.sidebar.success("✅ Salvo!")
                    st.balloons()
                except Exception as e: st.sidebar.error(f"Erro: {e}")

    except Exception as e:
        st.error("Erro no processamento do arquivo")
        st.exception(e)
