import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Configuração da Página
st.set_page_config(
    page_title="Dashboard de Análise",
    page_icon="📊",
    layout="wide"
)

# Título e Subtítulo
st.title("📊 Dashboard de Business Intelligence")
st.markdown("---")

# 2. Upload do Arquivo
st.sidebar.header("Carregar Dados")
uploaded_file = st.sidebar.file_uploader("Solte seu arquivo CSV aqui", type=["csv"])

if uploaded_file is not None:
    # Tenta ler o CSV (tratando possíveis erros de separador ou encoding)
    try:
        df = pd.read_csv(uploaded_file)
        
        # Visão Geral dos Dados
        st.subheader("Visualização da Tabela de Dados")
        st.dataframe(df.head())

        # Informações básicas
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Linhas", df.shape[0])
        col1.metric("Total de Colunas", df.shape[1])
        
        # --- ÁREA DE CRIAÇÃO DE GRÁFICOS ---
        st.markdown("---")
        st.subheader("📈 Análise Gráfica")

        # Seleção de Colunas para o Gráfico
        col_opcoes = df.columns.tolist()
        
        c1, c2, c3 = st.columns(3)
        x_axis = c1.selectbox("Eixo X (Categorias)", col_opcoes, index=0)
        y_axis = c2.selectbox("Eixo Y (Valores)", col_opcoes, index=1 if len(col_opcoes) > 1 else 0)
        chart_type = c3.selectbox("Tipo de Gráfico", ["Barras", "Linha", "Pizza", "Dispersão"])

        # Gerar Gráfico com Plotly
        if chart_type == "Barras":
            fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} por {x_axis}")
        elif chart_type == "Linha":
            fig = px.line(df, x=x_axis, y=y_axis, title=f"Evolução de {y_axis}")
        elif chart_type == "Pizza":
            fig = px.pie(df, names=x_axis, values=y_axis, title=f"Distribuição de {y_axis}")
        elif chart_type == "Dispersão":
            fig = px.scatter(df, x=x_axis, y=y_axis, title=f"Correlação: {x_axis} vs {y_axis}")

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando upload do arquivo CSV. Por favor, utilize a barra lateral.")
