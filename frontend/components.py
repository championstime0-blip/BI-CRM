import streamlit as st

def card(title, value):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def title(text):
    st.markdown(f"<h1>{text}</h1>", unsafe_allow_html=True)

