import streamlit as st

def load_css():
    st.markdown("""
    <style>
    body { background:#0f172a; color:white; }
    .card { background:#020617; padding:20px; border-radius:12px; }
    .card-title { color:#94a3b8; font-size:14px; }
    .card-value { font-size:32px; font-weight:700; }
    </style>
    """, unsafe_allow_html=True)
