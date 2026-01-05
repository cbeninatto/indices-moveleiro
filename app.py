# app.py
import os
import streamlit as st
import pandas as pd

from src.extract_crc import extract_crc_china_page12
from src.fetchers import (
    fetch_ptax_usdbrl_buy_for_dates,
    fetch_fred_series_for_dates,
    load_iron_ore_from_csv_for_dates,  # ✅ NEW
)
from src.analytics import build_enriched_metrics
from src.dashboard_html import build_dashboard_html
from src.report_pdf import build_pdf_report

st.set_page_config(page_title="Índices Moveleiro", layout="wide")

st.title("Índices Moveleiro — Atualização automática via SteelBenchmarker")

# ✅ NEW: Read FRED config from Streamlit Secrets (no manual key input)
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

# ✅ NEW: Upload Iron Ore CSV (Date + Price)
st.write("### 2) Upload do CSV de Minério de Ferro (Date + Price)")
iron_csv = st.file_uploader(
    "Envie o CSV do Iron Ore (somente as 2 primeiras colunas serão usadas: Date e Price)",
    type=["csv"],
)

colA, colB, colC = st.columns([1, 1, 2])
run_btn = colA.button("Gerar CSV + HTML + PDF", type="primary", use_container_width=True)

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

    # ✅ NEW: Iron Ore from uploaded CSV
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

    # Enrich metrics
    st.info("Calculando variações e métricas (YoY, 6M, 3M, 1M, correlações, volatilidade)...")
    enriched = build_enriched_metrics(df)

    csv_path = os.path.join(output_dir, "indices_moveleiro.csv")
    enriched.to_csv(csv_path, index=False, encoding="utf-8-sig")

    st.success("CSV gerado.")
    with open(csv_path, "rb") as f:
        st.download_button("Download CSV", f, file_name="indices_moveleiro.csv", mime="text/csv")

    st.info("Gerando dashboard HTML...")
    html_path = os.path.join(output_dir, "Indices_Moveleiro.html")
    html_str = build_dashboard_html(enriched, title="Índices Moveleiro")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_str)

    st.success("HTML gerado.")
    with open(html_path, "rb") as f:
        st.download_button("Download HTML", f, file_name="Indices_Moveleiro.html", mime="text/html")

    st.info("Gerando PDF...")
    pdf_out_path = os.path.join(output_dir, "Indices_Moveleiro.pdf")
    build_pdf_report(enriched, pdf_out_path, title="Índices Moveleiro")

    st.success("PDF gerado.")
    with open(pdf_out_path, "rb") as f:
        st.download_button("Download PDF", f, file_name="Indices_Moveleiro.pdf", mime="application/pdf")

    st.write("### Prévia (HTML)")
    st.components.v1.html(html_str, height=800, scrolling=True)
