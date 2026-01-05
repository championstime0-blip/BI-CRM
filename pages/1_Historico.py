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
# ESTILIZAÇÃO CSS (CÓPIA EXATA DA HOME)
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
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1; border-radius: 8px; padding: 20px 30px;
    margin-bottom: 15px; margin-top: 10px; display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.profile-group { display: flex; flex-direction: column; }
.profile-label { color: #94a3b8; font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 4px; }
.profile-value { color: #f8fafc; font-size: 24px; font-weight: 600; font-family: 'Rajdhani', sans-serif; }
.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }
.date-card { background: rgba(15, 23, 42, 0.4); border: 1px solid #334155; border-radius: 12px; padding: 12px; text-align: center; margin-bottom: 30px; }
.date-label { font-family: 'Rajdhani', sans-serif; font-size: 13px; text-transform: uppercase; letter-spacing: 2px; color: #64748b; margin-bottom: 2px; }
.date-value { font-family: 'Orbitron', sans-serif; font-size: 18px; color: #94a3b8; letter-spacing: 1px; }
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
# UTILS VISUAIS
# =========================
ETAPAS_FUNIL = ["Sem contato", "Aguardando Resposta", "Confirmou Interesse", "Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]

def card(title, value):
    st.markdown(f'<div class="card"><div class="card-title">{title}</div><div class="card-value">{value}</div></div>', unsafe_allow_html=True)

def subheader_futurista(icon, text):
    st.markdown(f'<div class="futuristic-sub"><span class="sub-icon">{icon}</span>{text}</div>', unsafe_allow_html=True)

def processar_snapshot(df):
    # Recalcula Status e Data
    def status(row):
        etapa_lower = str(row["Etapa"]).lower() if "Etapa" in row else ""
        motivo = str(row["Motivo de Perda"]).strip().lower() if "Motivo de Perda" in row else ""
        if any(x in etapa_lower for x in ["faturado", "ganho", "venda"]): return "Ganho"
        if motivo not in ["", "nan", "none", "-", "nan", "0", "nada", "n/a"]: return "Perdido"
        return "Em Andamento"
    
    if "Status" not in df.columns:
        df["Status"] = df.apply(status, axis=1)
        
    # Converter Data de Criação para DateTime real (para o recorte temporal)
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], errors='coerce')
        
    if "Fonte" in df.columns:
        df["Fonte"] = df["Fonte"].fillna("Desconhecido").astype(str)
        
    return df

# =========================
# RENDERIZADOR COMPLETO (IDÊNTICO À HOME)
# =========================
def render_dashboard_completo(df):
    # 1. HEADER (RESPONSÁVEL E EQUIPE)
    resp = df["Responsável"].mode()[0] if "Responsável" in df.columns and not df["Responsável"].empty else "N/A"
    
    equipe = "N/A"
    if "Equipe" in df.columns and not df["Equipe"].empty:
         equipe_raw = str(df["Equipe"].mode()[0])
         if "Prepara" in equipe_raw: equipe = "Expansão Prepara"
         elif "Microlins" in equipe_raw: equipe = "Expansão Microlins"
         elif "Ensina" in equipe_raw: equipe = "Expansão Ensina Mais"
         else: equipe = equipe_raw
    elif "marca_ref" in df.columns:
         equipe = f"Expansão {df['marca_ref'].iloc[0]}"

    st.markdown(f"""
    <div class="profile-header">
        <div class="profile-group"><span class="profile-label">Responsável</span><span class="profile-value">{resp}</span></div>
        <div class="profile-divider"></div>
        <div class="profile-group"><span class="profile-label">Equipe</span><span class="profile-value">{equipe}</span></div>
    </div>""", unsafe_allow_html=True)
    
    # 2. DATA CARD (RECORTE TEMPORAL)
    if "Data de Criação" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Data de Criação"]):
        d_min = df["Data de Criação"].min()
        d_max = df["Data de Criação"].max()
        if pd.notnull(d_min) and pd.notnull(d_max):
            d_str = f"{d_min.strftime('%d/%m/%Y')} ➔ {d_max.strftime('%d/%m/%Y')}"
            st.markdown(f'<div class="date-card"><div class="date-label">📅 Recorte Temporal do Arquivo</div><div class="date-value">{d_str}</div></div>', unsafe_allow_html=True)

    # 3. KPIs TOPO
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    
    c1, c2 = st.columns(2)
    with c1: card("Leads Totais", total)
    with c2: card("Leads em Andamento", len(em_andamento))
    st.divider()

    # 4. GRÁFICOS CENTRAIS
    col_mkt, col_funil = st.columns(2)
    
    # Marketing
    with col_mkt:
        subheader_futurista("📡", "MARKETING & FONTES")
        if "Fonte" in df.columns:
            df_fonte = df["Fonte"].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=['#22d3ee', '#06b6d4', '#0891b2', '#155e75'])
            fig_pie.update_traces(textposition='outside', textinfo='percent+label')
            fig_pie.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.markdown('<div class="futuristic-sub" style="font-size:18px; margin-top:20px; border:none;"><span class="sub-icon">🏆</span>TOP 3 CANAIS DE AQUISIÇÃO</div>', unsafe_allow_html=True)
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

    # Funil
    with col_funil:
        subheader_futurista("📉", "DESCIDA DE FUNIL")
        if "Etapa" in df.columns:
            df_funil = df.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
            df_funil["Percentual"] = (df_funil["Qtd"] / total * 100).round(1) if total > 0 else 0
            
            # Taxa Avanço
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
                <div class="funnel-label">🚀 Taxa de Avanço Real de Funil</div>
                <div class="funnel-percent">{taxa_avanco:.1f}%</div>
                <div class="funnel-sub">Leads Qualificados+ / (Total - Sem Resposta)</div>
            </div>''', unsafe_allow_html=True)
        else:
            st.warning("Dados de Etapa indisponíveis.")

    # 5. DETALHE DAS PERDAS
    st.divider()
    subheader_futurista("🚫", "DETALHE DAS PERDAS")
    k1, k2 = st.columns(2)
    with k1: card("Total Perdido", len(perdidos))
    with k2: card("Perda: Aguardando s/ Resp.", len(perda_especifica) if "Motivo de Perda" in df.columns else 0)
    
    st.write("")
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

with st.spinner("Sincronizando com o banco de dados..."):
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
                st.warning("⚠️ Banco de dados vazio. Salve um arquivo na Home.")
                st.stop()
        except Exception as e:
            st.error(f"Erro: {e}")
            st.stop()

# =========================
# SISTEMA DE FILTRO EM CASCATA (DRILL-DOWN)
# =========================
if not df_db.empty:
    st.sidebar.header("🗂️ Filtros de Busca")
    
    # 1. Preparar Colunas Auxiliares para Filtro
    df_db['data_dt'] = pd.to_datetime(df_db['data_salvamento'], dayfirst=True, errors='coerce')
    df_db['Ano_Filtro'] = df_db['data_dt'].dt.year.fillna(0).astype(int)
    # Mes em Português para ficar bonito
    meses_pt = {1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril", 5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto", 9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"}
    df_db['Mes_Filtro'] = df_db['data_dt'].dt.month.map(meses_pt)
    
    if 'marca_ref' not in df_db.columns: df_db['marca_ref'] = 'Geral'
    
    # --- NIVEL 1: MARCA ---
    marcas_disp = sorted(df_db['marca_ref'].unique())
    f_marca = st.sidebar.selectbox("1. Marca", marcas_disp)
    df_f1 = df_db[df_db['marca_ref'] == f_marca]
    
    # --- NIVEL 2: ANO ---
    anos_disp = sorted(df_f1['Ano_Filtro'].unique(), reverse=True)
    if len(anos_disp) > 0:
        f_ano = st.sidebar.selectbox("2. Ano", anos_disp)
        df_f2 = df_f1[df_f1['Ano_Filtro'] == f_ano]
    else:
        df_f2 = df_f1

    # --- NIVEL 3: MÊS ---
    meses_disp = df_f2['Mes_Filtro'].unique()
    if len(meses_disp) > 0:
        f_mes = st.sidebar.selectbox("3. Mês", meses_disp)
        df_f3 = df_f2[df_f2['Mes_Filtro'] == f_mes]
    else:
        df_f3 = df_f2

    # --- NIVEL 4: SEMANA (ARQUIVO FINAL) ---
    if not df_f3.empty:
        # Cria label bonito: "Semana 1 (Salvo em 04/01 às 14:00)"
        df_f3['Label_Select'] = df_f3['semana_ref'] + " | " + df_f3['data_salvamento']
        
        # Remove duplicatas de ID (mostra apenas uma opção por snapshot)
        opcoes = df_f3[['snapshot_id', 'Label_Select']].drop_duplicates().sort_values('snapshot_id', ascending=False)
        
        f_arquivo = st.sidebar.selectbox("4. Arquivo (Snapshot)", opcoes['Label_Select'])
        
        # --- CARREGAR E RENDERIZAR ---
        if f_arquivo:
            id_snap = opcoes[opcoes['Label_Select'] == f_arquivo]['snapshot_id'].values[0]
            
            # Filtra e Limpa
            df_recuperado = df_db[df_db['snapshot_id'] == id_snap].copy()
            cols_tec = ['snapshot_id', 'data_salvamento', 'semana_ref', 'marca_ref', 'Ano_Filtro', 'Mes_Filtro', 'Label_Select', 'data_dt']
            df_visual = df_recuperado.drop(columns=[c for c in cols_tec if c in df_recuperado.columns])
            
            # Processa e Renderiza
            df_final = processar_snapshot(df_visual)
            
            st.divider()
            render_dashboard_completo(df_final)
            
            with st.expander("🔍 Ver Dados Brutos"):
                st.dataframe(df_final)
    else:
        st.sidebar.warning("Nenhum arquivo encontrado para esta combinação.")
