import streamlit as st
import pandas as pd

# Importar suas funções
from src.extract_crc import extract_crc_china_page12
from src.fetchers import (
    fetch_steelbenchmarker_pdf, 
    fetch_iron_ore_automated, 
    fetch_usd_brl_ptax, 
    fetch_usd_cny_fred
)

st.set_page_config(page_title="Índices Moveleiro", layout="wide")
st.title("🏭 Índices Moveleiro – Gerador Automático")

# --- 1. PAINEL DE CONTROLE ---
st.write("### 1. Atualizar Fontes de Dados")
col1, col2 = st.columns(2)

with col1:
    st.info("📉 **SteelBenchmarker (PDF)**")
    if st.button("🔄 Baixar PDF (SteelBenchmarker.com)"):
        with st.spinner("Baixando PDF..."):
            pdf_bytes = fetch_steelbenchmarker_pdf()
            if pdf_bytes:
                st.session_state['pdf_bytes'] = pdf_bytes
                st.success("PDF baixado!")

with col2:
    st.info("🪨 **Iron Ore (Yahoo Finance)**")
    if st.button("🔄 Baixar Cotações (TIO=F)"):
        with st.spinner("Baixando Yahoo Finance..."):
            df_iron = fetch_iron_ore_automated()
            if df_iron is not None:
                st.session_state['df_iron'] = df_iron
                st.success(f"Encontrados: {len(df_iron)} registros")
                # CORREÇÃO: use_container_width removido, width='stretch' inserido
                st.dataframe(df_iron.tail(3), width='stretch', hide_index=True)

# --- 2. CONSOLIDAÇÃO ---
st.write("---")
st.write("### 2. Processamento")

if 'pdf_bytes' in st.session_state and 'df_iron' in st.session_state:
    if st.button("🚀 GERAR CSV COMPLETO"):
        try:
            with st.spinner("Extraindo e Consolidando..."):
                # 1. Extrair PDF
                df_crc = extract_crc_china_page12(st.session_state['pdf_bytes'])
                
                # 2. Buscar Câmbio
                df_ptax = fetch_usd_brl_ptax(start_date=df_crc['date'].min())
                df_cny = fetch_usd_cny_fred()
                
                # 3. Merge (Juntar tudo)
                final_df = df_crc.sort_values('date')
                df_iron_sorted = st.session_state['df_iron'].sort_values('Date')
                
                # Merge inteligente do Minério (Backward search)
                final_df = pd.merge_asof(
                    final_df, df_iron_sorted, left_on='date', right_on='Date', 
                    direction='backward', tolerance=pd.Timedelta(days=7)
                )
                
                # Merge Câmbio
                final_df = pd.merge(final_df, df_ptax, on='date', how='left')
                final_df = pd.merge(final_df, df_cny, on='date', how='left')
                
                # Finalizar colunas
                final_df['Sea_Freight_USD_ton'] = ""
                final_df.rename(columns={'Price': 'Iron_Ore_USD_ton'}, inplace=True)
                
                cols = ['date', 'CRC_China_USD_ton', 'Iron_Ore_USD_ton', 'Sea_Freight_USD_ton', 'USD_BRL_buy', 'USD_CNY']
                # Garante apenas colunas existentes
                final_df = final_df[[c for c in cols if c in final_df.columns]]
                
                st.session_state['final_df'] = final_df
                st.success("Sucesso!")
        except Exception as e:
            st.error(f"Erro: {e}")

# --- 3. DOWNLOAD ---
if 'final_df' in st.session_state:
    st.write("### 3. Conferência")
    st.dataframe(st.session_state['final_df'].tail(10)) # Dataframe normal para ver os dados
    
    csv = st.session_state['final_df'].to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Baixar CSV", csv, "indices_moveleiro.csv", "text/csv")
