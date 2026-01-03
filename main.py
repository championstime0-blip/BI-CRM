# ===== MOTIVOS DE PERDA =====
perdas = df[df["Status_Calc"] == "Perdido"]

if not perdas.empty:
    df_motivos = (
        perdas["Motivo de Perda"]
        .value_counts()
        .reset_index(name="Qtd")
        .rename(columns={"index": "Motivo de Perda"})
    )

    fig_loss = px.bar(
        df_motivos,
        x="Qtd",
        y="Motivo de Perda",
        orientation="h",
        title="Motivos de Perda"
    )

    st.plotly_chart(fig_loss, use_container_width=True)
