import streamlit as st
import pandas as pd
# ... (conectar_google e CSS aqui)

def carregar_dados_marca(marca):
    client = conectar_google()
    sh = client.open("BI_Historico")
    ws = sh.worksheet(marca)
    return pd.DataFrame(ws.get_all_records())

st.title("📈 Painel Histórico")
marca = st.selectbox("Ver Marca:", ["Microlins", "PreparaIA", "Ensina Mais 1", "Ensina Mais 2"])

df_hist = carregar_dados_marca(marca)

if not df_hist.empty:
    df_hist['Data'] = pd.to_datetime(df_hist['Data'], dayfirst=True)
    
    # Filtros de Data
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Início", df_hist['Data'].min())
    with col2:
        data_fim = st.date_input("Fim", df_hist['Data'].max())
        
    mask = (df_hist['Data'].dt.date >= data_inicio) & (df_hist['Data'].dt.date <= data_fim)
    st.dataframe(df_hist.loc[mask], use_container_width=True)
