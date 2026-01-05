import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
from datetime import datetime

# =========================
# CONFIGURAÇÃO DA PÁGINA
# =========================
st.set_page_config(page_title="Previsão de Vendas", layout="wide")

# =========================
# ESTILIZAÇÃO CSS (PREMIUM)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;600;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }

/* Títulos */
.futuristic-header {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #a855f7 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(34, 211, 238, 0.4); margin-bottom: 20px;
}

/* Card de Marca no Topo */
.brand-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-left: 5px solid #22d3ee;
    border-radius: 8px; padding: 20px; margin-bottom: 25px;
    box-shadow: 0 4px 15px rgba(34, 211, 238, 0.15);
    display: flex; align-items: center; justify-content: center;
}
.brand-name {
    font-family: 'Orbitron'; font-size: 32px; color: #fff; text-transform: uppercase; letter-spacing: 2px;
}

/* Cards de KPI */
.kpi-card {
    background: linear-gradient(135deg, #1e293b, #111827); border: 1px solid #334155;
    padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    transition: transform 0.2s;
}
.kpi-card:hover { transform: translateY(-3px); border-color: #22d3ee; }
.kpi-val { font-family: 'Orbitron'; font-size: 28px; color: #4ade80; margin-top: 5px; }
.kpi-val-loss { font-family: 'Orbitron'; font-size: 28px; color: #f87171; margin-top: 5px; } /* Vermelho para perda */
.kpi-val-wait { font-family: 'Orbitron'; font-size: 28px; color: #fbbf24; margin-top: 5px; } /* Amarelo para espera */
.kpi-lbl { font-family: 'Rajdhani'; font-size: 14px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }

/* Ajuste na Tabela Editável */
div[data-testid="stDataEditor"] { 
    border: 1px solid #334155; border-radius: 8px; overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================
COLUNAS_PADRAO = ["Consultor", "Lead", "Cidade", "Campanha", "Marca", "Valor", "Data_Registro"]
PLANILHA_NOME = "BI_Historico"

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
    except: return None

# =========================
# FUNÇÕES DE BANCO DE DADOS
# =========================
def carregar_aba(nome_aba):
    client = conectar_google()
    if not client: return pd.DataFrame(columns=COLUNAS_PADRAO)
    try:
        sh = client.open(PLANILHA_NOME)
        try: ws = sh.worksheet(nome_aba)
        except: 
            ws = sh.add_worksheet(nome_aba, 1000, 20)
            ws.append_row(COLUNAS_PADRAO)
            return pd.DataFrame(columns=COLUNAS_PADRAO)

        dados = ws.get_all_values()
        if not dados: return pd.DataFrame(columns=COLUNAS_PADRAO)

        # Tratamento de Cabeçalho Flexível
        header = [h.strip() for h in dados[0]]
        if "Consultor" in header and "Valor" in header:
            df = pd.DataFrame(dados[1:], columns=header)
        else:
            # Se não tem cabeçalho, assume que é dado e usa padrão
            if len(dados[0]) >= len(COLUNAS_PADRAO):
                 if dados[0][0] == "Consultor": 
                     df = pd.DataFrame(dados[1:], columns=COLUNAS_PADRAO)
                 else:
                     df = pd.DataFrame(dados, columns=COLUNAS_PADRAO)
            else:
                 return pd.DataFrame(columns=COLUNAS_PADRAO)

        # Limpeza Numérica
        if 'Valor' in df.columns:
            df['Valor'] = df['Valor'].astype(str).str.replace('R$', '', regex=False).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0.0)
            
        return df
    except: return pd.DataFrame(columns=COLUNAS_PADRAO)

def salvar_full(nome_aba, df):
    client = conectar_google()
    sh = client.open(PLANILHA_NOME)
    try: ws = sh.worksheet(nome_aba)
    except: ws = sh.add_worksheet(nome_aba, 1000, 20)
    ws.clear()
    df_save = df.copy().astype(str)
    ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())

def adicionar_lead(dados):
    client = conectar_google()
    sh = client.open(PLANILHA_NOME)
    try: ws = sh.worksheet("previsao_ativa")
    except: ws = sh.add_worksheet("previsao_ativa", 1000, 20)
    
    vals = ws.get_all_values()
    if not vals: ws.append_row(COLUNAS_PADRAO)
    elif vals[0][0] != "Consultor": ws.insert_row(COLUNAS_PADRAO, 1)
    
    ws.append_row(dados)

# =========================
# BARRA LATERAL (Cadastro)
# =========================
st.sidebar.markdown("### 📝 Nova Previsão")
with st.sidebar.form("form_add"):
    marcas_opts = ["Microlins", "PreparaIA", "Ensina Mais 1", "Ensina Mais 2"]
    
    f_consultor = st.text_input("Consultor")
    f_lead = st.text_input("Nome do Lead")
    f_cidade = st.text_input("Cidade")
    f_campanha = st.text_input("Campanha")
    f_marca = st.selectbox("Marca", marcas_opts)
    f_valor = st.number_input("Valor Previsto (R$)", min_value=0.0, step=100.0)
    
    if st.form_submit_button("💾 Cadastrar"):
        if f_lead and f_consultor:
            dados = [f_consultor, f_lead, f_cidade, f_campanha, f_marca, f_valor, datetime.now().strftime("%d/%m/%Y")]
            adicionar_lead(dados)
            st.success("Cadastrado!")
            st.rerun()
        else: st.error("Preencha Consultor e Lead.")

# =========================
# PAINEL PRINCIPAL
# =========================
st.markdown('<div class="futuristic-header">🔮 Painel de Previsão de Vendas</div>', unsafe_allow_html=True)

# 1. Filtro Global
col_filter, _ = st.columns([1, 2])
with col_filter:
    filtro_marca = st.selectbox("Filtrar Visão por Marca:", ["TODAS"] + marcas_opts)

# 2. CARD DE CABEÇALHO (O PEDIDO DO USUÁRIO)
if filtro_marca != "TODAS":
    st.markdown(f"""
    <div class="brand-banner">
        <div class="brand-name">{filtro_marca}</div>
    </div>
    """, unsafe_allow_html=True)

# Carregar Dados
df_ativos = carregar_aba("previsao_ativa")
df_prorrog = carregar_aba("prorrogacao")
df_desist = carregar_aba("desistencia")

def filtrar(df):
    if filtro_marca != "TODAS" and not df.empty and "Marca" in df.columns:
        return df[df["Marca"] == filtro_marca]
    return df

# ABAS
tab1, tab2, tab3 = st.tabs(["🎯 Previsão Ativa", "⏳ Prorrogações", "🚫 Desistências"])

# --- TAB 1: ATIVOS ---
with tab1:
    df_view = filtrar(df_ativos)
    total_prev = df_view['Valor'].sum() if not df_view.empty else 0.0
    
    # KPI
    col_k1, col_k2, _ = st.columns([1, 1, 2])
    with col_k1: st.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Pipeline Ativo</div><div class="kpi-val">R$ {total_prev:,.2f}</div></div>', unsafe_allow_html=True)
    with col_k2: st.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Leads na Mesa</div><div class="kpi-val">{len(df_view)}</div></div>', unsafe_allow_html=True)
    
    st.divider()

    if not df_ativos.empty:
        df_ativos['Ação'] = "Manter" # Valor padrão
        
        # Configuração VISUAL AMIGÁVEL da Tabela
        col_conf = {
            "Valor": st.column_config.NumberColumn(
                "Valor Previsto", 
                format="R$ %.2f", 
                min_value=0, 
                help="Valor estimado de fechamento"
            ),
            "Ação": st.column_config.SelectboxColumn(
                "O que fazer?",
                options=["Manter", "Prorrogar", "Desistência"],
                required=True,
                width="medium",
                help="Mude para mover o lead de aba"
            ),
            "Marca": st.column_config.TextColumn("Marca", width="small", disabled=True),
            "Lead": st.column_config.TextColumn("Nome do Lead", width="medium"),
            "Consultor": st.column_config.TextColumn("Consultor", width="small"),
            "Cidade": st.column_config.TextColumn("Cidade", width="small"),
            "Campanha": st.column_config.TextColumn("Campanha", width="small"),
            "Data_Registro": st.column_config.TextColumn("Data", disabled=True, width="small")
        }
        
        df_editado = st.data_editor(
            df_view if filtro_marca != "TODAS" else df_ativos,
            column_config=col_conf,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_ativos"
        )
        
        if st.button("⚡ Processar Alterações", type="primary"):
            with st.spinner("Processando..."):
                prorrogados = df_editado[df_editado['Ação'] == 'Prorrogar']
                desistentes = df_editado[df_editado['Ação'] == 'Desistência']
                mantidos = df_editado[df_editado['Ação'] == 'Manter']
                
                # Salvar Ativos (Concatenando com o que estava oculto pelo filtro)
                if filtro_marca != "TODAS":
                    ocultos = df_ativos[df_ativos['Marca'] != filtro_marca]
                    df_final = pd.concat([ocultos, mantidos[COLUNAS_PADRAO]])
                else:
                    df_final = mantidos[COLUNAS_PADRAO]
                salvar_full("previsao_ativa", df_final)
                
                # Salvar Prorrogações
                if not prorrogados.empty:
                    df_p = carregar_aba("prorrogacao")
                    prorrogados = prorrogados.assign(Data_Movimento=datetime.now().strftime("%d/%m/%Y"))
                    cols_p = COLUNAS_PADRAO + ['Data_Movimento']
                    df_p_novo = pd.concat([df_p, prorrogados[cols_p]]) if not df_p.empty else prorrogados[cols_p]
                    salvar_full("prorrogacao", df_p_novo)

                # Salvar Desistências
                if not desistentes.empty:
                    df_d = carregar_aba("desistencia")
                    desistentes = desistentes.assign(Data_Movimento=datetime.now().strftime("%d/%m/%Y"))
                    cols_d = COLUNAS_PADRAO + ['Data_Movimento']
                    df_d_novo = pd.concat([df_d, desistentes[cols_d]]) if not df_d.empty else desistentes[cols_d]
                    salvar_full("desistencia", df_d_novo)

                st.success("Atualizado!")
                st.rerun()
    else:
        st.info("Sua lista de previsão está vazia. Comece cadastrando na barra lateral!")

# --- TAB 2: PRORROGAÇÕES ---
with tab2:
    df_view_p = filtrar(df_prorrog)
    total_prorrog = df_view_p['Valor'].sum() if not df_view_p.empty else 0.0
    
    # KPI FINANCEIRO PRORROGAÇÃO
    st.markdown(f'<div class="kpi-card" style="border-color: #fbbf24;"><div class="kpi-lbl">Total em Stand-by</div><div class="kpi-val-wait">R$ {total_prorrog:,.2f}</div></div>', unsafe_allow_html=True)
    st.write("")
    
    if not df_view_p.empty:
        df_view_p['Resgatar'] = False
        
        col_conf_p = {
            "Resgatar": st.column_config.CheckboxColumn("Voltar p/ Ativo?", default=False),
            "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
            "Data_Movimento": st.column_config.TextColumn("Data Prorrogação", width="small")
        }
        
        ed_p = st.data_editor(
            df_view_p, 
            column_config=col_conf_p, 
            disabled=COLUNAS_PADRAO + ["Data_Movimento"], 
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("🔄 Restaurar Selecionados"):
            recup = ed_p[ed_p['Resgatar']==True]
            if not recup.empty:
                df_a = carregar_aba("previsao_ativa")
                salvar_full("previsao_ativa", pd.concat([df_a, recup[COLUNAS_PADRAO]]))
                
                restantes = ed_p[ed_p['Resgatar']==False]
                if filtro_marca != "TODAS":
                    outros = df_prorrog[df_prorrog['Marca'] != filtro_marca]
                    final = pd.concat([outros, restantes]).drop(columns=['Resgatar'])
                else:
                    final = restantes.drop(columns=['Resgatar'])
                salvar_full("prorrogacao", final)
                st.rerun()
    else: st.info("Nenhuma prorrogação registrada.")

# --- TAB 3: DESISTÊNCIAS ---
with tab3:
    df_view_d = filtrar(df_desist)
    total_lost = df_view_d['Valor'].sum() if not df_view_d.empty else 0.0
    
    # KPI FINANCEIRO DESISTÊNCIA
    st.markdown(f'<div class="kpi-card" style="border-color: #f87171;"><div class="kpi-lbl">Total Perdido</div><div class="kpi-val-loss">R$ {total_lost:,.2f}</div></div>', unsafe_allow_html=True)
    st.write("")
    
    if not df_view_d.empty:
        df_view_d['Recuperar'] = False
        
        col_conf_d = {
            "Recuperar": st.column_config.CheckboxColumn("Tentar de Novo?", default=False),
            "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
            "Data_Movimento": st.column_config.TextColumn("Data Perda", width="small")
        }
        
        ed_d = st.data_editor(
            df_view_d, 
            column_config=col_conf_d, 
            disabled=COLUNAS_PADRAO + ["Data_Movimento"], 
            hide_index=True,
            use_container_width=True
        )
        
        if st.button("♻️ Resgatar Leads"):
            recup = ed_d[ed_d['Recuperar']==True]
            if not recup.empty:
                df_a = carregar_aba("previsao_ativa")
                salvar_full("previsao_ativa", pd.concat([df_a, recup[COLUNAS_PADRAO]]))
                
                restantes = ed_d[ed_d['Recuperar']==False]
                if filtro_marca != "TODAS":
                    outros = df_desist[df_desist['Marca'] != filtro_marca]
                    final = pd.concat([outros, restantes]).drop(columns=['Recuperar'])
                else:
                    final = restantes.drop(columns=['Recuperar'])
                salvar_full("desistencia", final)
                st.rerun()
    else: st.info("Nenhuma desistência registrada.")
