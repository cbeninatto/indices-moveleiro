# app.py
import os
import streamlit as st
import pandas as pd

from src.extract_crc import extract_crc_china_page12
from src.fetchers import (
    fetch_ptax_usdbrl_buy_for_dates,
    fetch_fred_series_for_dates,
    load_iron_ore_from_csv_for_dates,
)

st.set_page_config(page_title="Índices Moveleiro", layout="wide")

st.title("Índices Moveleiro — Gerador de CSV (CRC + Iron Ore + FX)")

# Read FRED config from Streamlit Secrets (no manual key input)
fred_key = st.secrets.get("FRED_API_KEY", "")
fred_series = st.secrets.get("FRED_SERIES_USD_CNY", "DEXCHUS")

with st.expander("Configurações (APIs)", expanded=True):
    st.write("**FRED (USD/CNY)**: lido automaticamente via *Secrets* do Streamlit Cloud.")
    st.caption("Configure em Settings → Secrets:")
    st.code('FRED_API_KEY = "SUA_CHAVE"\nFRED_SERIES_USD_CNY = "DEXCHUS"', language="toml")

    if not fred_key:
        st.error("FRED_API_KEY não encontrado em Secrets. Configure em Settings → Secrets.")
        st.stop()
    else:
        st.success(f"FRED configurado via Secrets ✅  (série: {fred_series})")

st.write("### 1) Upload do SteelBenchmarker history.pdf")
pdf_file = st.file_uploader("Envie o PDF", type=["pdf"])

st.write("### 2) Upload do CSV de Minério de Ferro (Date + Price)")
iron_csv = st.file_uploader(
    "Envie o CSV do Iron Ore (somente as 2 primeiras colunas serão usadas: Date e Price)",
    type=["csv"],
)

colA, colB, colC = st.columns([1, 1, 2])
run_btn = colA.button("Gerar CSV", type="primary", use_container_width=True)

output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

if run_btn:
    if not pdf_file:
        st.error("Envie um PDF primeiro.")
        st.stop()

    if not iron_csv:
        st.error("Envie também o CSV de Minério de Ferro (Date + Price).")
        st.stop()

    # Save uploaded PDF to disk
    pdf_path = os.path.join(output_dir, "history.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_file.getbuffer())

    st.info("Extraindo CRC China (página 12)...")
    crc_df = extract_crc_china_page12(pdf_path)

    if crc_df.empty:
        st.error("Não foi possível extrair a tabela de CRC China da página 12.")
        st.stop()

    st.success(f"Extraído: {len(crc_df)} linhas de CRC China.")
    st.dataframe(crc_df, use_container_width=True)

    dates = crc_df["date"].tolist()

    st.info("Lendo CSV de Minério de Ferro e mapeando para as datas do CRC...")
    iron = load_iron_ore_from_csv_for_dates(iron_csv, dates)

    st.info("Buscando USD/BRL PTAX (BCB Olinda) para as datas...")
    usdbrl = fetch_ptax_usdbrl_buy_for_dates(dates)

    st.info("Buscando USD/CNY (FRED) para as datas...")
    usdcny = fetch_fred_series_for_dates(dates, fred_key=fred_key, series_id=fred_series)

    # Merge
    df = (
        crc_df.merge(iron, on="date", how="left")
        .merge(usdbrl, on="date", how="left")
        .merge(usdcny, on="date", how="left")
    )

    # ✅ Rename to match required output columns EXACTLY
    df = df.rename(columns={
        "CRC Steel China (USD/TON)": "CRC_China_USD_ton",
        "Iron Ore (USD/TON)": "Iron_Ore_USD_ton",
        "USD/BRL": "USD_BRL_buy",
        "USD/CNY": "USD_CNY",
    })

    # ✅ Add Sea Freight column blank (manual input later)
    df["Sea_Freight_USD_ton"] = ""

    # ✅ Keep only required columns and order
    df = df[[
        "date",
        "CRC_China_USD_ton",
        "Iron_Ore_USD_ton",
        "Sea_Freight_USD_ton",
        "USD_BRL_buy",
        "USD_CNY",
    ]].copy()

    # Ensure date format is consistent
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%-m/%-d/%Y") if os.name != "nt" else pd.to_datetime(df["date"]).dt.strftime("%#m/%#d/%Y")

    csv_path = os.path.join(output_dir, "indices_moveleiro.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    st.success("CSV gerado (Sea_Freight_USD_ton em branco para preencher manualmente).")
    st.dataframe(df, use_container_width=True)

    with open(csv_path, "rb") as f:
        st.download_button("Download CSV", f, file_name="indices_moveleiro.csv", mime="text/csv")
