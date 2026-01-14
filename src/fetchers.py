import requests
import pandas as pd
import io
import streamlit as st
import yfinance as yf
from datetime import datetime

# --- 1. FUNÇÃO DO STEELBENCHMARKER (PDF) ---
def fetch_steelbenchmarker_pdf():
    url = "http://steelbenchmarker.com/history.pdf"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return io.BytesIO(response.content)
    except Exception as e:
        st.error(f"Erro ao baixar PDF: {e}")
        return None

# --- 2. FUNÇÃO DO MINÉRIO (YAHOO) ---
def fetch_iron_ore_automated():
    try:
        ticker = yf.Ticker("TIO=F")
        hist = ticker.history(period="5y")
        df = hist.reset_index()[['Date', 'Close']]
        df.columns = ['Date', 'Price']
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        return df
    except Exception as e:
        st.error(f"Erro ao baixar Iron Ore: {e}")
        return None

# --- 3. FUNÇÃO DO DÓLAR (BCB) ---
def fetch_usd_brl_ptax(start_date):
    data_inicial = start_date.strftime('%m-%d-%Y')
    data_final = datetime.today().strftime('%m-%d-%Y')
    url = f"https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)?@dataInicial='{data_inicial}'&@dataFinalCotacao='{data_final}'&$top=10000&$format=json&$select=cotacaoCompra,dataHoraCotacao"

    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if 'value' not in data: return pd.DataFrame(columns=['date', 'USD_BRL_buy'])
        
        df = pd.DataFrame(data['value'])
        df.rename(columns={'cotacaoCompra': 'USD_BRL_buy', 'dataHoraCotacao': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        return df[['date', 'USD_BRL_buy']]
    except Exception as e:
        st.error(f"Erro BCB: {e}")
        return pd.DataFrame(columns=['date', 'USD_BRL_buy'])

# --- 4. FUNÇÃO DO YUAN (FRED) ---
def fetch_usd_cny_fred():
    series_id = st.secrets.get("FRED_SERIES_USD_CNY", "DEXCHUS")
    api_key = st.secrets.get("FRED_API_KEY")
    if not api_key:
        st.error("FRED_API_KEY ausente nos Secrets.")
        return pd.DataFrame(columns=['date', 'USD_CNY'])

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {"series_id": series_id, "api_key": api_key, "file_type": "json", "sort_order": "desc", "limit": 1000}

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        df = pd.DataFrame(data.get("observations", []))
        if df.empty: return pd.DataFrame(columns=['date', 'USD_CNY'])
        
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df.dropna(subset=['value'], inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.rename(columns={'value': 'USD_CNY'}, inplace=True)
        return df[['date', 'USD_CNY']]
    except Exception as e:
        st.error(f"Erro FRED: {e}")
        return pd.DataFrame(columns=['date', 'USD_CNY'])
