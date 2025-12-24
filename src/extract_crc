import re
import pandas as pd
import pdfplumber
from datetime import datetime

DATE_RE = re.compile(r"^\d{1,2}-[A-Za-z]{3}-\d{2}$")

def _parse_date(s: str) -> pd.Timestamp:
    # Ex.: 13-May-24
    return pd.to_datetime(s, format="%d-%b-%y", errors="coerce")

def extract_crc_china_page12(pdf_path: str) -> pd.DataFrame:
    """
    Extrai (date, CRC Steel China (USD/TON)) da página 12 (1-indexed) do PDF.
    A página 12 contém a tabela China Ex-works: Scrap | HRB | CRC | Plate | Rebar.
    Vamos capturar a coluna CRC (o 3º número de preço após a data, na estrutura do PDF).
    """
    page_index = 11  # 0-index => página 12
    rows = []

    with pdfplumber.open(pdf_path) as pdf:
        if len(pdf.pages) <= page_index:
            return pd.DataFrame(columns=["date", "CRC Steel China (USD/TON)"])

        text = pdf.pages[page_index].extract_text() or ""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Linhas relevantes começam com data
    for ln in lines:
        parts = ln.split()
        if not parts:
            continue
        if not DATE_RE.match(parts[0]):
            continue

        # Exemplo (página 12):
        # 13-May-24 451 6 1.3% 526 6 1.2% 461 8 1.8% 438 9 2.1%
        # Queremos o preço CRC = 526 (após HRB price).
        # Estrutura: date, scrap_price, scrap_change, scrap_pct, hrb_price, hrb_change, hrb_pct, crc_price, ...
        try:
            date_s = parts[0]
            # Encontrar todos os inteiros na linha após a data, na ordem
            ints = [int(x.replace(",", "")) for x in parts[1:] if re.fullmatch(r"-?\d{1,3}(?:,\d{3})*|\d+", x)]
            # ints aqui devem começar com: [scrap_price, scrap_change, hrb_price, hrb_change, crc_price, crc_change, plate_price, plate_change, rebar_price, rebar_change]
            # Pela observação do PDF, o crc_price é o 5º inteiro.
            if len(ints) < 5:
                continue
            crc_price = ints[4]

            rows.append({
                "date": _parse_date(date_s).date(),
                "CRC Steel China (USD/TON)": float(crc_price),
            })
        except Exception:
            continue

    df = pd.DataFrame(rows).dropna()
    df = df.sort_values("date").reset_index(drop=True)
    return df
