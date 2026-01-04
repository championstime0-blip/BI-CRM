import streamlit as st
import pandas as pd
import plotly.express as px

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="BI CRM Expansão", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (NEON/DARK + FONTE FUTURISTA)
# =========================
st.markdown("""
<style>
/* Importando Fonte Sci-Fi */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');

/* Fundo Geral */
.stApp { background-color: #0b0f1a; color: #e0e0e0; }

/* --- TÍTULO PRINCIPAL (H1) --- */
.futuristic-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 56px;
    font-weight: 900;
    text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #818cf8 50%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: 3px;
    margin-bottom: 10px;
    text-shadow: 0 0 30px rgba(34, 211, 238, 0.3);
}

/* --- SUBTÍTULOS (H2) --- */
.futuristic-sub {
    font-family: 'Rajdhani', sans-serif;
    font-size: 24px;
    font-weight: 700;
    text-transform: uppercase;
    color: #e2e8f0;
    letter-spacing: 2px;
    border-bottom: 1px solid #1e293b;
    padding-bottom: 8px;
    margin-top: 30px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
}

.sub-icon {
    margin-right: 12px;
    font-size: 24px;
    color: #22d3ee; /* Cyan Neon */
    text-shadow: 0 0 10px rgba(34, 211, 238, 0.6);
}

/* --- CARD DE PERFIL (CLEAN TECH) --- */
.profile-header {
    background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
    border-left: 5px solid #6366f1;
    border-radius: 8px;
    padding: 20px 30px;
    margin-bottom: 15px;
    margin-top: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.profile-group { display: flex; flex-direction: column; }

.profile-label {
    color: #94a3b8;
    font-family: 'Rajdhani', sans-serif;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 4px;
}

.profile-value {
    color: #f8fafc;
    font-size: 24px;
    font-weight: 600;
    font-family: 'Rajdhani', sans-serif;
}

.profile-divider { width: 1px; height: 40px; background-color: #334155; margin: 0 20px; }

/* Estilo dos Cards de KPI (Neon) */
.card {
    background: linear-gradient(135deg, #111827, #020617);
    padding: 24px;
    border-radius: 16px;
    border: 1px solid #1e293b;
    text-align: center;
    box-shadow: 0 0 15px rgba(56,189,248,0.05);
    transition: all 0.3s ease;
    height: 100%;
}
.card:hover {
    box-shadow: 0 0 25px rgba(56,189,248,0.2);
    border-color: #38bdf8;
    transform: translateY(-2px);
}
.card-title {
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
    min-height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.card-value {
    font-family: 'Orbitron', sans-serif;
    font-size: 36px;
    font-weight: 700;
    background: -webkit-linear-gradient(45deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* --- Card de Recorte de Data --- */
.date-card {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px;
    text-align: center;
    margin-bottom: 30px;
}
.date-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #64748b;
    margin-bottom: 2px;
}
.date-value {
    font-family: 'Orbitron', sans-serif; /* Fonte Tech para números */
    font-size: 18px;
    color: #94a3b8;
    letter-spacing: 1px;
}

/* --- Card de Avanço de Funil --- */
.funnel-card {
    background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
    border-top: 2px solid #22d3ee;
    border-radius: 0 0 12px 12px;
    padding: 15px;
    text-align: center;
    margin-top: -10px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}
.funnel-label {
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 1.2px;
}
.funnel-percent {
    font-family: 'Orbitron', sans-serif;
    font-size: 32px;
    font-weight: 700;
    color: #22d3ee;
    margin: 5px 0;
}
.funnel-sub { font-size: 10px; color: #64748b; font-style: italic; }

/* --- TOP 3 FONTES --- */
.top-source-container { margin-top: 25px; padding: 0; }
.top-item {
    border-left: 3px solid #22d3ee; 
    padding: 12px 15px;
    margin-bottom: 8px;
    border-radius: 0 8px 8px 0;
    display: flex; align-items: center; justify-content: space-between;
    transition: transform 0.2s;
    border: 1px solid rgba(34, 211, 238, 0.1); border-left-width: 3px;
}
.top-item:hover { transform: translateX(5px); border-color: rgba(34, 211, 238, 0.3); }
.top-rank { 
    font-family: 'Orbitron', sans-serif; 
    font-weight: 900; color: #22d3ee; font-size: 16px; margin-right: 12px; min-width: 25px; 
}
.top-name { 
    font-family: 'Rajdhani', sans-serif;
    color: #f1f5f9; font-weight: 600; font-size: 15px; 
    flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-right: 10px;
}
.top-val-abs { 
    color: #fff; font-weight: bold; font-size: 14px; display: block; 
}
.top-val-pct { color: #94a3b8; font-size: 10px; font-weight: 400; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONSTANTES
# =========================
ETAPAS_FUNIL = [
    "Sem contato",
    "Aguardando Resposta",
    "Confirmou Interesse",
    "Qualificado",
    "Reunião Agendada",
    "Reunião Realizada",
    "Follow-up",
    "negociação",
    "em aprovação",
    "faturado"
]

MARCAS = ["PreparaIA", "Microlins", "Ensina Mais 1", "Ensina Mais 2"]

# =========================
# FUNÇÕES VISUAIS
# =========================
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

# =========================
# MOTOR BLINDADO
# =========================
def load_csv(file):
    raw = file.read().decode("latin-1", errors="ignore")
    sep = ";" if raw.count(";") > raw.count(",") else ","
    file.seek(0)
    return pd.read_csv(file, sep=sep, engine="python", on_bad_lines="skip")

def processar(df):
    df.columns = df.columns.str.strip()
    cols_map = {c: c for c in df.columns}
    for c in df.columns:
        c_lower = c.lower()
        if c_lower in ["fonte", "origem", "source", "conversion origin", "origem do lead"]:
            cols_map[c] = "Fonte"
        if c_lower in ["data de criação", "data da criação", "created date"]:
            cols_map[c] = "Data de Criação"
        if c_lower in ["dono do lead", "responsável", "responsavel", "owner"]:
            cols_map[c] = "Responsável"
        if c_lower in ["equipe", "equipe do dono do lead", "team"]:
            cols_map[c] = "Equipe"
    df = df.rename(columns=cols_map)
    df["Etapa"] = df["Etapa"].astype(str).str.strip()
    df["Motivo de Perda"] = df.get("Motivo de Perda", "").astype(str)
    if "Data de Criação" in df.columns:
        df["Data de Criação"] = pd.to_datetime(df["Data de Criação"], dayfirst=True, errors='coerce')
    
    def status(row):
        etapa_lower = row["Etapa"].lower()
        if "faturado" in etapa_lower or "ganho" in etapa_lower or "venda" in etapa_lower:
            return "Ganho"
        motivo = row["Motivo de Perda"].strip().lower()
        if motivo not in ["", "nan", "none", "-", "nan"]:
            return "Perdido"
        return "Em Andamento"
    df["Status"] = df.apply(status, axis=1)
    return df

# =========================
# DASHBOARD
# =========================
def dashboard(df, marca):
    total = len(df)
    perdidos = df[df["Status"] == "Perdido"]
    em_andamento = df[df["Status"] == "Em Andamento"]
    perda_especifica = df[
        (df["Etapa"].str.strip() == "Aguardando Resposta") &
        (df["Motivo de Perda"].str.lower().str.contains("sem resposta", na=False))
    ]

    # --- KPIs ---
    c1, c2 = st.columns(2)
    with c1: card("Leads Totais", total)
    with c2: card("Leads em Andamento", len(em_andamento))

    st.divider()

    # --- GRÁFICOS ---
    col_mkt, col_funil = st.columns(2)

    # 1. Marketing
    with col_mkt:
        # TÍTULO AJUSTADO
        subheader_futurista("📡", "MARKETING & FONTES")
        
        possible_cols = ["Fonte", "Origem", "Source", "Conversion Origin"]
        col_fonte = next((c for c in df.columns if c in possible_cols), None)

        if col_fonte:
            df_fonte = df[col_fonte].value_counts().reset_index()
            df_fonte.columns = ["Fonte", "Qtd"]
            neon_palette = ['#22d3ee', '#06b6d4', '#0891b2', '#164e63', '#67e8f9']
            fig_pie = px.pie(df_fonte, values='Qtd', names='Fonte', hole=0.6, color_discrete_sequence=neon_palette)
            fig_pie.update_traces(textposition='outside', textinfo='percent+label', marker=dict(line=dict(color='#0b0f1a', width=3)))
            fig_pie.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

            # TOP 3 Renderizado
            st.markdown('<div class="futuristic-sub" style="font-size:18px; margin-top:20px; border:none;"><span class="sub-icon">🏆</span>TOP 3 CANAIS DE AQUISIÇÃO</div>', unsafe_allow_html=True)
            
            top3 = df_fonte.head(3)
            max_val = top3['Qtd'].max() if not top3.empty else 1
            html_content = '<div class="top-source-container">'
            for i, row in top3.iterrows():
                rank = i + 1
                nome = row['Fonte']
                qtd = row['Qtd']
                bar_width = (qtd / max_val) * 100
                pct_total = (qtd / total * 100)
                bg_style = f"background: linear-gradient(90deg, rgba(34, 211, 238, 0.15) {bar_width}%, rgba(15, 23, 42, 0.0) {bar_width}%);"
                
                item_html = f'<div class="top-item" style="{bg_style}">'
                item_html += f'<div style="display:flex; align-items:center; width: 70%;">'
                item_html += f'<span class="top-rank">#{rank}</span>'
                item_html += f'<span class="top-name" title="{nome}">{nome}</span>'
                item_html += f'</div>'
                item_html += f'<div class="top-val-group">'
                item_html += f'<span class="top-val-abs">{qtd}</span>'
                item_html += f'<span class="top-val-pct">{pct_total:.1f}% do total</span>'
                item_html += f'</div></div>'
                html_content += item_html
            html_content += '</div>'
            st.markdown(html_content, unsafe_allow_html=True)
        else:
            st.info("Coluna de 'Fonte' não identificada.")

    # 2. Funil
    with col_funil:
        # TÍTULO AJUSTADO
        subheader_futurista("📉", "DESCIDA DE FUNIL")

        df_funil = df.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
        df_funil["Percentual"] = (df_funil["Qtd"] / total * 100).round(1)
        fig_funil = px.bar(df_funil, x="Qtd", y="Etapa", orientation="h", text=df_funil["Percentual"].astype(str) + "%", color="Qtd", color_continuous_scale="Blues")
        fig_funil.update_layout(template="plotly_dark", showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title="Volume", yaxis_title="")
        st.plotly_chart(fig_funil, use_container_width=True)

        etapas_avanco = ["Qualificado", "Reunião Agendada", "Reunião Realizada", "Follow-up", "negociação", "em aprovação", "faturado"]
        df['Etapa_Clean'] = df['Etapa'].str.strip()
        qtd_avancados = len(df[df['Etapa_Clean'].isin(etapas_avanco)])
        qtd_sem_resposta = len(perda_especifica)
        base_calculo = total - qtd_sem_resposta
        perc_avanco = (qtd_avancados / base_calculo * 100) if base_calculo > 0 else 0

        st.markdown(f"""
        <div class="funnel-card">
            <div class="funnel-label">🚀 Taxa de Avanço Real de Funil</div>
            <div class="funnel-percent">{perc_avanco:.1f}%</div>
            <div class="funnel-sub">Leads Qualificados+ / (Total - Sem Resposta)</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # 3. Perdas
    # TÍTULO AJUSTADO
    subheader_futurista("🚫", "DETALHE DAS PERDAS")
    
    kpi_loss1, kpi_loss2 = st.columns(2)
    with kpi_loss1: card("Leads Improdutivos (Total Perdido)", len(perdidos))
    with kpi_loss2: card("Perda: Aguardando s/ Resp.", len(perda_especifica))

    st.write("") 

    df_loss = perdidos.groupby("Etapa").size().reindex(ETAPAS_FUNIL).fillna(0).reset_index(name="Qtd")
    df_loss["Percentual"] = (df_loss["Qtd"] / total * 100).round(1)
    df_loss["Label"] = df_loss.apply(lambda x: f"{int(x['Qtd'])}<br>({x['Percentual']}%)", axis=1)

    fig_loss = px.bar(df_loss, x="Etapa", y="Qtd", text="Label", color="Qtd", color_continuous_scale="Blues", title="")
    fig_loss.update_traces(textposition='outside', marker_line_color='#22d3ee', marker_line_width=1, opacity=0.9, textfont_size=12)
    fig_loss.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=False, xaxis_title="", yaxis_title="Leads Perdidos", yaxis=dict(showgrid=False), height=500)
    st.plotly_chart(fig_loss, use_container_width=True)

# =========================
# APP MAIN
# =========================
# TÍTULO PRINCIPAL (H1) ATUALIZADO
st.markdown('<div class="futuristic-title">💠 BI CRM Expansão</div>', unsafe_allow_html=True)

marca = st.selectbox("Selecione a Marca", MARCAS)
arquivo = st.file_uploader("Upload CSV RD Station", type=["csv"])

if arquivo:
    try:
        df = load_csv(arquivo)
        df = processar(df)

        resp_val = df["Responsável"].mode()[0] if "Responsável" in df.columns and not df["Responsável"].empty else "Não Identificado"
        equipe_raw = df["Equipe"].mode()[0] if "Equipe" in df.columns and not df["Equipe"].empty else "Geral"
        equipe_val = "Expansão Ensina Mais" if equipe_raw in ["Geral", "", "nan"] else equipe_raw

        st.markdown(f"""
        <div class="profile-header">
            <div class="profile-group">
                <span class="profile-label">Responsável</span>
                <span class="profile-value">{resp_val}</span>
            </div>
            <div class="profile-divider"></div>
            <div class="profile-group">
                <span class="profile-label">Equipe do Responsável</span>
                <span class="profile-value">{equipe_val}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if "Data de Criação" in df.columns and not df["Data de Criação"].isnull().all():
            min_date = df["Data de Criação"].min().strftime('%d/%m/%Y')
            max_date = df["Data de Criação"].max().strftime('%d/%m/%Y')
            st.markdown(f"""
            <div class="date-card">
                <div class="date-label">📅 Recorte Temporal da Base</div>
                <div class="date-value">
                    {min_date} <span style="color:#64748b; padding:0 10px;">➔</span> {max_date}
                </div>
            </div>
            """, unsafe_allow_html=True)

        dashboard(df, marca)
    except Exception as e:
        st.error("Erro ao processar o arquivo")
        st.exception(e)
