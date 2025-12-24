import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def build_pdf_report(df: pd.DataFrame, out_path: str, title: str = "Índices Moveleiro") -> None:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    d = d.sort_values("date")

    last = d.iloc[-1]

    c = canvas.Canvas(out_path, pagesize=A4)
    w, h = A4

    y = h - 60
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)

    y -= 26
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Última atualização (data do relatório): {last['date'].date()}")

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Últimos valores")
    y -= 14
    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"CRC Steel China (USD/TON): {last.get('CRC Steel China (USD/TON)', '')}")
    y -= 12
    c.drawString(50, y, f"Iron Ore (USD/TON): {last.get('Iron Ore (USD/TON)', '')}")
    y -= 12
    c.drawString(50, y, f"USD/BRL: {last.get('USD/BRL', '')}")
    y -= 12
    c.drawString(50, y, f"USD/CNY: {last.get('USD/CNY', '')}")

    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Variações do CRC (aprox. por pontos do relatório)")
    y -= 14
    c.setFont("Helvetica", 10)
    for lab in ["1M %", "3M %", "6M %", "YoY %"]:
        v = last.get(lab, None)
        txt = "n/d" if pd.isna(v) else f"{v:.2f}%"
        c.drawString(50, y, f"{lab}: {txt}")
        y -= 12

    y -= 10
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Volatilidade")
    y -= 14
    c.setFont("Helvetica", 10)
    v = last.get("Volatilidade (6p) %", None)
    txt = "n/d" if pd.isna(v) else f"{v:.2f}%"
    c.drawString(50, y, f"Volatilidade (6p) %: {txt}")

    y -= 22
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Observações")
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(50, y, "- CRC extraído da tabela China Ex-works (página 12).")
    y -= 12
    c.drawString(50, y, "- Iron Ore, câmbio e demais séries são mapeadas para a data (ou último dia útil anterior).")

    c.showPage()
    c.save()

