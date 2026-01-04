def calcular_kpis(df):
    total = len(df)

    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]

    perda_sem_resposta = df[
        (df["Etapa"].str.strip() == "Aguardando Resposta") &
        (df["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))
    ]

    return {
        "total": total,
        "perdidos_df": perdidos,
        "em_andamento_df": em_andamento,
        "perda_sem_resposta_df": perda_sem_resposta
    }
