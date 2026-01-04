import streamlit as st
from backend.loader import load_csv
from backend.processor import processar
from frontend.styles import load_css
from frontend.pages import dashboard

st.set_page_config(layout="wide")
load_css()

st.title("BI CRM Expansão")

file = st.file_uploader("Upload CSV", type="csv")

if file:
    df = processar(load_csv(file))
    dashboard(df)
