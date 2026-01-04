import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

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
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.card {
    background: linear-gradient(135deg, #111827, #020617); padding: 24px; border-radius: 16px;
    border: 1px solid #1e293b; text-align: center; height: 100%;
}
.card-title { font-family: 'Rajdhani', sans-serif; font-size: 14px; color: #94a3b8; text-transform: uppercase; }
.card-value { font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; color: #22d3ee; }

.funnel-card { background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border-top: 2px solid #22d3ee; border-radius: 0 0 12px 12px; padding: 15px; text-align: center; }
.top-item { border-left: 3px solid #22d3ee; padding: 12px 15px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: space-between; background: rgba(34, 211, 238, 0.05); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE PROCESSAMENTO (DEDUPLICADO)
# ==========================================
def processar(df):
    # Remove colunas duplicadas pelo nome (Vacina contra Erro 1-Dimensional)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    df.columns = df.columns.astype(str).str.strip()
    cols_map = {}
    for c in df.columns:
        c_low = c.lower()
        if any(x in c_low for x in ["fonte", "origem", "source", "conversion origin"]): cols_map[c] = "Fonte"
        elif any(x in c_low for x in ["data de cri", "data da cri", "created date"]): cols_map[c] = "Data de Criação"
        elif any(x in c_low for x in ["dono", "respons", "owner"]): cols_map[c] = "Responsável"
        elif any(x in c_low for x in ["equipe", "team"]): cols_map[c] = "Equipe"
        elif c_low == "etapa": cols_map[c] = "Etapa"
        elif "motivo" in c_low: cols_map[c] = "Motivo de Perda"
    
    df = df.rename(columns=cols_map)
    df = df.loc[:, ~df.columns.duplicated()].copy()

    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", pd.Series([""]*len(df))).astype(str).fillna("")
    
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status_lead(row):
        etapa = str(row["Etapa"]).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row["Motivo de Perda"]).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0"]: return "Perdido"
        return "Em Andamento"
    
    df["Status"] = df.apply(status_lead, axis=1)
    return df

# ==========================================
# 3. INTERFACE E DASHBOARD
# ==========================================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
SEMANAS = ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"]

marca = st.sidebar.selectbox("Selecione a Marca", MARCAS)
semana_sel = st.sidebar.selectbox("Semana de Referência", SEMANAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        content = arquivo.read().decode("latin-1", errors="ignore")
        sep = ";" if content.count(";") > content.count(",") else ","
        arquivo.seek(0)
        df_raw = pd.read_csv(arquivo, sep=sep, engine="python")
        df = processar(df_raw)

        # Identificação
        resp = df["Responsável"].mode()[0] if "Responsável" in df.columns and not df["Responsável"].empty else "N/A"
        equipe = df["Equipe"].mode()[0] if "Equipe" in df.columns and not df["Equipe"].empty else "Geral"
        st.markdown(f'<div class="profile-header"><div><b>Responsável:</b> {resp}</div><div><b>Equipe:</b> {equipe}</div></div>', unsafe_allow_html=True)

        # KPIs
        total = len(df)
        em_andamento = df[df["Status"] == "Em Andamento"]
        perdidos = df[df["Status"] == "Perdido"]
        
        mask_sem_resp = (df["Etapa"].astype(str).str.contains("Aguardando Resposta", case=False, na=False)) & \
                        (df["Motivo de Perda"].astype(str).str.contains("sem resposta", case=False, na=False))
        qtd_sem_resp = len(df[mask_sem_resp])

        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Em Andamento</div><div class="card-value">{len(em_andamento)}</div></div>', unsafe_allow_html=True)

        # Gráficos
        st.divider()
        col_mkt, col_funil = st.columns(2)

        with col_mkt:
            st.markdown('<div class="futuristic-sub"><span class="sub-icon">📡</span>MARKETING & FONTES</div>', unsafe_allow_html=True)
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            neon_palette = ['#22d3ee', '#06b6d4', '#0891b2', '#164e63', '#67e8f9']
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=neon_palette)
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            top3 = df_fonte.head(3)
            for i, row in top3.iterrows():
                st.markdown(f'<div class="top-item"><span>#{i+1} {row["Fonte"]}</span><b>{row["Qtd"]}</b></div>', unsafe_allow_html=True)

        with col_funil:
            st.markdown('<div class="futuristic-sub"><span class="sub-icon">📉</span>DESCIDA DE FUNIL</div>', unsafe_allow_html=True)
            etapas_ordem = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
            df_funil = df.groupby("Etapa").size().reindex(etapas_ordem).fillna(0).reset_index(name="Qtd")
            fig_funil = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h", color="Qtd", color_continuous_scale="Blues")
            fig_funil.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_funil, use_container_width=True)
            
            etapas_avanco = ["Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
            qtd_ok = len(df[df['Etapa'].isin(etapas_avanco)])
            base_real = total - qtd_sem_resp
            taxa = (qtd_ok / base_real * 100) if base_real > 0 else 0
            st.markdown(f'<div class="funnel-card"><div style="color:#94a3b8">TAXA DE AVANÇO REAL</div><div class="card-value" style="font-size:42px;">{taxa:.1f}%</div></div>', unsafe_allow_html=True)

        # SALVAMENTO
        st.sidebar.markdown("---")
        if st.sidebar.button(f"💾 SALVAR DADOS: {semana_sel}"):
            with st.spinner("Salvando no Google Sheets..."):
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
                    ws.append_row([agora.strftime('%d/%m/%Y'), agora.strftime('%H:%M:%S'), semana_sel, resp, equipe, total, len(em_andamento), len(perdidos), qtd_sem_resp, f"{taxa:.1f}%", df_fonte.iloc[0]['Fonte'] if not df_fonte.empty else "N/A"])
                    st.sidebar.success("✅ Salvo com Sucesso!")
                    st.balloons()
                except Exception as e: st.sidebar.error(f"Erro: {e}")

    except Exception as e: st.error(f"Erro no processamento: {e}")
