def kpis_gerais(df):
    return {
        "total": len(df),
        "andamento": len(df[df["Status"]=="Em Andamento"]),
        "perdidos": len(df[df["Status"]=="Perdido"]),
        "ganhos": len(df[df["Status"]=="Ganho"])
    }

