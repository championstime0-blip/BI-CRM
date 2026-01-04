import pandas as pd

def processar(df):
    df.columns = df.columns.str.strip()

    df = df.loc[:, ~df.columns.duplicated()].copy()

    texto_cols = ["Responsável", "Equipe", "Etapa", "Status", "Motivo de Perda", "Fonte"]
    for col in texto_cols:
        if col in df.columns:
            if isinstance(df[col], pd.DataFrame):
                df[col] = df[col].iloc[:, 0]
            df[col] = df[col].astype(str).fillna("N/A")

    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors="coerce")

    return df
