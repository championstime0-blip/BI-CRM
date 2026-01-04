import streamlit as st

def load_css():
    st.markdown("""
    <style>
    body { background:#0b0f1a; color:#e5e7eb; }
    .card{background:#020617;border:1px solid #1e293b;
          padding:20px;border-radius:12px;text-align:center}
    .card-title{color:#94a3b8;font-size:13px}
    .card-value{font-size:32px;font-weight:700}
    </style>
    """, unsafe_allow_html=True)

