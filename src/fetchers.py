def load_iron_ore_from_csv_for_dates(uploaded_file, dates: list[date]) -> pd.DataFrame:
    """
    Reads uploaded Iron Ore CSV and returns:
      date (CRC dates) + Iron Ore (USD/TON)

    Uses only the first 2 columns of the CSV: Date and Price.
    If the exact date is missing, uses nearest previous available date (up to 30 days).
    """
    content = uploaded_file.getvalue()

    # Try sniff delimiter automatically (works for comma/semicolon/tab)
    df = pd.read_csv(io.BytesIO(content), sep=None, engine="python")

    if df.shape[1] < 2:
        return pd.DataFrame({"date": dates, "Iron Ore (USD/TON)": [np.nan] * len(dates)})

    dcol = df.columns[0]
    pcol = df.columns[1]

    tmp = df[[dcol, pcol]].copy()
    tmp.columns = ["Date", "Price"]

    # ---- DATE PARSING (robust) ----
    # First attempt (US style / month-first)
    dt1 = pd.to_datetime(tmp["Date"], errors="coerce", dayfirst=False)

    # If too many NaT, try dayfirst=True (Brazil/Europe style)
    if dt1.notna().mean() < 0.6:
        dt2 = pd.to_datetime(tmp["Date"], errors="coerce", dayfirst=True)
        tmp["Date"] = dt2
    else:
        tmp["Date"] = dt1

    # ---- PRICE PARSING (robust) ----
    # Remove currency symbols, thousands separators, spaces
    tmp["Price"] = (
        tmp["Price"]
        .astype(str)
        .str.replace(r"[^\d\.\-]", "", regex=True)  # keeps digits, dot, minus
    )
    tmp["Price"] = pd.to_numeric(tmp["Price"], errors="coerce")

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
