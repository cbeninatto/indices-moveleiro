import streamlit as st
import pandas as pd
import io

# Importar suas funções (certifique-se que estão no src/fetchers.py e src/extract_crc.py)
from src.extract_crc import extract_crc_china_page12
from src.fetchers import (
    fetch_steelbenchmarker_pdf, 
    fetch_iron_ore_automated, 
    fetch_usd_brl_ptax, 
    fetch_usd_cny_fred
)

st.set_page_config(page_title="Índices Moveleiro", layout="wide")
st.title("🏭 Índices Moveleiro – Gerador Automático")

# --- 1. AQUISIÇÃO DE DADOS (SIDEBAR OU TOPO) ---
st.write("### 1. Atualizar Fontes de Dados")
col1, col2 = st.columns(2)

with col1:
    st.info("📉 **SteelBenchmarker (PDF)**")
    if st.button("🔄 Baixar PDF (SteelBenchmarker.com)"):
        with st.spinner("Baixando PDF..."):
            pdf_bytes = fetch_steelbenchmarker_pdf()
            if pdf_bytes:
                st.session_state['pdf_bytes'] = pdf_bytes
                st.success("PDF baixado e em memória!")

with col2:
    st.info("🪨 **Iron Ore (Yahoo Finance)**")
    if st.button("🔄 Baixar Cotações (TIO=F)"):
        with st.spinner("Baixando dados do Yahoo Finance..."):
            df_iron = fetch_iron_ore_automated()
            if df_iron is not None:
                st.session_state['df_iron'] = df_iron
                st.success(f"Cotações de Minério: {len(df_iron)} registros encontrados.")
                # Mostra as últimas 3 datas para confirmação
                st.dataframe(df_iron.tail(3), use_container_width=True, hide_index=True)

# --- 2. PROCESSAMENTO E VISUALIZAÇÃO ---
st.write("---")
st.write("### 2. Consolidação")

# Só libera o botão se tivermos o PDF e o Minério
if 'pdf_bytes' in st.session_state and 'df_iron' in st.session_state:
    
    if st.button("🚀 PROCESSAR E BUSCAR CÂMBIO (USD/BRL & CNY)"):
        
        try:
            with st.spinner("1/4 Extraindo dados do PDF..."):
                # Extrai dados do PDF que está na memória
                df_crc = extract_crc_china_page12(st.session_state['pdf_bytes'])
                st.session_state['df_crc'] = df_crc

            with st.spinner("2/4 Buscando USD/BRL (Banco Central)..."):
                # Busca todo o histórico necessário de uma vez ou filtra pelas datas
                min_date = df_crc['date'].min()
                df_ptax = fetch_usd_brl_ptax(start_date=min_date) # Sua função existente
            
            with st.spinner("3/4 Buscando USD/CNY (FRED)..."):
                df_cny = fetch_usd_cny_fred() # Sua função existente
            
            with st.spinner("4/4 Consolidando dados..."):
                # --- LÓGICA DE MERGE (Juntar tudo) ---
                
                # 1. Base é o SteelBenchmarker
                final_df = df_crc.copy()
                
                # 2. Merge Iron Ore (Considerando data exata ou anterior mais próxima)
                # Ordenar para garantir o merge_asof correto
                final_df = final_df.sort_values('date')
                df_iron_sorted = st.session_state['df_iron'].sort_values('Date')
                
                # Merge inteligente (procura data igual ou a anterior mais próxima)
                final_df = pd.merge_asof(
                    final_df, 
                    df_iron_sorted, 
                    left_on='date', 
                    right_on='Date', 
                    direction='backward',
                    tolerance=pd.Timedelta(days=7) # Aceita até 7 dias de diferença se for feriado
                )
                
                # 3. Merge Câmbio (Pode usar lógica similar ou merge direto se as funções já tratam datas)
                # Assumindo aqui que df_ptax e df_cny têm coluna 'date'
                final_df = pd.merge(final_df, df_ptax, on='date', how='left')
                final_df = pd.merge(final_df, df_cny, on='date', how='left')
                
                # Renomear e limpar colunas
                final_df['Sea_Freight_USD_ton'] = "" # Coluna em branco conforme requisito
                
                # Selecionar colunas finais (Ajuste os nomes conforme suas funções retornam)
                # Exemplo genérico:
                cols_final = [
                    'date', 
                    'CRC_China_USD_ton', 
                    'Price', # Iron Ore vindo do Yahoo
                    'Sea_Freight_USD_ton', 
                    'USD_BRL_buy', 
                    'USD_CNY'
                ]
                
                # Filtrar apenas colunas que existem (para evitar erro se nome for diferente)
                cols_existing = [c for c in cols_final if c in final_df.columns]
                final_df = final_df[cols_existing]
                
                # Renomear Iron Ore para o padrão
                final_df.rename(columns={'Price': 'Iron_Ore_USD_ton'}, inplace=True)
                
                # Guardar no estado
                st.session_state['final_df'] = final_df
                st.success("Consolidação concluída!")

        except Exception as e:
            st.error(f"Erro durante o processamento: {e}")
            st.write(e) # Mostra o erro técnico para debug

# --- 3. EXPORTAÇÃO E CONFERÊNCIA ---
if 'final_df' in st.session_state:
    st.write("### 3. Conferência e Download")
    
    # MOSTRAR DADOS PARA VOCÊ SABER QUE FUNCIONOU
    st.dataframe(st.session_state['final_df'].tail(10))
    
    # Métricas rápidas para conferência
    last_row = st.session_state['final_df'].iloc[-1]
    m1, m2, m3 = st.columns(3)
    m1.metric("Último CRC (PDF)", f"${last_row.get('CRC_China_USD_ton', 0)}")
    m2.metric("Último USD/BRL", f"R${last_row.get('USD_BRL_buy', 0):.4f}")
    m3.metric("Último USD/CNY", f"¥{last_row.get('USD_CNY', 0):.4f}")

    # Botão de Download
    csv = st.session_state['final_df'].to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Baixar CSV Final",
        data=csv,
        file_name='indices_moveleiro_consolidado.csv',
        mime='text/csv',
    )
