import pandas as pd

ETAPAS_FUNIL = [
    "sem contato","aguardando resposta","confirmou interesse",
    "qualificado","reunião agendada","reunião realizada",
    "follow-up","negociação","em aprovação","faturado"
]

def processar(df):
    df.columns = df.columns.str.strip()

    rename = {}
    for c in df.columns:
        cl = c.lower()
        if cl in ["fonte","origem","source"]:
            rename[c] = "Fonte"
        if cl in ["data de criação","created date"]:
            rename[c] = "Data de Criação"
        if cl in ["responsável","owner"]:
            rename[c] = "Responsável"
        if cl in ["equipe","team"]:
            rename[c] = "Equipe"

    df = df.rename(columns=rename)

    if "Motivo de Perda" not in df.columns:
        df["Motivo de Perda"] = ""

    df["Etapa"] = df["Etapa"].astype(str).str.strip().str.lower()
    df["Motivo de Perda"] = df["Motivo de Perda"].astype(str)

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors="coerce")

    def status(row):
        if "faturado" in row["Etapa"]:
            return "Ganho"
        if row["Motivo de Perda"].strip():
            return "Perdido"
        return "Em Andamento"

    df["Status"] = df.apply(status, axis=1)
    return df

