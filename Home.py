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
# MOTOR DE PROCESSAMENTO
# =========================
def processar(arquivo_bruto):
    # Força a leitura em Latin-1 para evitar erros de acentuação (Ã£, Ã¡)
    df = pd.read_csv(arquivo_bruto, sep=';', encoding='latin-1', on_bad_lines='skip')
    
    # RESOLUÇÃO DO ERRO 'str': Remove colunas duplicadas pelo nome antes de qualquer processamento
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    # Mapeamento inteligente de colunas
    cols_map = {}
    for c in df.columns:
        c_low = str(c).lower()
        if "fonte" in c_low: cols_map[c] = "Fonte"
        elif "data de cri" in c_low: cols_map[c] = "Data de Criação"
        elif "responsavel" in c_low and "equipe" not in c_low: cols_map[c] = "Responsável"
        elif "equipe" in c_low: cols_map[c] = "Equipe"
        elif "etapa" in c_low: cols_map[c] = "Etapa"
        elif "motivo de perda" in c_low: cols_map[c] = "Motivo de Perda"
    
    df = df.rename(columns=cols_map)

    # Garante que as colunas críticas são strings únicas (Series)
    for col in ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte"]:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("N/A")
            # Correção visual de caracteres especiais
            df[col] = df[col].str.replace("ExpansÃ£o", "Expansão").str.replace("responsÃ¡vel", "responsável")

    def definir_status(row):
        etapa = str(row.get("Etapa", "")).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]): return "Ganho"
        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada"]: return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(definir_status, axis=1)
    return df

# =========================
# APP INTERFACE
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

# SIDEBAR - OPÇÕES DE SEMANA E MARCA
st.sidebar.header("⚙️ Configurações")
marca = st.sidebar.selectbox("Selecione a Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
semana_ref = st.sidebar.selectbox("Semana de Referência", ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"])

arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(arquivo)
        
        # --- HEADER DE PERFIL ---
        resp_v = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        equipe_v = df["Equipe"].iloc[0] if "Equipe" in df.columns else "Expansão Ensina Mais"

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp_v}</span></div>
            <div class="profile-divider"></div>
            <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe_v}</span></div>
        </div>
        """, unsafe_allow_html=True)

        # --- KPIs ---
        total = len(df)
        andamento = len(df[df["Status"] == "Em Andamento"])
        
        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div class="card-title">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div class="card-title">Em Andamento</div><div class="card-value">{andamento}</div></div>', unsafe_allow_html=True)

        # --- GRÁFICOS ---
        st.divider()
        col_mkt, col_funil = st.columns(2)
        
        with col_mkt:
            st.markdown("### 📡 Marketing & Fontes")
            df_f = df["Fonte"].value_counts().reset_index()
            df_f.columns = ["Fonte", "Qtd"]
            fig_pie = px.pie(df_f, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_pie.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_funil:
            st.markdown("### 📉 Detalhe das Perdas")
            perdidos = df[df["Status"] == "Perdido"]
            if not perdidos.empty:
                df_loss = perdidos.groupby("Etapa").size().reset_index(name="Qtd")
                fig_loss = px.bar(df_loss, x="Etapa", y="Qtd", color="Qtd", color_continuous_scale="Purples", text_auto=True)
                fig_loss.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_loss, use_container_width=True)

        # --- BOTÃO SALVAR ---
        st.sidebar.markdown("---")
        if st.sidebar.button(f"🚀 SALVAR DADOS: {semana_ref}"):
            with st.spinner("Enviando para o histórico..."):
                try:
                    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get("CREDENCIAIS_GOOGLE")), scope)
                    client = gspread.authorize(creds)
                    sh = client.open("BI_Historico")
                    try:
                        ws = sh.worksheet(marca)
                    except:
                        ws = sh.add_worksheet(title=marca, rows="1000", cols="20")
                        ws.append_row(["Data", "Hora", "Semana", "Responsável", "Equipe", "Total", "Andamento", "Perdidos", "Taxa", "Top Fonte"])
                    
                    # Cálculo da Taxa de Avanço (Exemplo)
                    taxa_val = f"{(andamento/total*100):.1f}%" if total > 0 else "0%"
                    
                    ws.append_row([
                        datetime.now().strftime('%d/%m/%Y'), 
                        datetime.now().strftime('%H:%M:%S'), 
                        semana_ref, resp_v, equipe_v, total, andamento, (total-andamento), taxa_val, df_f.iloc[0]['Fonte']
                    ])
                    st.sidebar.success(f"✅ {semana_ref} salva com sucesso!")
                except Exception as e:
                    st.sidebar.error(f"Erro ao salvar: {e}")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
