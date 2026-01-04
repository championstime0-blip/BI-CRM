import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# =========================
# CONFIGURAÇÃO E CSS
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 50px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(34, 211, 238, 0.3); margin-bottom: 20px;
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

# =========================
# MOTOR DE PROCESSAMENTO
# =========================
def identificar_colunas(df):
    # Remove colunas duplicadas pelo nome antes de renomear
    df = df.loc[:, ~df.columns.duplicated()].copy()
    
    mapeamento = {}
    for c in df.columns:
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
        df = pd.read_csv(arquivo, sep=';', encoding='latin-1')
        if len(df.columns) <= 1:
            arquivo.seek(0)
            df = pd.read_csv(arquivo, sep=',', encoding='latin-1')
        return df
    except Exception as e:
        st.error(f"Erro na leitura: {e}")
        return None

# =========================
# INTERFACE
# =========================
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]
marca_selecionada = st.sidebar.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    df_raw = carregar_csv(arquivo)
    
    if df_raw is not None:
        df = identificar_colunas(df_raw)
        
        # --- SOLUÇÃO PARA O ERRO 'str' ---
        # Garantimos que selecionamos apenas UMA coluna mesmo que o nome se repita
        def extrair_serie_limpa(dataframe, nome_coluna):
            if nome_coluna in dataframe.columns:
                col = dataframe[nome_coluna]
                # Se for DataFrame (duplicada), pega a primeira coluna
                if isinstance(col, pd.DataFrame):
                    col = col.iloc[:, 0]
                return col.astype(str).fillna("")
            return pd.Series([""] * len(dataframe)).astype(str)

        col_etapa = extrair_serie_limpa(df, "Etapa")
        col_motivo = extrair_serie_limpa(df, "Motivo de Perda")
        
        # Aplicamos as transformações na Series individual
        df["Etapa_Clean"] = col_etapa
        df["Motivo_Clean"] = col_motivo

        # Conversão de Data
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
        df = df.dropna(subset=["Data de Criação"])

        # Lógica de Status
        def definir_status(row):
            et = str(row["Etapa_Clean"]).lower()
            mt = str(row["Motivo_Clean"]).lower()
            if any(x in et for x in ["ganho", "venda", "faturado"]): return "Ganho"
            if mt.strip() != "" and mt.strip() != "nan": return "Perdido"
            return "Em Andamento"

        df["Status"] = df.apply(definir_status, axis=1)

        # KPIs
        total = len(df)
        em_andamento = len(df[df["Status"] == "Em Andamento"])
        
        # Filtro Sem Resposta (Usando as colunas limpas)
        mask_sem_resp = (df["Etapa_Clean"].str.lower().str.contains("aguardando resposta", na=False)) & \
                        (df["Motivo_Clean"].str.lower().str.contains("sem resposta", na=False))
        qtd_sem_resp = len(df[mask_sem_resp])

        # Exibição
        resp = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        st.markdown(f'<div class="profile-header"><span><b>Responsável:</b> {resp}</span><span><b>Marca:</b> {marca_selecionada}</span></div>', unsafe_allow_html=True)

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
            df_funil = df.groupby("Etapa_Clean").size().reindex(ordem).fillna(0).reset_index(name="Qtd")
            fig_f = px.bar(df_funil, x="Qtd", y="Etapa_Clean", orientation='h', color="Qtd", color_continuous_scale="Blues")
            fig_f.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_f, use_container_width=True)

        # Salvar
        if st.button("🚀 SALVAR NO GOOGLE SHEETS"):
            try:
                etapas_ok = ["qualificado", "reunião agendada", "reunião realizada", "follow-up", "negociação", "em aprovação", "faturado"]
                qtd_ok = len(df[df["Etapa_Clean"].str.lower().isin(etapas_ok)])
                base = total - qtd_sem_resp
                taxa = (qtd_ok / base * 100) if base > 0 else 0
                
                creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get("CREDENCIAIS_GOOGLE")), ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"])
                client = gspread.authorize(creds)
                sh = client.open("BI_Historico")
                
                try: ws = sh.worksheet(marca_selecionada)
                except: 
                    ws = sh.add_worksheet(title=marca_selecionada, rows="1000", cols="20")
                    ws.append_row(["Data", "Hora", "Semana", "Recorte", "Responsavel", "Equipe", "Total", "Andamento", "Perdidos", "Sem Resposta", "Taxa", "Top Fonte"])

                agora = datetime.now()
                ws.append_row([
                    agora.strftime('%d/%m/%Y'), agora.strftime('%H:%M:%S'), agora.strftime('%Y-W%W'),
                    f"{df['Data de Criação'].min().strftime('%d/%m/%Y')} a {df['Data de Criação'].max().strftime('%d/%m/%Y')}", 
                    str(resp), "Geral", int(total), int(em_andamento), int(total-em_andamento), int(qtd_sem_resp), f"{taxa:.1f}%", str(df_f.iloc[0]['Fonte'] if not df_f.empty else "N/A")
                ])
                st.success("✅ Salvo!")
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")
