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
# ESTILIZAÇÃO CSS (PREMIUM & UI IMPROVEMENTS)
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

/* Mini Cards por Marca */
.brand-mini-card {
    background: #1e293b; border-left: 4px solid; padding: 15px; 
    border-radius: 0 8px 8px 0; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;
}
.bmc-label { font-family: 'Rajdhani'; font-weight: bold; font-size: 18px; color: #fff; }
.bmc-val { font-family: 'Orbitron'; font-weight: bold; font-size: 20px; }

/* Cores por contexto */
.wait-color { border-color: #fbbf24; }
.wait-text { color: #fbbf24; }
.loss-color { border-color: #f87171; }
.loss-text { color: #f87171; }

/* Ajuste na Tabela Editável para ficar mais larga e limpa */
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

        header = [h.strip() for h in dados[0]]
        if "Consultor" in header and "Valor" in header:
            df = pd.DataFrame(dados[1:], columns=header)
        else:
            if len(dados[0]) >= len(COLUNAS_PADRAO):
                 if dados[0][0] == "Consultor": 
                     df = pd.DataFrame(dados[1:], columns=COLUNAS_PADRAO)
                 else:
                     df = pd.DataFrame(dados, columns=COLUNAS_PADRAO)
            else:
                 return pd.DataFrame(columns=COLUNAS_PADRAO)

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
# UI - CADASTRO
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
col_filter, _ = st.columns([1, 3])
with col_filter:
    filtro_marca = st.selectbox("Filtrar Painel por Marca:", ["TODAS"] + marcas_opts)

# Carregar Dados
df_ativos = carregar_aba("previsao_ativa")
df_prorrog = carregar_aba("prorrogacao")
df_desist = carregar_aba("desistencia")

def filtrar_dados(df):
    if filtro_marca != "TODAS" and not df.empty and "Marca" in df.columns:
        return df[df["Marca"] == filtro_marca]
    return df

tab1, tab2, tab3 = st.tabs(["🎯 Previsão Ativa", "⏳ Prorrogações", "🚫 Desistências"])

# ==============================================================================
# TAB 1: PREVISÃO ATIVA (TABELA AMIGÁVEL)
# ==============================================================================
with tab1:
    df_view = filtrar_dados(df_ativos)
    
    # KPI GLOBAL DA ABA
    total_prev = df_view['Valor'].sum() if not df_view.empty else 0.0
    st.markdown(f"""
    <div style="background: rgba(74, 222, 128, 0.1); border: 1px solid #4ade80; padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 20px;">
        <span style="font-family:'Rajdhani'; color:#e0e0e0; font-size:16px;">VALOR TOTAL EM PIPELINE</span><br>
        <span style="font-family:'Orbitron'; color:#4ade80; font-size:24px;">R$ {total_prev:,.2f}</span>
    </div>
    """, unsafe_allow_html=True)

    if not df_ativos.empty:
        # Garante a coluna Ação antes de exibir
        df_view_edit = df_view.copy()
        df_view_edit['Ação'] = "Manter" 

        # CONFIGURAÇÃO AMIGÁVEL DA TABELA
        col_conf = {
            "Ação": st.column_config.SelectboxColumn(
                "Ação Imediata",
                options=["Manter", "Prorrogar", "Desistência"],
                width="medium",
                required=True
            ),
            "Valor": st.column_config.NumberColumn(
                "Valor (R$)", format="R$ %.2f", min_value=0, width="small"
            ),
            "Lead": st.column_config.TextColumn("Nome do Lead", width="medium"),
            "Consultor": st.column_config.TextColumn("Consultor", width="small"),
            "Marca": st.column_config.TextColumn("Marca", width="small"),
            "Cidade": st.column_config.TextColumn("Cidade", width="small"),
            "Campanha": st.column_config.TextColumn("Campanha", width="small"),
            # Esconde colunas técnicas para deixar amigável
            "Data_Registro": st.column_config.Column(None, width="small", disabled=True) 
        }

        # Ordem amigável das colunas
        column_order = ["Ação", "Valor", "Marca", "Lead", "Consultor", "Cidade", "Campanha", "Data_Registro"]

        df_editado = st.data_editor(
            df_view_edit,
            column_config=col_conf,
            column_order=column_order,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            key="editor_ativos_v2"
        )
        
        col_act, _ = st.columns([1, 4])
        if col_act.button("⚡ Processar Alterações", type="primary"):
            with st.spinner("Movendo leads..."):
                # Separa os grupos baseado na edição
                prorrogados = df_editado[df_editado['Ação'] == 'Prorrogar']
                desistentes = df_editado[df_editado['Ação'] == 'Desistência']
                # Quem fica: quem está marcado como Manter
                mantidos = df_editado[df_editado['Ação'] == 'Manter']

                # Lógica de Salvamento dos Ativos (Preservando quem estava oculto pelo filtro)
                cols_save = COLUNAS_PADRAO
                
                if filtro_marca != "TODAS":
                    # Recupera o que estava escondido
                    df_hidden = df_ativos[df_ativos['Marca'] != filtro_marca]
                    df_final_ativos = pd.concat([df_hidden, mantidos[cols_save]])
                else:
                    df_final_ativos = mantidos[cols_save]
                
                salvar_full("previsao_ativa", df_final_ativos)

                # Append Prorrogações
                if not prorrogados.empty:
                    df_p = carregar_aba("prorrogacao")
                    prorrogados = prorrogados.assign(Data_Movimento=datetime.now().strftime("%d/%m/%Y"))
                    cols_p = COLUNAS_PADRAO + ['Data_Movimento']
                    # Garante que as colunas existem no concat
                    if df_p.empty: df_p = pd.DataFrame(columns=cols_p)
                    df_p_new = pd.concat([df_p, prorrogados[cols_p]])
                    salvar_full("prorrogacao", df_p_new)

                # Append Desistências
                if not desistentes.empty:
                    df_d = carregar_aba("desistencia")
                    desistentes = desistentes.assign(Data_Movimento=datetime.now().strftime("%d/%m/%Y"))
                    cols_d = COLUNAS_PADRAO + ['Data_Movimento']
                    if df_d.empty: df_d = pd.DataFrame(columns=cols_d)
                    df_d_new = pd.concat([df_d, desistentes[cols_d]])
                    salvar_full("desistencia", df_d_new)

                st.success("Painel atualizado!")
                st.rerun()
    else:
        st.info("Nenhum lead ativo no momento.")

# ==============================================================================
# TAB 2: PRORROGAÇÕES (DIVIDIDO POR MARCA)
# ==============================================================================
with tab2:
    # 1. Filtra pelo Global primeiro
    df_p_filtrado = filtrar_dados(df_prorrog)
    
    if not df_p_filtrado.empty:
        # Pega lista de marcas presentes neste DF filtrado
        marcas_presentes = sorted(df_p_filtrado['Marca'].unique())
        
        # Coluna de controle checkbox
        df_p_filtrado['Resgatar'] = False
        
        # Cria um container de editor para tudo (para podermos salvar em lote)
        # MAS o usuário quer "Divisão por Marca". 
        # A melhor forma funcional no Streamlit é iterar e mostrar visualmente, 
        # mas editar um dataframe único para facilitar o "Salvar".
        # Porém, para ficar bonito visualmente (Mini Cards), vamos iterar.
        
        # Dicionario para guardar as edicoes de cada marca
        edicoes_p = {}
        
        for m in marcas_presentes:
            # Sub-dataframe da marca
            df_m = df_p_filtrado[df_p_filtrado['Marca'] == m].copy()
            total_m = df_m['Valor'].sum()
            
            # MINI CARD DA MARCA
            st.markdown(f"""
            <div class="brand-mini-card wait-color">
                <span class="bmc-label">{m}</span>
                <span class="bmc-val wait-text">R$ {total_m:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Tabela da Marca
            edicoes_p[m] = st.data_editor(
                df_m,
                column_config={
                    "Resgatar": st.column_config.CheckboxColumn("Voltar?", width="small", default=False),
                    "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Data_Movimento": st.column_config.TextColumn("Data Prorrog.", width="small")
                },
                disabled=COLUNAS_PADRAO + ["Data_Movimento"],
                hide_index=True,
                key=f"editor_prorrog_{m}"
            )
            st.write("") # Espaço
        
        # Botão Único de Ação no Final
        st.divider()
        if st.button("🔄 Restaurar Leads Selecionados (Todas as Marcas acima)"):
            leads_para_resgatar = pd.DataFrame()
            leads_para_ficar = pd.DataFrame()
            
            # Junta tudo que foi editado
            for m in marcas_presentes:
                df_edited_m = edicoes_p[m]
                resgatar = df_edited_m[df_edited_m['Resgatar'] == True]
                ficar = df_edited_m[df_edited_m['Resgatar'] == False]
                
                leads_para_resgatar = pd.concat([leads_para_resgatar, resgatar])
                leads_para_ficar = pd.concat([leads_para_ficar, ficar])
            
            # Executa Movimento
            if not leads_para_resgatar.empty:
                # 1. Adiciona em Ativos
                df_a = carregar_aba("previsao_ativa")
                df_a_new = pd.concat([df_a, leads_para_resgatar[COLUNAS_PADRAO]])
                salvar_full("previsao_ativa", df_a_new)
                
                # 2. Atualiza Prorrogação
                # Precisamos manter os leads de marcas que NÃO apareceram na tela (se houve filtro)
                if filtro_marca != "TODAS":
                    outras_marcas = df_prorrog[df_prorrog['Marca'] != filtro_marca]
                    df_p_final = pd.concat([outras_marcas, leads_para_ficar]).drop(columns=['Resgatar'])
                else:
                    df_p_final = leads_para_ficar.drop(columns=['Resgatar'])
                
                salvar_full("prorrogacao", df_p_final)
                st.success("Leads restaurados!")
                st.rerun()
            else:
                st.warning("Selecione alguém para restaurar.")
                
    else:
        st.info("Nenhuma prorrogação encontrada.")

# ==============================================================================
# TAB 3: DESISTÊNCIAS (DIVIDIDO POR MARCA)
# ==============================================================================
with tab3:
    df_d_filtrado = filtrar_dados(df_desist)
    
    if not df_d_filtrado.empty:
        marcas_presentes_d = sorted(df_d_filtrado['Marca'].unique())
        df_d_filtrado['Recuperar'] = False
        edicoes_d = {}
        
        for m in marcas_presentes_d:
            df_m_d = df_d_filtrado[df_d_filtrado['Marca'] == m].copy()
            total_m_d = df_m_d['Valor'].sum()
            
            # MINI CARD DA MARCA
            st.markdown(f"""
            <div class="brand-mini-card loss-color">
                <span class="bmc-label">{m}</span>
                <span class="bmc-val loss-text">R$ {total_m_d:,.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            
            edicoes_d[m] = st.data_editor(
                df_m_d,
                column_config={
                    "Recuperar": st.column_config.CheckboxColumn("Recuperar?", width="small", default=False),
                    "Valor": st.column_config.NumberColumn(format="R$ %.2f"),
                    "Data_Movimento": st.column_config.TextColumn("Data Perda", width="small")
                },
                disabled=COLUNAS_PADRAO + ["Data_Movimento"],
                hide_index=True,
                key=f"editor_desist_{m}"
            )
            st.write("")

        st.divider()
        if st.button("♻️ Resgatar Leads Perdidos (Todas as Marcas acima)"):
            resgatar_d_total = pd.DataFrame()
            ficar_d_total = pd.DataFrame()
            
            for m in marcas_presentes_d:
                df_e = edicoes_d[m]
                resgatar_d_total = pd.concat([resgatar_d_total, df_e[df_e['Recuperar'] == True]])
                ficar_d_total = pd.concat([ficar_d_total, df_e[df_e['Recuperar'] == False]])
            
            if not resgatar_d_total.empty:
                # 1. Add Ativos
                df_a = carregar_aba("previsao_ativa")
                df_a_new = pd.concat([df_a, resgatar_d_total[COLUNAS_PADRAO]])
                salvar_full("previsao_ativa", df_a_new)
                
                # 2. Remove Desistencia
                if filtro_marca != "TODAS":
                    outras = df_desist[df_desist['Marca'] != filtro_marca]
                    final = pd.concat([outras, ficar_d_total]).drop(columns=['Recuperar'])
                else:
                    final = ficar_d_total.drop(columns=['Recuperar'])
                
                salvar_full("desistencia", final)
                st.success("Leads resgatados do cemitério!")
                st.rerun()
            else:
                st.warning("Selecione alguém para resgatar.")
    else:
        st.info("Nenhuma desistência registrada.")
