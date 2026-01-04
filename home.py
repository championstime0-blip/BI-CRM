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

# [Mantive seu CSS original aqui para não perder o visual futurista]
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 56px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; display: flex; align-items: center; justify-content: space-between;
}
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); height: 100%;
}
.card-value { font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700; color: #22d3ee; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE (CORRIGIDA)
# =========================
def conectar_google():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Tenta pegar das Variáveis de Ambiente do Render primeiro
    creds_json = os.environ.get("gcp_service_account")
    
    # Se não achar (local), tenta pegar do st.secrets
    if not creds_json:
        creds_json = st.secrets.get("gcp_service_account")
        
    if not creds_json:
        raise ValueError("Credenciais Google não encontradas no Environment ou Secrets.")
        
    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def processar(arquivo_bruto):
    # RD CRM usa Latin-1 e separador ponto e vírgula
    df = pd.read_csv(arquivo_bruto, sep=';', encoding='latin-1', on_bad_lines='skip')
    
    # Limpa colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Mapeamento manual e forçado
    cols_map = {}
    for c in df.columns:
        c_low = str(c).lower()
        if "fonte" in c_low: cols_map[c] = "Fonte"
        elif "data de cri" in c_low: cols_map[c] = "Data de Criação"
        elif "responsavel" in c_low or "responsÃ¡vel" in c_low: cols_map[c] = "Responsável"
        elif "equipe" in c_low: cols_map[c] = "Equipe"
        elif "etapa" in c_low: cols_map[c] = "Etapa"
        elif "motivo de perda" in c_low: cols_map[c] = "Motivo de Perda"
    
    df = df.rename(columns=cols_map)

    # Garante que colunas existem para não quebrar o dashboard
    for col in ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte"]:
        if col not in df.columns:
            df[col] = "N/A"
        else:
            df[col] = df[col].astype(str).str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável").fillna("N/A")

    def definir_status(row):
        etapa = str(row.get("Etapa", "")).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada"]: return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(definir_status, axis=1)
    return df

# =========================
# APP PRINCIPAL
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

st.sidebar.header("⚙️ Configurações")
marca = st.sidebar.selectbox("Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
semana_ref = st.sidebar.selectbox("Semana", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5"])

arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(arquivo)
        
        # --- EXIBIÇÃO IMEDIATA ---
        resp_v = df["Responsável"].iloc[0] if not df.empty else "N/A"
        equipe_v = df["Equipe"].iloc[0] if not df.empty else "Geral"

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_v}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_v}</span></div>
        </div>
        """, unsafe_allow_html=True)

        total = len(df)
        andamento = len(df[df["Status"] == "Em Andamento"])
        perdidos = len(df[df["Status"] == "Perdido"])

        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Andamento</div><div class="card-value">{andamento}</div></div>', unsafe_allow_html=True)

        # Gráfico de Perdas
        st.divider()
        st.markdown("### 🚫 DETALHE DAS PERDAS")
        df_p = df[df["Status"] == "Perdido"]
        if not df_p.empty:
            fig = px.bar(df_p.groupby("Etapa").size().reset_index(name="Qtd"), x="Etapa", y="Qtd", color="Qtd", color_continuous_scale="Purples", text_auto=True)
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        # --- SALVAMENTO ---
        if st.sidebar.button(f"🚀 SALVAR DADOS: {semana_ref}"):
            with st.spinner("Salvando..."):
                client = conectar_google()
                sh = client.open("BI_Historico")
                try: ws = sh.worksheet(marca)
                except: ws = sh.add_worksheet(title=marca, rows="1000", cols="20")
                
                taxa = f"{(andamento/total*100):.1f}%" if total > 0 else "0%"
                ws.append_row([datetime.now().strftime('%d/%m/%Y'), datetime.now().strftime('%H:%M:%S'), semana_ref, resp_v, equipe_v, total, andamento, perdidos, taxa])
                st.sidebar.success("✅ Salvo!")
                st.balloons()

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
