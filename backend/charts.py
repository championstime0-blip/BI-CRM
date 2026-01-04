import plotly.express as px

def grafico_fontes(df):
    if "Fonte" not in df.columns:
        return None
    fonte = df["Fonte"].value_counts().reset_index()
    fonte.columns = ["Fonte","Qtd"]
    fig = px.pie(fonte, values="Qtd", names="Fonte", hole=0.55)
    fig.update_layout(template="plotly_dark")
    return fig

def grafico_funil(df, etapas):
    funil = df.groupby("Etapa").size().reindex(etapas).fillna(0).reset_index(name="Qtd")
    fig = px.bar(funil, x="Qtd", y="Etapa", orientation="h")
    fig.update_layout(template="plotly_dark")
    return fig

