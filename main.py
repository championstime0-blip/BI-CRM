import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
import io
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials

# ===============================
# CONFIGURAÇÃO DA PÁGINA
# ===============================
st.set_page_config(
    page_title="BI Expansão Performance",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===============================
# ESTILO
# ===============================
st.markdown("""
<style>
.stApp { background-color: #ffffff; }
[data-testid="stMetric"] { display: none; }

.kpi-card {
    background: #fff;
    padding: 18px;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    height: 120px;
}

.card-blue { border-left: 6px solid #3498db; }
.card-green { border-left: 6px solid #2ecc71; }
.card-orange { border-left: 6px solid #f39c12; }
.card-teal { border-left: 6px solid #1abc9c; }
.card-red { border-left: 6px solid #e74c3c; }

.card-label { font-size: 13px; color: #7f
