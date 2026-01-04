import pandas as pd

def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

