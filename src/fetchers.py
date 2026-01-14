import requests
import pandas as pd
import io
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

# --- 1. FUNÇÃO DO STEELBENCHMARKER (PDF) ---
def fetch_steelbenchmarker_pdf():
    """
    Baixa o PDF do SteelBenchmarker diretamente para a memória.
    """
    url = "http://steelbenchmarker.com/history.pdf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except Exception as e:
        st.error(f"Erro ao baixar PDF do SteelBenchmarker: {e}")
        return None

# --- 2. FUNÇÃO DO MINÉRIO (YAHOO FINANCE) ---
def fetch_iron_ore_automated():
    """
    Baixa dados do SGX Iron Ore 62% Fe (TIO=F) via Yahoo Finance.
    Retorna DataFrame com colunas ['Date', 'Price'].
    """
    try:
        # Ticker TIO=F é o futuro padrão de minério 62%
        ticker = yf.Ticker("TIO=F")
        
        # Baixa histórico de 5 anos para garantir cobertura
        hist = ticker.history(period="5y")
        
        # Limpeza e formatação
        df = hist.reset_index()[['Date', 'Close']]
        df.columns = ['Date', 'Price']
        
        # Remove timezone para evitar conflitos de merge
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        return df
    except Exception as e:
        st.error(f"Erro ao baixar Iron Ore do Yahoo Finance: {e}")
        return None

# --- 3. FUNÇÃO DO DÓLAR PTAX (BANCO CENTRAL) ---
def fetch_usd_brl_ptax(start_date):
    """
    Busca a taxa de compra PTAX do Dólar (USD/BRL) na API do Banco Central.
    """
    # Formata data para API (MM-DD-YYYY)
    data_inicial = start_date.strftime('%m-%d-%Y')
    data_final = datetime.today().strftime('%m-%d-%Y')
    
    url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='{data_inicial}'&@dataFinalCotacao='{data_final}'&$top=10000&$format=json&$select=cotacaoCompra,dataHoraCotacao"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'value' not in data or len(data['value']) == 0:
            st.warning("Nenhum dado encontrado na API do BCB.")
            return pd.DataFrame(columns=['date', 'USD_BRL_buy'])

        df = pd.DataFrame(data['value'])
        
        # Renomear e formatar
        df.rename(columns={'cotacaoCompra': 'USD_BRL_buy', 'dataHoraCotacao': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.normalize() # Remove horas
        
        return df[['date', 'USD_BRL_buy']]
        
    except Exception as e:
        st.error(f"Erro na API do Banco Central: {e}")
        return pd.DataFrame(columns=['date', 'USD_BRL_buy'])

# --- 4. FUNÇÃO DO YUAN (FRED - FEDERAL RESERVE) ---
def fetch_usd_cny_fred():
    """
    Busca a taxa de câmbio USD/CNY no FRED (St. Louis Fed).
    Requer FRED_API_KEY configurado nos Secrets do Streamlit.
    """
    series_id = st.secrets.get("FRED_SERIES_USD_CNY", "DEXCHUS")
    api_key = st.secrets.get("FRED_API_KEY")

    if not api_key:
        st.error("ERRO: FRED_API_KEY não encontrada nos Secrets do Streamlit.")
        return pd.DataFrame(columns=['date', 'USD_CNY'])

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "sort_order": "desc",
        "limit": 1000  # Pega os últimos ~3-4 anos (dias úteis)
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        observations = data.get("observations", [])
        if not observations:
            return pd.DataFrame(columns=['date', 'USD_CNY'])

        df = pd.DataFrame(observations)
        
        # Limpeza
        df['value'] = pd.to_numeric(df['value'], errors='coerce') # Converte "." para NaN
        df.dropna(subset=['value'], inplace=True)
        
        df['date'] = pd.to_datetime(df['date'])
        df.rename(columns={'value': 'USD_CNY'}, inplace=True)
        
        return df[['date', 'USD_CNY']]
        
    except Exception as e:
        st.error(f"Erro na API do FRED: {e}")
        return pd.DataFrame(columns=['date', 'USD_CNY'])
