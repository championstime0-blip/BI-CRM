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
# ESTILIZAÇÃO CSS (Futurista)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;700;900&family=Rajdhani:wght@500;700&display=swap');
.stApp { background-color: #0b0f1a; color: #e0e0e0; }

.futuristic-header {
    font-family: 'Orbitron', sans-serif; font-size: 36px; font-weight: 900; text-transform: uppercase;
    background: linear-gradient(90deg, #22d3ee 0%, #a855f7 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    text-shadow: 0 0 20px rgba(34, 211, 238, 0.4); margin-bottom: 20px;
}
.kpi-card {
    background: linear-gradient(135deg, #1e293b, #0f172a); border: 1px solid #334155;
    padding: 15px; border-radius: 10px; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.3);
}
.kpi-val { font-family: 'Orbitron'; font-size: 24px; color: #4ade80; }
.kpi-lbl { font-family: 'Rajdhani'; font-size: 14px; color: #94a3b8; text-transform: uppercase; }

div[data-testid="stDataEditor"] { border: 1px solid #22d3ee; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# =========================
# CONEXÃO GOOGLE SHEETS
# =========================
# Definição das colunas obrigatórias para evitar KeyError
COLUNAS_OBRIGATORIAS = ["Consultor", "Lead", "Cidade", "Campanha", "Marca", "Valor", "Data_Registro"]

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

PLANILHA_NOME = "BI_Historico"

# =========================
# FUNÇÕES DE BANCO DE DADOS (ROBUSTAS)
# =========================

def carregar_aba(nome_aba):
    """Carrega dados e GARANTE que as colunas existem para não dar erro."""
    client = conectar_google()
    # Se falhar conexão, retorna vazio com colunas certas
    if not client: return pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)
    
    try:
        sh = client.open(PLANILHA_NOME)
        
        # Tenta abrir a aba, se não existir, cria
        try:
            ws = sh.worksheet(nome_aba)
        except:
            ws = sh.add_worksheet(nome_aba, 1000, 20)
            ws.append_row(COLUNAS_OBRIGATORIAS) # Cria cabeçalho
            return pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)
            
        dados = ws.get_all_values()
        
        # Se estiver vazia (sem nem cabeçalho)
        if not dados:
            ws.append_row(COLUNAS_OBRIGATORIAS)
            return pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)
            
        # Carrega DataFrame
        df = pd.DataFrame(dados[1:], columns=dados[0])
        
        # VERIFICAÇÃO DE SEGURANÇA (CORREÇÃO DO KEYERROR)
        # Se o cabeçalho estiver errado (ex: não tem 'Valor'), ignora os dados e retorna vazio estruturado
        if 'Valor' not in df.columns or 'Marca' not in df.columns:
            # Opcional: Poderiamos limpar a aba aqui, mas por segurança apenas retornamos o DF vazio correto
            return pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)
            
        # Tratamento de tipos
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce').fillna(0.0)
        return df

    except Exception as e:
        # Em caso de qualquer erro catastrófico, não quebra a tela
        return pd.DataFrame(columns=COLUNAS_OBRIGATORIAS)

def salvar_full(nome_aba, df):
    client = conectar_google()
    if not client: return
    sh = client.open(PLANILHA_NOME)
    try:
        ws = sh.worksheet(nome_aba)
    except:
        ws = sh.add_worksheet(nome_aba, 1000, 20)
    
    ws.clear()
    # Garante que salva como string para não bugar JSON
    df_save = df.copy()
    df_save = df_save.astype(str)
    ws.update([df_save.columns.values.tolist()] + df_save.values.tolist())

def adicionar_lead(dados):
    client = conectar_google()
    if not client: return
    sh = client.open(PLANILHA_NOME)
    try:
        ws = sh.worksheet("previsao_ativa")
    except:
        ws = sh.add_worksheet("previsao_ativa", 1000, 20)
    
    # Se vazia, põe cabeçalho antes
    if not ws.get_all_values():
        ws.append_row(COLUNAS_OBRIGATORIAS)
    
    ws.append_row(dados)

# =========================
# UI - CADASTRO LATERAL
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
    
    submitted = st.form_submit_button("💾 Cadastrar Previsão")
    if submitted:
        if f_lead and f_consultor:
            dados = [f_consultor, f_lead, f_cidade, f_campanha, f_marca, f_valor, datetime.now().strftime("%d/%m/%Y")]
            adicionar_lead(dados)
            st.success("Cadastrado com sucesso!")
            st.rerun()
        else:
            st.error("Preencha Consultor e Lead.")

# =========================
# UI - PAINEL PRINCIPAL
# =========================
st.markdown('<div class="futuristic-header">🔮 Painel de Previsão de Vendas</div>', unsafe_allow_html=True)

# Filtro Global
filtro_marca = st.selectbox("Filtrar Visão por Marca:", ["TODAS"] + marcas_opts)

# Carrega Dados (Agora blindado contra erro)
df_ativos = carregar_aba("previsao_ativa")
df_prorrog = carregar_aba("prorrogacao")
df_desist = carregar_aba("desistencia")

# Aplica Filtro Visual
def filtrar(df):
    if filtro_marca != "TODAS" and not df.empty and "Marca" in df.columns:
        return df[df["Marca"] == filtro_marca]
    return df

# ABAS
tab1, tab2, tab3 = st.tabs(["🎯 Previsão Ativa", "⏳ Prorrogações", "🚫 Desistências"])

# --- TAB 1: ATIVOS ---
with tab1:
    df_view = filtrar(df_ativos)
    
    # KPIs Rápidos
    total_prev = df_view['Valor'].sum() if not df_view.empty else 0.0
    leads_count = len(df_view)
    
    k1, k2 = st.columns(2)
    with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Valor em Pipeline</div><div class="kpi-val">R$ {total_prev:,.2f}</div></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Leads Ativos</div><div class="kpi-val">{leads_count}</div></div>', unsafe_allow_html=True)
    
    st.divider()
    
    if not df_ativos.empty:
        st.info("Edite o **Valor** diretamente na tabela ou escolha uma **Ação** e clique em Processar.")
        
        # Coluna de controle
        df_ativos['Ação'] = "Manter" 
        
        # Configuração das Colunas
        col_config = {
            "Valor": st.column_config.NumberColumn("Valor Previsto", format="R$ %.2f", min_value=0, required=True),
            "Ação": st.column_config.SelectboxColumn(
                "Ação (Mover)",
                options=["Manter", "Prorrogar", "Desistência"],
                required=True,
                help="Selecione o destino deste lead"
            ),
            "Marca": st.column_config.SelectboxColumn("Marca", options=marcas_opts, required=True),
            "Data_Registro": st.column_config.TextColumn("Data", disabled=True)
        }
        
        # Mostra Tabela
        df_editado = st.data_editor(
            df_view if filtro_marca != "TODAS" else df_ativos,
            column_config=col_config,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_ativos"
        )
        
        col_btn, _ = st.columns([1, 4])
        if col_btn.button("⚡ Processar Alterações", type="primary"):
            with st.spinner("Atualizando..."):
                # Separa grupos
                prorrogados = df_editado[df_editado['Ação'] == 'Prorrogar'].copy()
                desistentes = df_editado[df_editado['Ação'] == 'Desistência'].copy()
                mantidos_editados = df_editado[df_editado['Ação'] == 'Manter'].copy()
                
                cols_save = COLUNAS_OBRIGATORIAS
                
                # Reconstrução dos Ativos
                if filtro_marca != "TODAS":
                    df_outras_marcas = df_ativos[df_ativos['Marca'] != filtro_marca]
                    df_final_ativos = pd.concat([df_outras_marcas, mantidos_editados[cols_save]])
                else:
                    df_final_ativos = mantidos_editados[cols_save]
                
                salvar_full("previsao_ativa", df_final_ativos)
                
                # Prorrogar
                if not prorrogados.empty:
                    df_prorrog_atual = carregar_aba("prorrogacao")
                    prorrogados['Data_Movimento'] = datetime.now().strftime("%d/%m/%Y")
                    # Garante que df_prorrog_atual tem as colunas certas antes do concat
                    if df_prorrog_atual.empty: df_prorrog_atual = pd.DataFrame(columns=cols_save + ['Data_Movimento'])
                    
                    df_novo_prorrog = pd.concat([df_prorrog_atual, prorrogados[cols_save + ['Data_Movimento']]])
                    salvar_full("prorrogacao", df_novo_prorrog)
                    
                # Desistir
                if not desistentes.empty:
                    df_desist_atual = carregar_aba("desistencia")
                    desistentes['Data_Movimento'] = datetime.now().strftime("%d/%m/%Y")
                    if df_desist_atual.empty: df_desist_atual = pd.DataFrame(columns=cols_save + ['Data_Movimento'])
                    
                    df_novo_desist = pd.concat([df_desist_atual, desistentes[cols_save + ['Data_Movimento']]])
                    salvar_full("desistencia", df_novo_desist)
                
                st.success("Atualizado!")
                st.rerun()
    else:
        st.warning("Nenhuma previsão ativa. Cadastre na barra lateral.")

# --- TAB 2: PRORROGAÇÕES ---
with tab2:
    df_view_p = filtrar(df_prorrog)
    
    st.markdown("### 🧊 Leads em Stand-by")
    if not df_view_p.empty:
        df_view_p['Retornar'] = False
        
        edit_prorrog = st.data_editor(
            df_view_p,
            column_config={
                "Retornar": st.column_config.CheckboxColumn("Voltar para Previsão?", default=False),
                "Valor": st.column_config.NumberColumn(format="R$ %.2f")
            },
            disabled=COLUNAS_OBRIGATORIAS + ["Data_Movimento"],
            hide_index=True,
            key="editor_prorrog"
        )
        
        if st.button("🔄 Restaurar Selecionados"):
            recuperar = edit_prorrog[edit_prorrog['Retornar'] == True]
            
            if not recuperar.empty:
                df_ativos_atual = carregar_aba("previsao_ativa")
                df_ativos_novo = pd.concat([df_ativos_atual, recuperar[COLUNAS_OBRIGATORIAS]])
                salvar_full("previsao_ativa", df_ativos_novo)
                
                # Remove de Prorrogação
                ficaram = edit_prorrog[edit_prorrog['Retornar'] == False]
                if filtro_marca != "TODAS":
                     outras = df_prorrog[df_prorrog['Marca'] != filtro_marca]
                     novo_prorrog = pd.concat([outras, ficaram]).drop(columns=['Retornar'])
                else:
                     novo_prorrog = ficaram.drop(columns=['Retornar'])
                
                salvar_full("prorrogacao", novo_prorrog)
                st.success("Leads recuperados!")
                st.rerun()
    else:
        st.info("Nenhuma prorrogação.")

# --- TAB 3: DESISTÊNCIAS ---
with tab3:
    df_view_d = filtrar(df_desist)
    
    st.markdown("### 💀 Cemitério de Leads")
    if not df_view_d.empty:
        df_view_d['Retornar'] = False
        
        edit_desist = st.data_editor(
            df_view_d,
            column_config={
                "Retornar": st.column_config.CheckboxColumn("Recuperar?", default=False),
                "Valor": st.column_config.NumberColumn(format="R$ %.2f")
            },
            disabled=COLUNAS_OBRIGATORIAS + ["Data_Movimento"],
            hide_index=True,
            key="editor_desist"
        )
        
        if st.button("♻️ Resgatar Lead"):
            recuperar_d = edit_desist[edit_desist['Retornar'] == True]
            
            if not recuperar_d.empty:
                df_ativos_atual = carregar_aba("previsao_ativa")
                df_ativos_novo = pd.concat([df_ativos_atual, recuperar_d[COLUNAS_OBRIGATORIAS]])
                salvar_full("previsao_ativa", df_ativos_novo)
                
                ficaram_d = edit_desist[edit_desist['Retornar'] == False]
                if filtro_marca != "TODAS":
                     outras_d = df_desist[df_desist['Marca'] != filtro_marca]
                     novo_desist = pd.concat([outras_d, ficaram_d]).drop(columns=['Retornar'])
                else:
                     novo_desist = ficaram_d.drop(columns=['Retornar'])
                
                salvar_full("desistencia", novo_desist)
                st.success("Leads resgatados!")
                st.rerun()
    else:
        st.info("Nenhuma desistência.")
