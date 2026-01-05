# src/fetchers.py
import io
import time
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta


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


def fetch_fred_series_for_dates(dates: list[date], fred_key: str, series_id: str = "DEXCHUS") -> pd.DataFrame:
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
    df = pd.read_csv(io.BytesIO(content))

    if df.shape[1] < 2:
        return pd.DataFrame({"date": dates, "Iron Ore (USD/TON)": [np.nan] * len(dates)})

    dcol = df.columns[0]
    pcol = df.columns[1]

    tmp = df[[dcol, pcol]].copy()
    tmp.columns = ["Date", "Price"]

    tmp["Date"] = pd.to_datetime(tmp["Date"], errors="coerce", dayfirst=False)
    tmp["Price"] = pd.to_numeric(tmp["Price"], errors="coerce")

    tmp = tmp.dropna(subset=["Date", "Price"])
    tmp["Date"] = tmp["Date"].dt.date
    tmp = tmp.sort_values("Date")

    if tmp.empty:
        return pd.DataFrame({"date": dates, "Iron Ore (USD/TON)": [np.nan] * len(dates)})

    tmp = tmp.groupby("Date", as_index=True)["Price"].last().sort_index()
    ser = tmp

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
