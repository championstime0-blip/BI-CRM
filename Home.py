import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 50px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(34, 211, 238, 0.3); margin-bottom: 20px;
}
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 22px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; border-bottom: 1px solid #1e293b; padding-bottom: 8px; margin-top: 25px; display: flex; align-items: center;
}
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 15px 25px; margin-bottom: 15px; display: flex; justify-content: space-between;
}
.card {
    background: linear-gradient(135deg, #111827, #020617); padding: 20px; border-radius: 12px;
    border: 1px solid #1e293b; text-align: center; height: 100%;
}
.card-value { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #22d3ee; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE PROCESSAMENTO
# ==========================================
def identificar_e_limpar_colunas(df):
    # REMOVE COLUNAS DUPLICADAS (Causa do erro AttributeError)
    # Se houver duas colunas "Motivo de Perda", ele mantém apenas a primeira.
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    cols_originais = df.columns.tolist()
    mapeamento = {}
    for c in cols_originais:
        c_norm = str(c).lower().strip()
        if any(x in c_norm for x in ["data de cri", "data da cri", "created", "criacao"]): mapeamento[c] = "Data de Criação"
        elif any(x in c_norm for x in ["fonte", "origem", "source", "origin"]): mapeamento[c] = "Fonte"
        elif any(x in c_norm for x in ["dono", "respons", "owner"]): mapeamento[c] = "Responsável"
        elif any(x in c_norm for x in ["equipe", "team"]): mapeamento[c] = "Equipe"
        elif c_norm == "etapa": mapeamento[c] = "Etapa"
        elif "motivo" in c_norm: mapeamento[c] = "Motivo de Perda"
    
    return df.rename(columns=mapeamento)

def carregar_csv(arquivo):
    try:
        # Tenta ponto e vírgula primeiro
        df = pd.read_csv(arquivo, sep=';', encoding='latin-1')
        if len(df.columns) <= 1:
            arquivo.seek(0)
            df = pd.read_csv(arquivo, sep=',', encoding='latin-1')
        return df
    except Exception as e:
        st.error(f"Erro na leitura: {e}")
        return None

# ==========================================
# 3. INTERFACE
# ==========================================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
marca_selecionada = st.sidebar.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    df_raw = carregar_csv(arquivo)
    
    if df_raw is not None:
        # Limpa duplicatas e mapeia
        df = identificar_e_limpar_colunas(df_raw)
        
        # Garante colunas básicas
        if "Motivo de Perda" not in df.columns: df["Motivo de Perda"] = ""
        if "Etapa" not in df.columns: df["Etapa"] = ""

        # Conversão de Dados Segura
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
        df = df.dropna(subset=["Data de Criação"])
        
        # Garante que sejam Series de Texto Únicas
        df["Etapa"] = df["Etapa"].astype(str).fillna("")
        df["Motivo de Perda"] = df["Motivo de Perda"].astype(str).fillna("")

        # Lógica de Status
        def definir_status(row):
            et = str(row["Etapa"]).lower()
            mt = str(row["Motivo de Perda"]).lower()
            if any(x in et for x in ["ganho", "venda", "faturado"]): return "Ganho"
            if mt.strip() != "" and mt.strip() != "nan": return "Perdido"
            return "Em Andamento"

        df["Status"] = df.apply(definir_status, axis=1)

        # KPIs e Identidade
        resp = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        equipe = df["Equipe"].iloc[0] if "Equipe" in df.columns else "Geral"
        min_d = df["Data de Criação"].min().strftime('%d/%m/%Y')
        max_d = df["Data de Criação"].max().strftime('%d/%m/%Y')

        st.markdown(f'<div class="profile-header"><span><b>Responsável:</b> {resp}</span><span><b>Equipe:</b> {equipe}</span></div>', unsafe_allow_html=True)

        # CÁLCULO TAXA AVANÇO (Aqui o erro ocorria)
        # Forçamos a seleção de uma única coluna como Series
        col_etapa = df["Etapa"].astype(str).str.lower()
        col_motivo = df["Motivo de Perda"].astype(str).str.lower()
        
        mask_sem_resp = (col_etapa.str.contains("aguardando resposta", na=False)) & \
                        (col_motivo.str.contains("sem resposta", na=False))
        
        total = len(df)
        qtd_sem_resp = len(df[mask_sem_resp])
        em_andamento = len(df[df["Status"] == "Em Andamento"])

        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div>Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div>Em Andamento</div><div class="card-value">{em_andamento}</div></div>', unsafe_allow_html=True)

        # Gráficos
        st.divider()
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown('##### 📡 Marketing & Fontes')
            df_f = df["Fonte"].value_counts().reset_index()
            df_f.columns = ['Fonte', 'Qtd']
            fig_p = px.pie(df_f, values='Qtd', names='Fonte', hole=0.5, color_discrete_sequence=px.colors.sequential.Blues_r)
            fig_p.update_layout(template="plotly_dark", showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_p, use_container_width=True)

        with col_b:
            st.markdown('##### 📉 Funil de Vendas')
            ordem = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
            df_funil = df.groupby("Etapa").size().reindex(ordem).fillna(0).reset_index(name="Qtd")
            fig_f = px.bar(df_funil, x="Qtd", y="Etapa", orientation='h', color="Qtd", color_continuous_scale="Blues")
            fig_f.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_f, use_container_width=True)

        # Botão Salvar
        st.divider()
        if st.button("🚀 SALVAR DADOS NO GOOGLE SHEETS"):
            try:
                etapas_ok = ["qualificado", "reunião agendada", "reunião realizada", "follow-up", "negociação", "em aprovação", "faturado"]
                qtd_ok = len(df[df["Etapa"].str.lower().isin(etapas_ok)])
                base = total - qtd_sem_resp
                taxa = (qtd_ok / base * 100) if base > 0 else 0
                
                creds_json = os.environ.get("CREDENCIAIS_GOOGLE")
                creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
                client = gspread.authorize(creds)
                sh = client.open("BI_Historico")
                
                try: ws = sh.worksheet(marca_selecionada)
                except: 
                    ws = sh.add_worksheet(title=marca_selecionada, rows="1000", cols="20")
                    ws.append_row(["Data", "Hora", "Semana", "Recorte", "Responsavel", "Equipe", "Total", "Andamento", "Perdidos", "Sem Resposta", "Taxa", "Top Fonte"])

                agora = datetime.now()
                ws.append_row([
                    agora.strftime('%d/%m/%Y'), agora.strftime('%H:%M:%S'), agora.strftime('%Y-W%W'),
                    f"{min_d} a {max_d}", str(resp), str(equipe), int(total), int(em_andamento), 
                    int(total-em_andamento), int(qtd_sem_resp), f"{taxa:.1f}%", str(df_f.iloc[0]['Fonte'] if not df_f.empty else "N/A")
                ])
                st.success("✅ Salvo com sucesso!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
