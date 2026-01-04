import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

st.set_page_config(page_title="Comparativo Marcas", layout="wide")

st.title("⚔️ Comparativo de Marcas")

def carregar_tudo():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
    client = gspread.authorize(creds)
    sh = client.open("BI_Historico")
    
    full_df = pd.DataFrame()
    marcas = ["Microlins", "PreparaIA", "Ensina Mais 1", "Ensina Mais 2"]
    
    for m in marcas:
        try:
            ws = sh.worksheet(m)
            df = pd.DataFrame(ws.get_all_records())
            if not df.empty:
                df['Marca'] = m
                # Limpeza da Taxa
                df['Taxa_Num'] = df['Taxa Avanço'].astype(str).str.replace('%','').str.replace(',','.').astype(float)
                full_df = pd.concat([full_df, df])
        except: pass
    return full_df

if st.button("Atualizar Comparativo"):
    df_all = carregar_tudo()
    
    if not df_all.empty:
        st.subheader("Média de Taxa de Avanço por Marca")
        fig = px.bar(df_all.groupby('Marca')['Taxa_Num'].mean().reset_index(), x="Marca", y="Taxa_Num", color="Marca", text_auto=True)
        fig.update_layout(template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Volume Total de Leads")
        fig2 = px.pie(df_all, names="Marca", values="Total", hole=0.5)
        fig2.update_layout(template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.error("Nenhum dado encontrado nas planilhas.")
