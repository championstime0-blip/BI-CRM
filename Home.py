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
    letter-spacing: 3px; margin-bottom: 10px;
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px;
    padding: 20px 30px; margin-bottom: 15px;
    display: flex; justify-content: space-between;
}
.profile-label { color: #94a3b8; font-size: 13px; text-transform: uppercase; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px;
    border: 1px solid #1e293b; text-align: center;
}
.card-value { font-family: 'Orbitron'; font-size: 36px; color: #22d3ee; }
</style>
""", unsafe_allow_html=True)

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def processar(arquivo_bruto):
    # Leitura do CSV (RD Station)
    df = pd.read_csv(
        arquivo_bruto,
        sep=';',
        encoding='latin-1',
        on_bad_lines='skip'
    )

    # Remove duplicadas ANTES do rename
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Mapeamento inteligente de colunas
    mapeamento = {}
    for c in df.columns:
        c_up = str(c).upper().strip()
        if "FONTE" in c_up:
            mapeamento[c] = "Fonte"
        elif "DATA DE CRIA" in c_up:
            mapeamento[c] = "Data de Criação"
        elif "RESPONS" in c_up and "EQUIPE" not in c_up:
            mapeamento[c] = "Responsável"
        elif "EQUIPE" in c_up:
            mapeamento[c] = "Equipe"
        elif "ETAPA" in c_up:
            mapeamento[c] = "Etapa"
        elif "MOTIVO DE PERDA" in c_up:
            mapeamento[c] = "Motivo de Perda"

    df = df.rename(columns=mapeamento)

    # 🔴 PONTO CRÍTICO: remove duplicadas APÓS o rename
    df = df.loc[:, ~df.columns.duplicated()].copy()

    # Limpeza segura de texto
    colunas_texto = ["Responsável", "Equipe", "Etapa", "Motivo de Perda", "Fonte"]
    for col in colunas_texto:
        if col in df.columns:
            # Garantia absoluta de Series
            if isinstance(df[col], pd.DataFrame):
                df[col] = df[col].iloc[:, 0]

            df[col] = (
                df[col]
                .astype(str)
                .fillna("N/A")
                .str.replace("ExpansÃ£o", "Expansão", regex=False)
                .str.replace("responsÃ¡vel", "responsável", regex=False)
            )

    # Definição de status
    def definir_status(row):
        etapa = str(row.get("Etapa", "")).lower()
        if any(x in etapa for x in ["faturado", "ganho", "venda"]):
            return "Ganho"

        motivo = str(row.get("Motivo de Perda", "")).strip().lower()
        if motivo not in ["", "nan", "none", "-", "0", "nada"]:
            return "Perdido"

        return "Em Andamento"

    df["Status"] = df.apply(definir_status, axis=1)

    return df

# =========================
# INTERFACE DO APP
# =========================
st.markdown('<div class="futuristic-title">BI CRM Expansão</div>', unsafe_allow_html=True)

st.sidebar.header("Configurações")
marca = st.sidebar.selectbox("Marca", ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"])
semana_ref = st.sidebar.selectbox(
    "Semana de Referência",
    ["Semana 1", "Semana 2", "Semana 3", "Semana 4", "Semana 5", "Fechamento Mês"]
)

arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = processar(arquivo)

        resp_v = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        equipe_v = df["Equipe"].iloc[0] if "Equipe" in df.columns else "Expansão Ensina Mais"

        st.markdown(f"""
        <div class="profile-header">
            <div>
                <div class="profile-label">Responsável</div>
                <div class="profile-value">{resp_v}</div>
            </div>
            <div>
                <div class="profile-label">Equipe</div>
                <div class="profile-value">{equipe_v}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        total = len(df)
        andamento = len(df[df["Status"] == "Em Andamento"])

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="card"><div>Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="card"><div>Em Andamento</div><div class="card-value">{andamento}</div></div>', unsafe_allow_html=True)

        st.divider()
        st.markdown("### Detalhe das Perdas")

        perdidos = df[df["Status"] == "Perdido"]
        if not perdidos.empty:
            df_loss = perdidos.groupby("Etapa").size().reset_index(name="Qtd")
            fig = px.bar(
                df_loss,
                x="Etapa",
                y="Qtd",
                color="Qtd",
                text_auto=True,
                color_continuous_scale="Purples"
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.sidebar.markdown("---")
        if st.sidebar.button(f"SALVAR DADOS: {semana_ref}"):
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(os.environ["CREDENCIAIS_GOOGLE"]),
                scope
            )
            client = gspread.authorize(creds)
            sh = client.open("BI_Historico")

            try:
                ws = sh.worksheet(marca)
            except:
                ws = sh.add_worksheet(title=marca, rows="1000", cols="20")

            ws.append_row([
                datetime.now().strftime('%d/%m/%Y'),
                datetime.now().strftime('%H:%M:%S'),
                semana_ref,
                resp_v,
                equipe_v,
                total,
                andamento,
                total - andamento,
                f"{(andamento / total * 100):.1f}%"
            ])

            st.sidebar.success("Dados salvos com sucesso.")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
