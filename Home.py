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
.top-item { border-left: 3px solid #22d3ee; padding: 10px; margin-bottom: 5px; background: rgba(34, 211, 238, 0.05); display: flex; justify-content: space-between; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE PROCESSAMENTO (BLINDADO)
# ==========================================
def identificar_colunas(df):
    """Mapeia colunas ignorando acentos e cases"""
    cols_originais = df.columns.tolist()
    mapeamento = {}
    
    for c in cols_originais:
        c_norm = str(c).lower().strip()
        # Data
        if any(x in c_norm for x in ["data de cri", "data da cri", "created", "criacao"]):
            mapeamento[c] = "Data de Criação"
        # Fonte
        elif any(x in c_norm for x in ["fonte", "origem", "source", "origin"]):
            mapeamento[c] = "Fonte"
        # Responsável
        elif any(x in c_norm for x in ["dono", "respons", "owner"]):
            mapeamento[c] = "Responsável"
        # Equipe
        elif any(x in c_norm for x in ["equipe", "team"]):
            mapeamento[c] = "Equipe"
        # Etapa (exato)
        elif c_norm == "etapa":
            mapeamento[c] = "Etapa"
        # Motivo
        elif "motivo" in c_norm:
            mapeamento[c] = "Motivo de Perda"
            
    return df.rename(columns=mapeamento)

def carregar_csv(arquivo):
    """Tenta ler com múltiplos separadores"""
    try:
        # Tenta Ponto-e-vírgula (Brasil)
        df = pd.read_csv(arquivo, sep=';', encoding='latin-1')
        if len(df.columns) <= 1:
            arquivo.seek(0)
            # Tenta Vírgula (Padrão)
            df = pd.read_csv(arquivo, sep=',', encoding='latin-1')
        return df
    except Exception as e:
        st.error(f"Erro na leitura física do arquivo: {e}")
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
        df = identificar_colunas(df_raw)
        
        # Validação de Segurança
        colunas_necessarias = ["Data de Criação", "Etapa", "Fonte"]
        faltando = [c for c in colunas_necessarias if c not in df.columns]
        
        if faltando:
            st.error(f"❌ Não conseguimos identificar as colunas: {faltando}")
            st.write("Colunas detectadas no seu arquivo:", df_raw.columns.tolist())
            st.stop()

        # Limpeza de Dados
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
        df = df.dropna(subset=["Data de Criação"])
        df["Etapa"] = df["Etapa"].astype(str).fillna("Sem Etapa")
        df["Motivo de Perda"] = df.get("Motivo de Perda", pd.Series([""])).astype(str).fillna("")

        # Lógica de Status
        def definir_status(row):
            etapa = row["Etapa"].lower()
            motivo = row["Motivo de Perda"].lower()
            if any(x in etapa for x in ["ganho", "venda", "faturado"]): return "Ganho"
            if motivo != "" and motivo != "nan": return "Perdido"
            return "Em Andamento"

        df["Status"] = df.apply(definir_status, axis=1)

        # Extração de Identidade
        resp = df["Responsável"].iloc[0] if "Responsável" in df.columns else "N/A"
        equipe = df["Equipe"].iloc[0] if "Equipe" in df.columns else "Geral"
        min_d = df["Data de Criação"].min().strftime('%d/%m/%Y')
        max_d = df["Data de Criação"].max().strftime('%d/%m/%Y')

        # Visualização Superior
        st.markdown(f'<div class="profile-header"><span><b>Responsável:</b> {resp}</span><span><b>Equipe:</b> {equipe}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:center; color:#94a3b8; margin-bottom:20px;">📅 {min_d} até {max_d}</div>', unsafe_allow_html=True)

        # KPIs
        total = len(df)
        em_andamento = len(df[df["Status"] == "Em Andamento"])
        perdidos = len(df[df["Status"] == "Perdido"])
        
        # Cálculo de Perda s/ Resposta (Ajustado para evitar erro 0)
        mask_sem_resp = (df["Etapa"].str.contains("Aguardando Resposta", case=False, na=False)) & \
                        (df["Motivo de Perda"].str.contains("sem resposta", case=False, na=False))
        qtd_sem_resp = len(df[mask_sem_resp])

        c1, c2 = st.columns(2)
        with c1: st.markdown(f'<div class="card"><div style="color:#94a3b8">Leads Totais</div><div class="card-value">{total}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="card"><div style="color:#94a3b8">Em Andamento</div><div class="card-value">{em_andamento}</div></div>', unsafe_allow_html=True)

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
        if st.button("🚀 SALVAR NA PLANILHA BI_HISTORICO"):
            with st.spinner("Salvando..."):
                try:
                    # Cálculo da Taxa
                    etapas_ok = ["Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
                    qtd_ok = len(df[df["Etapa"].isin(etapas_ok)])
                    base = total - qtd_sem_resp
                    taxa = (qtd_ok / base * 100) if base > 0 else 0
                    
                    # Conexão Google
                    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(os.environ.get("CREDENCIAIS_GOOGLE")), scope)
                    client = gspread.authorize(creds)
                    sh = client.open("BI_Historico")
                    
                    try:
                        ws = sh.worksheet(marca_selecionada)
                    except:
                        ws = sh.add_worksheet(title=marca_selecionada, rows="1000", cols="20")
                        ws.append_row(["Data", "Hora", "Semana", "Recorte", "Responsavel", "Equipe", "Total", "Andamento", "Perdidos", "Sem Resposta", "Taxa", "Top Fonte"])

                    agora = datetime.now()
                    top_f = df_f.iloc[0]['Fonte'] if not df_f.empty else "N/A"
                    
                    ws.append_row([
                        agora.strftime('%d/%m/%Y'), agora.strftime('%H:%M:%S'), agora.strftime('%Y-W%W'),
                        f"{min_d} a {max_d}", resp, equipe, total, em_andamento, perdidos, qtd_sem_resp, f"{taxa:.1f}%", top_f
                    ])
                    st.success("✅ Salvo com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
