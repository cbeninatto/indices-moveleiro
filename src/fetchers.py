# src/fetchers.py
import io
import time
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
import yfinance as yf
import pandas as pd
import streamlit as st

def fetch_steelbenchmarker_pdf():
    """
    Downloads the SteelBenchmarker PDF directly into memory.
    """
    url = "http://steelbenchmarker.com/history.pdf"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status() # Check for errors
        return io.BytesIO(response.content)
    except Exception as e:
        st.error(f"Erro ao baixar PDF do SteelBenchmarker: {e}")
        return None

def fetch_iron_ore_automated():
    """
    Fetches SGX Iron Ore 62% Fe Futures (TIO=F) via Yahoo Finance.
    Returns a DataFrame compliant with the app's structure.
    """
    try:
        # Ticker TIO=F is the standard SGX Iron Ore 62% Fe CFR
        ticker = yf.Ticker("TIO=F")
        
        # Download 'max' history to ensure we cover the PDF dates
        hist = ticker.history(period="5y") 
        
        # Reset index to make Date a column and clean up
        df = hist.reset_index()[['Date', 'Close']]
        df.columns = ['Date', 'Price']
        
        # Ensure Date format matches what the app expects (datetime objects)
        df['Date'] = pd.to_datetime(df['Date']).dt.tz_localize(None)
        
        return df
    except Exception as e:
        st.error(f"Erro ao baixar Iron Ore do Yahoo Finance: {e}")
        return None


def _to_datestr_iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")


def _to_bcb_mmddyyyy(d: date) -> str:
    return d.strftime("%m-%d-%Y")


def _nearest_prev_business_day(d: date) -> date:
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d


def fetch_ptax_usdbrl_buy_for_dates(dates: list[date]) -> pd.DataFrame:
    """
    BCB Olinda PTAX - CotacaoDolarDia -> cotacaoCompra
    Se não houver cotação na data (feriado/fim de semana), busca o dia útil anterior.
    """
    base = (
        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        "CotacaoDolarDia(dataCotacao=@dataCotacao)"
    )

    out = []
    session = requests.Session()

    for d in dates:
        dd = _nearest_prev_business_day(d)
        ok = False
        for _ in range(5):
            params = {
                "@dataCotacao": f"'{_to_bcb_mmddyyyy(dd)}'",
                "$select": "cotacaoCompra,dataHoraCotacao",
                "$format": "json",
            }
            r = session.get(base, params=params, timeout=30)
            if r.status_code >= 500:
                time.sleep(1.0)
                continue
            r.raise_for_status()
            js = r.json()
            values = js.get("value", [])
            if values:
                out.append({"date": d, "USD/BRL": float(values[0]["cotacaoCompra"])})
                ok = True
                break
            dd = dd - timedelta(days=1)

        if not ok:
            out.append({"date": d, "USD/BRL": None})

    return pd.DataFrame(out)


def fetch_fred_series_for_dates(
    dates: list[date], fred_key: str, series_id: str = "DEXCHUS"
) -> pd.DataFrame:
    """
    FRED series observations. Retorna o valor no dia (ou último dia anterior com dado).
    """
    start = min(dates)
    end = max(dates)

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": fred_key,
        "file_type": "json",
        "observation_start": _to_datestr_iso(start - timedelta(days=10)),
        "observation_end": _to_datestr_iso(end),
    }

    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()

    obs = js.get("observations", [])
    data = []
    for o in obs:
        ds = o.get("date")
        val = o.get("value")
        if not ds or val in (None, ".", ""):
            continue
        try:
            data.append((pd.to_datetime(ds).date(), float(val)))
        except Exception:
            pass

    if not data:
        return pd.DataFrame({"date": dates, "USD/CNY": [None] * len(dates)})

    ser = pd.Series({d: v for d, v in data}).sort_index()

    out = []
    for d in dates:
        dd = d
        v = None
        for _ in range(10):
            if dd in ser.index:
                v = float(ser.loc[dd])
                break
            dd = dd - timedelta(days=1)
        out.append({"date": d, "USD/CNY": v})

    return pd.DataFrame(out)


def load_iron_ore_from_csv_for_dates(uploaded_file, dates: list[date]) -> pd.DataFrame:
    """
    Reads uploaded Iron Ore CSV and returns:
      date (CRC dates) + Iron Ore (USD/TON)

    Uses only the first 2 columns of the CSV: Date and Price.
    If the exact date is missing, uses nearest previous available date (up to 30 days).
    """
    content = uploaded_file.getvalue()

    # Try sniff delimiter automatically (works for comma/semicolon/tab)
    df = pd.read_csv(io.BytesIO(content), sep=None, engine="python", encoding_errors="ignore")

    if df.shape[1] < 2:
        return pd.DataFrame({"date": dates, "Iron Ore (USD/TON)": [np.nan] * len(dates)})

    dcol = df.columns[0]
    pcol = df.columns[1]

    tmp = df[[dcol, pcol]].copy()
    tmp.columns = ["Date", "Price"]

    # ---- DATE PARSING (robust) ----
    dt1 = pd.to_datetime(tmp["Date"], errors="coerce", dayfirst=False)
    if dt1.notna().mean() < 0.6:
        dt2 = pd.to_datetime(tmp["Date"], errors="coerce", dayfirst=True)
        tmp["Date"] = dt2
    else:
        tmp["Date"] = dt1

    # ---- PRICE PARSING (robust, handles decimal comma) ----
    s = tmp["Price"].astype(str).str.strip()
    s = s.str.replace(r"[^\d\.\,\-]", "", regex=True)

    # "113,89" -> "113.89"
    mask_decimal_comma = s.str.contains(",", na=False) & ~s.str.contains(r"\.", na=False)
    s.loc[mask_decimal_comma] = s.loc[mask_decimal_comma].str.replace(",", ".", regex=False)

    # "1,234.56" -> "1234.56"
    mask_thousands_comma = s.str.contains(",", na=False) & s.str.contains(r"\.", na=False)
    s.loc[mask_thousands_comma] = s.loc[mask_thousands_comma].str.replace(",", "", regex=False)

    tmp["Price"] = pd.to_numeric(s, errors="coerce")

    tmp = tmp.dropna(subset=["Date", "Price"])
    if tmp.empty:
        return pd.DataFrame({"date": dates, "Iron Ore (USD/TON)": [np.nan] * len(dates)})

    tmp["Date"] = tmp["Date"].dt.date
    tmp = tmp.sort_values("Date")

    # If duplicate dates, keep last
    ser = tmp.groupby("Date", as_index=True)["Price"].last().sort_index()

    out = []
    for d in dates:
        dd = d
        val = None
        for _ in range(30):
            if dd in ser.index:
                val = float(ser.loc[dd])
                break
            dd = dd - timedelta(days=1)
        out.append({"date": d, "Iron Ore (USD/TON)": val})

    return pd.DataFrame(out)
