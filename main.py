import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import io
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="BI Expansão Performance",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# ESTILO
# ===============================
st.markdown("""
<style>
.stApp { background-color: #ffffff; }
[data-testid="stMetric"] { display: none; }

.kpi-card {
    background: #fff;
    padding: 18px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    height: 120px;
}

.card-blue { border-left: 6px solid #3498db; }
.card-green { border-left: 6px solid #2ecc71; }
.card-orange { border-left: 6px solid #f39c12; }
.card-teal { border-left: 6px solid #1abc9c; }
.card-red { border-left: 6px solid #e74c3c; }

.card-label { font-size: 13px; color: #7f8c8d; font-weight: bold; }
.card-value { font-size: 28px; font-weight: bold; }
.card-sub { font-size: 12px; color: #95a5a6; }

.date-range-box {
    background: #2c3e50;
    color: #fff;
    padding: 12px;
    border-radius: 10px;
    text-align: center;
    font-size: 16px;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)

# ===============================
# GOOGLE SHEETS
# ===============================
def conectar_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    if "CREDENCIAIS_GOOGLE" not in os.environ:
        return None

    creds_dict = json.loads(os.environ["CREDENCIAIS_GOOGLE"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open("BI_Historico").sheet1


def salvar_historico(df, semana, marca):
    sheet = conectar_gsheets()
    if sheet is None:
        return False

    df_save = df.copy()
    df_save["marca_ref"] = marca
    df_save["semana_ref"] = semana
    df_save["data_upload"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_rows(df_save.fillna("-").astype(str).values.tolist())
    return True


def carregar_historico():
    sheet = conectar_gsheets()
    if sheet is None:
        return pd.DataFrame()
    return pd.DataFrame(sheet.get_all_records())


# ===============================
# LEITURA E PROCESSAMENTO
# ===============================
def load_data(file):
    raw = file.getvalue()
    for enc in ["utf-8-sig", "latin-1", "cp1252"]:
        try:
            text = raw.decode(enc)
            sep = ";" if ";" in text.splitlines()[0] else ","
            return pd.read_csv(io.StringIO(text), sep=sep)
        except:
            continue
    return pd.DataFrame()


def process_data(df):
    df.columns = [c.strip() for c in df.columns]

    # Data
    col_data = next((c for c in df.columns if "data" in c.lower()), None)
    if col_data:
        df["Data_Criacao_DT"] = pd.to_datetime(df[col_data], errors="coerce", dayfirst=True)

    # Status
    def status_calc(row):
        etapa = str(row.get("Etapa", "")).lower()
        motivo = str(row.get("Motivo de Perda", "")).lower()
        if any(x in etapa for x in ["venda", "fechamento", "matricula", "faturado"]):
            return "Ganho"
        if motivo in ["", "nan", "-", "sem resposta"]:
            return "Em Andamento"
        return "Perdido"

    df["Status_Calc"] = df.apply(status_calc, axis=1)
    return df


# ===============================
# CARD
# ===============================
def metric_card(label, value, sub, style):
    st.markdown(f"""
    <div class="kpi-card {style}">
        <div class="card-label">{label}</div>
        <div class="card-value">{value}</div>
        <div class="card-sub">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


# ===============================
# DASHBOARD
# ===============================
def dashboard(df, titulo):
    if df.empty:
        return

    total = len(df)
    ganhos = len(df[df["Status_Calc"] == "Ganho"])
    conv = ganhos / total * 100 if total else 0

    if "Data_Criacao_DT" in df:
        st.markdown(
            f"""<div class="date-range-box">
            📅 {df["Data_Criacao_DT"].min().date()} → {df["Data_Criacao_DT"].max().date()}
            </div>""",
            unsafe_allow_html=True
        )

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric_card("Leads Totais", total, "Base total", "card-blue")
    with c2: metric_card("Conversão Final", f"{conv:.1f}%", "Vendas", "card-green")
    with c3: metric_card("Leads Ganhos", ganhos, "Fechados", "card-teal")
    with c4: metric_card("Leads Perdidos", len(df[df["Status_Calc"] == "Perdido"]), "Descartes", "card-red")

    st.divider()
    t1, t2, t3 = st.tabs(["📊 Status", "📈 Funil", "🚫 Motivos de Perda"])

    # STATUS
    with t1:
        df_status = (
            df["Status_Calc"]
            .value_counts()
            .reset_index()
            .rename(columns={"index": "Status_Calc", "Status_Calc": "Qtd"})
        )
        fig = px.bar(df_status, x="Status_Calc", y="Qtd", title="Status dos Leads")
        st.plotly_chart(fig, use_container_width=True)

    # FUNIL
    with t2:
        ordem = [
            "Aguardando Resposta",
            "Confirmou Interesse",
            "Qualificado",
            "Reunião Agendada",
            "Reunião Realizada",
            "Venda/Fechamento"
        ]
        df_funil = (
            df["Etapa"]
            .value_counts()
            .reindex(ordem)
            .fillna(0)
            .reset_index()
            .rename(columns={"index": "Etapa", "Etapa": "Qtd"})
        )

        fig = go.Figure(go.Funnel(
            y=df_funil["Etapa"],
            x=df_funil["Qtd"],
            textinfo="value+percent initial"
        ))
        st.plotly_chart(fig, use_container_width=True)

    # MOTIVOS
    with t3:
        perdas = df[df["Status_Calc"] == "Perdido"]
        if not perdas.empty:
            df_motivos = (
                perdas["Motivo de Perda"]
                .value_counts()
                .reset_index()
                .rename(columns={"index": "Motivo de Perda", "Motivo de Perda": "Qtd"})
            )

            fig = px.bar(
                df_motivos,
                x="Qtd",
                y="Motivo de Perda",
                orientation="h",
                title="Motivos de Perda"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("Nenhuma perda registrada")


# ===============================
# INTERFACE
# ===============================
st.title("🚀 BI Expansão Performance")

modo = st.radio("Modo:", ["📥 Importar", "🗄 Histórico"], horizontal=True)

if modo == "📥 Importar":
    marcas = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
    marca = st.sidebar.selectbox("Marca", marcas)
    semana = st.sidebar.selectbox("Semana", ["SEM1", "SEM2", "SEM3", "SEM4", "SEM5"])
    file = st.sidebar.file_uploader("CSV RD Station", type=["csv"])

    if file:
        df = process_data(load_data(file))
        if st.sidebar.button("💾 Salvar Histórico"):
            salvar_historico(df, semana, marca)
        dashboard(df, marca)

else:
    df_hist = carregar_historico()
    if not df_hist.empty:
        marca = st.sidebar.selectbox("Marca", ["Todas"] + list(df_hist["marca_ref"].unique()))
        df_view = df_hist if marca == "Todas" else df_hist[df_hist["marca_ref"] == marca]
        dashboard(df_view, marca)
    else:
        st.warning("Sem dados históricos")
