import numpy as np
import pandas as pd

NUM_COLS = ["CRC Steel China (USD/TON)", "Iron Ore (USD/TON)", "USD/BRL", "USD/CNY"]

def _pct_change(series: pd.Series, periods: int) -> pd.Series:
    return series.pct_change(periods=periods) * 100.0

def _rolling_vol(series: pd.Series, window: int = 6) -> pd.Series:
    # volatilidade (%), usando std de variação percentual mensal/quinzenal conforme amostra
    return series.pct_change().rolling(window).std() * 100.0

def build_enriched_metrics(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["date"] = pd.to_datetime(out["date"]).dt.date
    out = out.sort_values("date").reset_index(drop=True)

    # Força numérico
    for c in out.columns:
        if c in ["date"]:
            continue
        out[c] = pd.to_numeric(out[c], errors="coerce")

    # Variações: YoY (~24 pontos se bi-mensal), 6M (~12), 3M (~6), 1M (~2)
    # Obs: como SteelBenchmarker é 2x por mês, usamos aproximação por "pontos".
    out["1M %"] = _pct_change(out["CRC Steel China (USD/TON)"], 2)
    out["3M %"] = _pct_change(out["CRC Steel China (USD/TON)"], 6)
    out["6M %"] = _pct_change(out["CRC Steel China (USD/TON)"], 12)
    out["YoY %"] = _pct_change(out["CRC Steel China (USD/TON)"], 24)

    # Volatilidade rolling (6 pontos)
    out["Volatilidade (6p) %"] = _rolling_vol(out["CRC Steel China (USD/TON)"], window=6)

    # Correlações (Pearson simples, rolling, e lag)
    # Rolling corr (6 pontos) CRC vs cada variável
    for col in ["Iron Ore (USD/TON)", "USD/BRL", "USD/CNY"]:
        out[f"Corr Rolling 6p (CRC vs {col})"] = out["CRC Steel China (USD/TON)"].rolling(6).corr(out[col])

        # Lag corr: CRC(t) vs X(t-1) e X(t-2)
        out[f"Corr Lag1 (CRC vs {col})"] = out["CRC Steel China (USD/TON)"].rolling(10).corr(out[col].shift(1))
        out[f"Corr Lag2 (CRC vs {col})"] = out["CRC Steel China (USD/TON)"].rolling(10).corr(out[col].shift(2))

    return out
