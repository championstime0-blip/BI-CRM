def calcular_kpis(df):
    total = len(df)

    perdidos = df[df["Status"].str.lower() == "perdido"]
    andamento = df[df["Status"].str.lower().str.contains("andamento", na=False)]

    aguardando = df[df["Etapa"].str.lower().str.contains("aguardando", na=False)]

    return {
        "total": total,
        "perdidos": len(perdidos),
        "andamento": len(andamento),
        "aguardando": len(aguardando)
    }
