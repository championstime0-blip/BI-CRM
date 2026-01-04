import streamlit as st

def card(title, value):
    st.markdown(f"""
    <div class="card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f"""
    <div class="futuristic-sub">
        <span class="sub-icon">{icon}</span>
        {text}
    </div>
    """, unsafe_allow_html=True)

def profile_header(responsavel, equipe):
    st.markdown(f"""
    <div class="profile-header">
        <div class="profile-group">
            <span class="profile-label">Responsável</span>
            <span class="profile-value">{responsavel}</span>
        </div>
        <div class="profile-divider"></div>
        <div class="profile-group">
            <span class="profile-label">Equipe do Responsável</span>
            <span class="profile-value">{equipe}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

def date_card(inicio, fim):
    st.markdown(f"""
    <div class="date-card">
        <div class="date-label">📅 Recorte Temporal da Base</div>
        <div class="date-value">
            {inicio} <span style="color:#64748b; padding:0 10px;">➔</span> {fim}
        </div>
    </div>
    """, unsafe_allow_html=True)
