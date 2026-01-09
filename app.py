# app.py (Simplified Logic)

import streamlit as st
from src.fetchers import fetch_steelbenchmarker_pdf, fetch_iron_ore_automated
# ... other imports ...

st.title("Índices Moveleiro – Gerador Automático")

# --- CONTROL PANEL ---
st.write("### 1. Fontes de Dados")

col1, col2 = st.columns(2)

with col1:
    st.info("📉 **SteelBenchmarker**")
    # Button to fetch PDF
    if st.button("🔄 Baixar PDF Atualizado"):
        with st.spinner("Baixando PDF do SteelBenchmarker..."):
            pdf_file = fetch_steelbenchmarker_pdf()
            if pdf_file:
                st.session_state['pdf_file'] = pdf_file
                st.success("PDF baixado com sucesso!")

with col2:
    st.info("🪨 **Iron Ore (Yahoo Finance)**")
    # Button to fetch Iron Ore
    if st.button("🔄 Baixar Cotações Iron Ore"):
        with st.spinner("Baixando dados da SGX/Yahoo..."):
            df_iron = fetch_iron_ore_automated()
            if df_iron is not None:
                st.session_state['df_iron'] = df_iron
                st.success(f"Iron Ore carregado! ({len(df_iron)} registros)")

# --- GENERATION ---
st.write("---")
if 'pdf_file' in st.session_state and 'df_iron' in st.session_state:
    if st.button("🚀 GERAR CSV CONSOLIDADO"):
        # Call your existing processing logic here, passing 
        # st.session_state['pdf_file'] and st.session_state['df_iron']
        pass
else:
    st.warning("Por favor, clique nos botões acima para baixar os dados antes de gerar.")
