import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import unicodedata
import io

# =============================================================================
# CONFIG
# =============================================================================
st.set_page_config(page_title="BI Funil Comercial", layout="wide")

# =============================================================================
# FUNÇÕES AUXILIARES
# =============================================================================
def normalizar(txt):
    if pd.isna(txt):
        return ""
    txt = str(txt).strip().lower()
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("utf-8")
    return txt


def carregar_csv(file):
    raw = file.getvalue()
    for enc in ["utf-8-sig", "latin-1", "iso-8859-1"]:
        try:
            content = raw.decode(enc)
            sep = ";" if ";" in content.splitlines()[0] else ","
            return pd.read_csv(io.StringIO(content), sep=sep)
        except:
            pass
    return pd.DataFrame()

# =============================================================================
# PROCESSAMENTO
# =============================================================================
def processar_dados(df):
    df.columns = [c.strip() for c in df.columns]

    if "Etapa" not in df.columns:
        st.error("Coluna 'Etapa' não encontrada no CSV.")
        st.stop()

    df["Etapa_Normalizada"] = df["Etapa"].apply(normalizar)

    def mapear_etapa(e):
        if "sem contato" in e:
            return "Sem contato"
        if "aguardando" in e:
            return "Aguardando Resposta"
        if "confirmou" in e:
            return "Confirmou Interesse"
        if "qualificado" in e:
            return "Qualificado"
        if "reuniao agendada" in e:
            return "Reunião Agendada"
        if "reuniao realizada" in e:
            return "Reunião Realizada"
        if "follow" in e:
            return "Follow-up"
        if "negociacao" in e:
            return "negociação"
        if "aprovacao" in e:
            return "em aprovação"
        if "faturado" in e:
            return "faturado"
        return "Sem contato"

    df["Etapa_Funil"] = df["Etapa_Normalizada"].apply(mapear_etapa)

    # STATUS CALCULADO
    def status_calc(etapa):
        if etapa == "faturado":
            return "Ganho"
        return "Em andamento"

    df["Status_Calc"] = df["Etapa_Funil"].apply(status_calc)

    return df

# =============================================================================
# DASHBOARD
# =============================================================================
def dashboard(df):
    st.title("📊 Funil Comercial")

    # -------------------------
    # KPIs
    # -------------------------
    total = len(df)
    ganhos = len(df[df["Status_Calc"] == "Ganho"])
    conversao = (ganhos / total * 100) if total > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Leads Totais", total)
    c2.metric("Faturados", ganhos)
    c3.metric("Conversão (%)", f"{conversao:.1f}%")

    st.divider()

    # -------------------------
    # STATUS DOS LEADS
    # -------------------------
    df_status = df["Status_Calc"].value_counts().reset_index()
    df_status.columns = ["Status", "Qtd"]

    fig_status = px.bar(
        df_status,
        x="Status",
        y="Qtd",
        text="Qtd",
        title="Status dos Leads"
    )
    st.plotly_chart(fig_status, use_container_width=True)

    st.divider()

    # -------------------------
    # FUNIL (ORDEM FIXA)
    # -------------------------
    ordem_funil = [
        "Sem contato",
        "Aguardando Resposta",
        "Confirmou Interesse",
        "Qualificado",
        "Reunião Agendada",
        "Reunião Realizada",
        "Follow-up",
        "negociação",
        "em aprovação",
        "faturado"
    ]

    df_funil = (
        df["Etapa_Funil"]
        .value_counts()
        .reindex(ordem_funil)
        .fillna(0)
        .reset_index()
    )
    df_funil.columns = ["Etapa", "Qtd"]

    fig_funil = go.Figure(
        go.Funnel(
            y=df_funil["Etapa"],
            x=df_funil["Qtd"],
            textinfo="value+percent initial"
        )
    )

    fig_funil.update_layout(title="Funil de Vendas")
    st.plotly_chart(fig_funil, use_container_width=True)

# =============================================================================
# APP
# =============================================================================
arquivo = st.file_uploader("📤 Envie o CSV", type=["csv"])

if arquivo:
    df_raw = carregar_csv(arquivo)

    if not df_raw.empty:
        df = processar_dados(df_raw)
        dashboard(df)
    else:
        st.error("Erro ao carregar o arquivo CSV.")
