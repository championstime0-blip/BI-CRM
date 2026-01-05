import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Histórico | Time Machine", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (IDENTICA A HOME)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }
.futuristic-title {
    font-family: 'Orbitron', sans-serif; font-size: 42px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 20px; text-shadow: 0 0 20px rgba(34, 211, 238, 0.3);
}
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif; font-size: 24px; font-weight: 700; text-transform: uppercase;
    color: #e2e8f0; letter-spacing: 2px; border-bottom: 1px solid #1e293b;
    padding-bottom: 8px; margin-top: 30px; margin-bottom: 20px; display: flex; align-items: center;
}
.sub-icon { margin-right: 12px; font-size: 24px; color: #22d3ee; text-shadow: 0 0 10px rgba(34, 211, 238, 0.6); }
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px; border-radius: 16px; border: 1px solid #1e293b; text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05); transition: all 0.3s ease; height: 100%;
}
.card:hover { box-shadow: 0 0 25px rgba(56,189,248,0.2); border-color: #38bdf8; transform: translateY(-2px); }
.card-title {
    font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8;
    text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; min-height: 30px; display: flex; align-items: center; justify-content: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.funnel-card {
    background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%); border-top: 2px solid #22d3ee;
    border-radius: 0 0 12px 12px; padding: 15px; text-align: center; margin-top: -10px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.funnel-label { font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.2px; }
.funnel-percent { font-family: 'Orbitron', sans-serif; font-size: 32px; font-weight: 700; color: #22d3ee; margin: 5px 0; }
.funnel-sub { font-size: 10px; color: #64748b; font-style: italic; }
.top-source-container { margin-top: 25px; padding: 0; }
.top-item {
    border-left: 3px solid #22d3ee; padding: 12px 15px; margin-bottom: 8px; border-radius: 0 8px 8px 0; display: flex; align-items: center; justify-content: space-between;
    transition: transform 0.2s; border: 1px solid rgba(34, 211, 238, 0.1); border-left-width: 3px;
}
.top-item:hover { transform: translateX(5px); border-color: rgba(34, 211, 238, 0.3); }
.top-rank { font-family: 'Orbitron', sans-serif; font-weight: 900; color: #22d3ee; font-size: 16px; margin-right: 12px; min-width: 25px; }
.top-name { font-family: 'Rajdhani', sans-serif; color: #f1f5f9; font-weight: 600; font-size: 15px; flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 10px; }
.top-val-abs { color: #fff; font-weight: bold; font-size: 14px; display: block; }
.top-val-pct { color: #94a3b8; font-size: 10px; font-weight: 400; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE
# =========================
def conectar_google():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_json = os.environ.get("gcp_service_account") or st.secrets.get("gcp_service_account")
        if not creds_json: 
             creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
             return gspread.authorize(creds)
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        return None

# =========================
# FUNÇÕES DE UI E PROCESSAMENTO
# =========================
ETAPAS_FUNIL = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]

def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def processar_snapshot(df):
    # Recalcula Status caso não tenha sido salvo ou precise de refresh
    def status(row):
        etapa_lower = str(row["Etapa"]).lower() if "Etapa" in row else ""
        motivo = str(row["Motivo de Perda"]).strip().lower() if "Motivo de Perda" in row else ""
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        if motivo not in ["", "nan", "none", "-", "nan", "0", "nada", "n/a"]: return "Perdido"
        return "Em Andamento"
    
    if "Status" not in df.columns:
        df["Status"] = df.apply(status, axis=1)
        
    # Tratamento de Strings e Numeros
    if "Fonte" in df.columns:
        df["Fonte"] = df["Fonte"].fillna("Desconhecido").astype(str)
        
    return df

# =========================
# DASHBOARD RENDER (CÓPIA DA HOME PARA VISUAL IDÊNTICO)
# =========================
def render_dashboard(df):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    # KPIs Topo
    c1, c2, c3 = st.columns(3)
    with c1: card("Total no Snapshot", total)
    with c2: card("Em Andamento", len(em_andamento))
    with c3: card("Perdidos", len(perdidos))
    
    st.divider()

    col_mkt, col_funil = st.columns(2)
    
    # 1. MKT (Gráfico de Pizza e Top 3)
    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2', '#155e75'])
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            fig_pie.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Lista TOP 3 estilizada
            st.markdown('<div class="futuristic-sub" style="font-size:18px; margin-top:20px; border:none;"><span class="sub-icon">🏆</span>TOP 3 CANAIS</div>', unsafe_allow_html=True)
            top3 = df_fonte.head(3)
            max_val = top3['Qtd'].max() if not top3.empty else 1
            html = '<div class="top-source-container">'
            for i, row in top3.iterrows():
                perc = (row['Qtd']/total*100) if total > 0 else 0
                wid = (row['Qtd']/max_val*100) if max_val > 0 else 0
                html += f'''
                <div class="top-item" style="background: linear-gradient(90deg, rgba(34, 211, 238, 0.15) {wid}%, rgba(15, 23, 42, 0.0) {wid}%);">
                    <div style="display:flex; align-items:center; width: 70%;">
                        <span class="top-rank">#{i+1}</span><span class="top-name">{row['Fonte']}</span>
                    </div>
                    <div class="top-val-group">
                        <span class="top-val-abs">{row['Qtd']}</span><span class="top-val-pct">{perc:.1f}%</span>
                    </div>
                </div>'''
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.warning("Dados de Fonte indisponíveis.")

    # 2. Funil
    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL")
        if "Etapa" in df.columns:
            df_funil = df.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
            df_funil["Percentual"] = (df_funil["Qtd"] / total * 100).round(1) if total > 0 else 0
            
            # Cálculo Taxa de Avanço
            avanco_list = ["Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
            df['Etapa_Clean'] = df['Etapa'].str.strip()
            qtd_avanco = len(df[df['Etapa_Clean'].isin(avanco_list)])
            
            perda_especifica = df[
                (df["Etapa"].str.strip() == "Aguardando Resposta") & 
                (df["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))
            ] if "Motivo de Perda" in df.columns else pd.DataFrame()
            
            qtd_sem_resp = len(perda_especifica)
            base = total - qtd_sem_resp
            taxa_avanco = (qtd_avanco / base * 100) if base > 0 else 0
            
            fig_funil = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h", text=df_funil["Percentual"].astype(str)+"%", color="Qtd", color_continuous_scale="Blues")
            fig_funil.update_layout(template="plotly_dark", showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_funil, use_container_width=True)
            
            st.markdown(f'''
            <div class="funnel-card">
                <div class="funnel-label">🚀 Taxa de Avanço Real</div>
                <div class="funnel-percent">{taxa_avanco:.1f}%</div>
                <div class="funnel-sub">Leads Qualificados+ / (Total - Sem Resposta)</div>
            </div>''', unsafe_allow_html=True)
        else:
            st.warning("Dados de Etapa indisponíveis.")

    st.divider()
    subheader_futurista("🚫", "DETALHE DAS PERDAS")
    
    if not perdidos.empty and "Etapa" in perdidos.columns:
        df_loss = perdidos.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
        df_loss["Percentual"] = (df_loss["Qtd"] / total * 100).round(1) if total > 0 else 0
        df_loss["Label"] = df_loss.apply(lambda x: f"{int(x['Qtd'])}<br>({x['Percentual']}%)", axis=1)
        
        fig_loss = px.bar(df_loss, x="Etapa", y="Qtd", text="Label", color="Qtd", color_continuous_scale="Blues")
        fig_loss.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
        st.plotly_chart(fig_loss, use_container_width=True)

# =========================
# APP MAIN
# =========================
st.markdown('<div class="futuristic-title">🕰️ Máquina do Tempo</div>', unsafe_allow_html=True)

# 1. CARREGAR METADADOS DO BANCO
with st.spinner("Conectando ao banco de dados..."):
    client = conectar_google()
    df_db = pd.DataFrame()
    
    if client:
        try:
            sh = client.open("BI_Historico")
            ws = sh.worksheet("db_snapshots")
            dados = ws.get_all_values()
            
            if len(dados) > 1 and 'snapshot_id' in dados[0]:
                df_db = pd.DataFrame(dados[1:], columns=dados[0])
            else:
                st.warning("⚠️ Banco vazio. Vá na Home e salve um arquivo.")
                st.stop()
        except Exception as e:
            st.error(f"Erro: {e}")
            st.stop()

# 2. SISTEMA DE FILTRAGEM ROBUSTA (CASCATA)
if not df_db.empty:
    st.sidebar.header("🗂️ Filtros de Busca")
    
    # Preparação de Dados para Filtro (Extraindo Ano/Mes)
    # Formato esperado data_salvamento: "04/01/2026 20:30"
    df_db['data_dt'] = pd.to_datetime(df_db['data_salvamento'], dayfirst=True, errors='coerce')
    df_db['Ano'] = df_db['data_dt'].dt.year
    df_db['Mes'] = df_db['data_dt'].dt.month_name()
    
    # Garantir que colunas de filtro existam
    if 'marca_ref' not in df_db.columns: df_db['marca_ref'] = 'Geral'
    if 'semana_ref' not in df_db.columns: df_db['semana_ref'] = 'N/A'
    
    # --- FILTRO 1: MARCA ---
    marcas_disp = sorted(df_db['marca_ref'].unique())
    f_marca = st.sidebar.selectbox("1. Selecione a Marca", marcas_disp)
    
    df_f1 = df_db[df_db['marca_ref'] == f_marca]
    
    # --- FILTRO 2: ANO ---
    anos_disp = sorted(df_f1['Ano'].dropna().unique(), reverse=True)
    if len(anos_disp) > 0:
        f_ano = st.sidebar.selectbox("2. Selecione o Ano", anos_disp)
        df_f2 = df_f1[df_f1['Ano'] == f_ano]
    else:
        st.sidebar.warning("Sem dados de ano.")
        df_f2 = df_f1
        
    # --- FILTRO 3: MÊS ---
    meses_disp = df_f2['Mes'].unique()
    if len(meses_disp) > 0:
        f_mes = st.sidebar.selectbox("3. Selecione o Mês", meses_disp)
        df_f3 = df_f2[df_f2['Mes'] == f_mes]
    else:
        df_f3 = df_f2
        
    # --- FILTRO 4: VERSÃO/ARQUIVO (SNAPSHOT FINAL) ---
    # Mostra a semana e a hora exata para diferenciar salvamentos
    if not df_f3.empty:
        df_f3['Label_Select'] = df_f3['semana_ref'] + " | Salvo em: " + df_f3['data_salvamento']
        
        # Agrupamos por ID para não repetir linhas no selectbox (uma opção por snapshot)
        opcoes_finais = df_f3[['snapshot_id', 'Label_Select']].drop_duplicates().sort_values('snapshot_id', ascending=False)
        
        f_snapshot = st.sidebar.selectbox("4. Escolha o Arquivo", options=opcoes_finais['Label_Select'])
        
        # --- CARREGAR DADOS ---
        if f_snapshot:
            id_escolhido = opcoes_finais[opcoes_finais['Label_Select'] == f_snapshot]['snapshot_id'].values[0]
            
            # Filtra e Copia
            df_recuperado = df_db[df_db['snapshot_id'] == id_escolhido].copy()
            
            # Limpeza
            cols_tec = ['snapshot_id', 'data_salvamento', 'semana_ref', 'marca_ref', 'Ano', 'Mes', 'Label_Select', 'data_dt']
            df_visual = df_recuperado.drop(columns=[c for c in cols_tec if c in df_recuperado.columns])
            
            # Processamento Final
            df_final = processar_snapshot(df_visual)
            
            st.divider()
            
            # Cabeçalho Informativo
            st.markdown(f"""
            <div style="background: rgba(34, 211, 238, 0.1); padding: 15px; border-radius: 10px; border-left: 4px solid #22d3ee; margin-bottom: 20px;">
                <h3 style="margin:0; font-family:'Rajdhani'; color: #22d3ee;">ARQUIVO CARREGADO: {f_snapshot}</h3>
                <p style="margin:0; color: #94a3b8;">Visualizando dados estáticos do passado.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # --- RENDERIZA O DASHBOARD COMPLETO ---
            render_dashboard(df_final)
            
            with st.expander("📂 Ver Tabela de Dados Brutos"):
                st.dataframe(df_final)
    else:
        st.sidebar.warning("Nenhum arquivo encontrado para esses filtros.")
