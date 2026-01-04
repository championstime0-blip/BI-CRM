import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
# ESTILIZAÇÃO CSS FUTURISTA
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
    margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between;
}
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }

.card {
    background: linear-gradient(135deg, #111827, #020617); padding: 24px; border-radius: 16px;
    border: 1px solid #1e293b; text-align: center; box-shadow: 0 0 15px rgba(56,189,248,0.05);
}
.card-title { font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
.card-value { font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; color: #22d3ee; }

.date-card { background: rgba(15, 23, 42, 0.4); border: 1px solid #334155; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 30px; }
.funnel-card { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border-top: 2px solid #22d3ee; padding: 15px; text-align: center; border-radius: 0 0 12px 12px; }

.top-item { border-left: 3px solid #22d3ee; padding: 12px 15px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: space-between; background: rgba(34, 211, 238, 0.05); }
</style>
""", unsafe_allow_html=True)

# =========================
# FUNÇÕES DE APOIO
# =========================
def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def kpi_card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

def processar_dados(df):
    df.columns = df.columns.str.strip()
    cols_map = {c: c for c in df.columns}
    for c in df.columns:
        c_lower = c.lower()
        if c_lower in ["fonte", "origem", "source", "origem do lead"]: cols_map[c] = "Fonte"
        if c_lower in ["data de criação", "data da criação", "created date"]: cols_map[c] = "Data de Criação"
        if c_lower in ["dono do lead", "responsável", "owner"]: cols_map[c] = "Responsável"
        if c_lower in ["equipe", "team"]: cols_map[c] = "Equipe"
    
    df = df.rename(columns=cols_map)
    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str)
    
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status_lead(row):
        etapa = row["Etapa"].lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = row["Motivo de Perda"].strip().lower()
        if motivo not in ["", "nan", "none", "-"]: return "Perdido"
        return "Em Andamento"
    
    df["Status"] = df.apply(status_lead, axis=1)
    return df

# =========================
# TÍTULO E INPUTS
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
marca = st.sidebar.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        raw_df = pd.read_csv(arquivo, sep=None, engine='python', encoding='latin-1')
        df = processar_dados(raw_df)

        # Extração de Identidade
        resp_val = df["Responsável"].mode()[0] if "Responsável" in df.columns else "N/A"
        equipe_raw = df["Equipe"].mode()[0] if "Equipe" in df.columns else "Geral"
        equipe_val = "Expansão Ensina Mais" if equipe_raw in ["Geral", "nan", ""] else equipe_raw
        
        min_date = df["Data de Criação"].min().strftime('%d/%m/%Y')
        max_date = df["Data de Criação"].max().strftime('%d/%m/%Y')

        # Header de Perfil
        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_val}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_val}</span></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f'<div class="date-card"><div class="date-label">📅 Recorte Temporal</div><div class="date-value">{min_date} ➔ {max_date}</div></div>', unsafe_allow_html=True)

        # KPIs
        total = len(df)
        em_andamento = df[df["Status"] == "Em Andamento"]
        perdidos = df[df["Status"] == "Perdido"]
        perda_especifica = df[(df["Etapa"] == "Aguardando Resposta") & (df["Motivo de Perda"].str.contains("sem resposta", case=False))]
        
        c1, c2 = st.columns(2)
        with c1: kpi_card("Leads Totais", total)
        with c2: kpi_card("Em Andamento", len(em_andamento))

        # Gráficos Linha 1
        st.divider()
        col_mkt, col_funil = st.columns(2)

        with col_mkt:
            subheader_futurista("📡", "MARKETING & FONTES")
            df_fonte = df["Fonte"].value_counts().reset_index()
            fig_pie = px.pie(df_fonte, values='count', names='Fonte', hole=0.6, color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_pie.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Top 3
            top3 = df_fonte.head(3)
            for i, r in top3.iterrows():
                st.markdown(f'<div class="top-item"><span>#{i+1} {r["Fonte"]}</span><b>{r["count"]} leads</b></div>', unsafe_allow_html=True)

        with col_funil:
            subheader_futurista("📉", "DESCIDA DE FUNIL")
            etapas_ordem = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
            df_funil = df.groupby("Etapa").size().reindex(etapas_ordem).fillna(0).reset_index(name="Qtd")
            fig_funil = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h", color="Qtd", color_continuous_scale="Blues")
            fig_funil.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_funil, use_container_width=True)
            
            # Taxa Avanço
            etapas_qualificadas = ["Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
            qtd_avanco = len(df[df["Etapa"].isin(etapas_qualificadas)])
            base_real = total - len(perda_especifica)
            perc_avanco = (qtd_avanco / base_real * 100) if base_real > 0 else 0
            st.markdown(f'<div class="funnel-card"><div class="card-title">🚀 Taxa de Avanço Real</div><div style="font-size:32px; font-weight:bold; color:#22d3ee;">{perc_avanco:.1f}%</div></div>', unsafe_allow_html=True)

        # Detalhe de Perdas
        st.divider()
        subheader_futurista("🚫", "DETALHE DAS PERDAS")
        cl1, cl2 = st.columns(2)
        with cl1: kpi_card("Perda s/ Resposta", len(perda_especifica))
        with cl2: kpi_card("Total Improdutivos", len(perdidos))

        # ==========================================
        # BOTÃO SALVAR (GOOGLE SHEETS)
        # ==========================================
        st.write("")
        if st.button("🚀 SALVAR DADOS NO GOOGLE SHEETS (HISTÓRICO)"):
            with st.spinner("Gravando na planilha BI_Historico..."):
                try:
                    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                    creds_json = os.environ.get("CREDENCIAIS_GOOGLE")
                    creds_dict = json.loads(creds_json)
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                    client = gspread.authorize(creds)
                    
                    sh = client.open("BI_Historico")
                    try:
                        ws = sh.worksheet(marca)
                    except gspread.WorksheetNotFound:
                        ws = sh.add_worksheet(title=marca, rows="100", cols="20")
                        ws.append_row(["Data Salvamento", "Semana Ref", "Recorte Temporal", "Responsável", "Equipe", "Total Leads", "Em Andamento", "Perdidos", "Perda s/ Resp", "Taxa Avanço Funil", "Top 1 Fonte"])
                    
                    dados = [
                        datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                        datetime.now().strftime('%Y-W%W'),
                        f"{min_date} a {max_date}",
                        resp_val, equipe_val, total, len(em_andamento), len(perdidos), len(perda_especifica), f"{perc_avanco:.1f}%",
                        top3.iloc[0]["Fonte"] if not top3.empty else "N/A"
                    ]
                    ws.append_row(dados)
                    st.success(f"✅ Dados de {marca} gravados com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")

    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
