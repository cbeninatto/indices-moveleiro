import time
import requests
import pandas as pd
from datetime import date, datetime, timedelta

def _to_datestr_iso(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def _to_bcb_mmddyyyy(d: date) -> str:
    return d.strftime("%m-%d-%Y")

def _nearest_prev_business_day(d: date) -> date:
    # se cair no fim de semana, volta para sexta
    while d.weekday() >= 5:
        d = d - timedelta(days=1)
    return d

def fetch_ptax_usdbrl_buy_for_dates(dates: list[date]) -> pd.DataFrame:
    """
    BCB Olinda PTAX - CotacaoDolarDia -> cotacaoCompra
    Se não houver cotação na data (feriado/fim de semana), busca o dia útil anterior.
    """
    base = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarDia(dataCotacao=@dataCotacao)"

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
            # se não achou, volta mais um dia
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

def fetch_tradingeconomics_iron_ore_for_dates(dates: list[date], te_key: str) -> pd.DataFrame:
    """
    TradingEconomics: tenta endpoints comuns e se adapta à estrutura do JSON.
    Objetivo: obter uma série diária e mapear para as datas (ou último dia anterior com dado).
    """
    start = min(dates)
    end = max(dates)

    # Tentativas de endpoint (TE muda bastante conforme plano/rota).
    candidates = [
        # histórico commodity (alguns planos):
        ("https://api.tradingeconomics.com/historical/commodity/iron%20ore", {"c": te_key, "d1": _to_datestr_iso(start - timedelta(days=10)), "d2": _to_datestr_iso(end)}),
        # markets historical commodity:
        ("https://api.tradingeconomics.com/markets/historical/commodity/iron%20ore", {"c": te_key, "d1": _to_datestr_iso(start - timedelta(days=10)), "d2": _to_datestr_iso(end)}),
        # markets commodity snapshot (fallback: pode não ter histórico):
        ("https://api.tradingeconomics.com/markets/commodity/iron%20ore", {"c": te_key}),
        ("https://api.tradingeconomics.com/markets/commodities/iron%20ore", {"c": te_key}),
    ]

    session = requests.Session()
    series = []

    last_err = None
    for url, params in candidates:
        try:
            r = session.get(url, params=params, timeout=30)
            r.raise_for_status()
            js = r.json()

            # Normalmente vem lista de dicts. Precisamos de Date + Value/Close/Last.
            if isinstance(js, dict) and "data" in js:
                js = js["data"]
            if not isinstance(js, list):
                continue

            tmp = []
            for it in js:
                if not isinstance(it, dict):
                    continue

                # variações de campo:
                ds = it.get("Date") or it.get("date") or it.get("Datetime") or it.get("LastUpdate")
                val = it.get("Value") or it.get("value") or it.get("Close") or it.get("close") or it.get("Last") or it.get("last")

                # em alguns endpoints, "Last" vem e "Date" não.
                if ds is None:
                    continue
                try:
                    d = pd.to_datetime(str(ds)).date()
                except Exception:
                    continue

                try:
                    if val is None:
                        continue
                    v = float(str(val).replace(",", ""))
                except Exception:
                    continue

                tmp.append((d, v))

            if tmp:
                series = tmp
                break

        except Exception as e:
            last_err = e
            continue

    if not series:
        # sem dados -> coluna vazia
        return pd.DataFrame({"date": dates, "Iron Ore (USD/TON)": [None] * len(dates)})

    ser = pd.Series({d: v for d, v in series}).sort_index()

    out = []
    for d in dates:
        dd = d
        v = None
        for _ in range(20):
            if dd in ser.index:
                v = float(ser.loc[dd])
                break
            dd = dd - timedelta(days=1)
        out.append({"date": d, "Iron Ore (USD/TON)": v})

    return pd.DataFrame(out)
