import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def build_dashboard_html(df: pd.DataFrame, title: str = "Índices Moveleiro") -> str:
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])

    # Gráfico geral com eixos duplos (CRC + Iron Ore + Freight opcional + câmbios)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=d["date"], y=d["CRC Steel China (USD/TON)"],
        mode="lines+markers", name="CRC Steel China (USD/TON)",
        marker=dict(size=6)
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=d["date"], y=d["Iron Ore (USD/TON)"],
        mode="lines+markers", name="Iron Ore (USD/TON)",
        marker=dict(size=5)
    ), secondary_y=False)

    # Câmbio no eixo secundário
    fig.add_trace(go.Scatter(
        x=d["date"], y=d["USD/BRL"],
        mode="lines+markers", name="USD/BRL",
        marker=dict(size=5)
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=d["date"], y=d["USD/CNY"],
        mode="lines+markers", name="USD/CNY",
        marker=dict(size=5)
    ), secondary_y=True)

    fig.update_layout(
        title=title,
        height=650,
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_yaxes(title_text="USD/TON", secondary_y=False)
    fig.update_yaxes(title_text="Câmbio", secondary_y=True)

    # Gráfico variações (1M, 3M, 6M, YoY)
    fig_var = go.Figure()
    for col in ["1M %", "3M %", "6M %", "YoY %"]:
        fig_var.add_trace(go.Scatter(
            x=d["date"], y=d[col],
            mode="lines+markers", name=col, marker=dict(size=5)
        ))
    fig_var.update_layout(
        title="Variações do CRC (aprox. por pontos do relatório)",
        height=420,
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig_var.update_yaxes(title_text="%")

    # Volatilidade
    fig_vol = go.Figure()
    fig_vol.add_trace(go.Scatter(
        x=d["date"], y=d["Volatilidade (6p) %"],
        mode="lines+markers", name="Volatilidade (6p) %", marker=dict(size=5)
    ))
    fig_vol.update_layout(
        title="Volatilidade (rolling 6 pontos) — CRC",
        height=420,
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_white",
    )
    fig_vol.update_yaxes(title_text="%")

    # Correlações rolling
    fig_corr = go.Figure()
    for col in [
        "Corr Rolling 6p (CRC vs Iron Ore (USD/TON))",
        "Corr Rolling 6p (CRC vs USD/BRL)",
        "Corr Rolling 6p (CRC vs USD/CNY)"
    ]:
        fig_corr.add_trace(go.Scatter(
            x=d["date"], y=d[col],
            mode="lines+markers", name=col.replace("Corr Rolling 6p ", ""), marker=dict(size=5)
        ))
    fig_corr.update_layout(
        title="Correlação Rolling (6 pontos) — CRC vs Drivers",
        height=420,
        margin=dict(l=40, r=40, t=60, b=40),
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig_corr.update_yaxes(title_text="Pearson (rolling)")

    # HTML final
    html = f"""
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #dfe1e1;
      color: #111;
    }}
    .container {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 18px 14px 40px;
    }}
    .section {{
      background: #fff;
      border-radius: 14px;
      overflow: hidden;
      margin-bottom: 18px;
      box-shadow: 0 8px 22px rgba(0,0,0,.08);
    }}
    .bar {{
      background: #000;
      color: #fff;
      padding: 12px 14px;
      font-weight: 700;
      letter-spacing: .3px;
    }}
    .content {{
      padding: 12px 12px 16px;
    }}
    .hint {{
      font-size: 12px;
      opacity: .75;
      margin-top: 6px;
    }}
  </style>
</head>
<body>
  <div class="container">

    <div class="section">
      <div class="bar">Índices Moveleiro</div>
      <div class="content">
        <div id="fig_main"></div>
        <div class="hint">Fonte CRC: SteelBenchmarker (página 12) • Drivers: TradingEconomics, BCB/Olinda, FRED</div>
      </div>
    </div>

    <div class="section">
      <div class="bar">Variações do CRC (YoY, 6M, 3M, 1M)</div>
      <div class="content">
        <div id="fig_var"></div>
      </div>
    </div>

    <div class="section">
      <div class="bar">Volatilidade</div>
      <div class="content">
        <div id="fig_vol"></div>
      </div>
    </div>

    <div class="section">
      <div class="bar">Correlações (Pearson Rolling e Lag)</div>
      <div class="content">
        <div id="fig_corr"></div>
      </div>
    </div>

  </div>

<script>
  const fig_main = {fig.to_json()};
  const fig_var  = {fig_var.to_json()};
  const fig_vol  = {fig_vol.to_json()};
  const fig_corr = {fig_corr.to_json()};

  Plotly.newPlot("fig_main", fig_main.data, fig_main.layout, {{responsive: true}});
  Plotly.newPlot("fig_var",  fig_var.data,  fig_var.layout,  {{responsive: true}});
  Plotly.newPlot("fig_vol",  fig_vol.data,  fig_vol.layout,  {{responsive: true}});
  Plotly.newPlot("fig_corr", fig_corr.data, fig_corr.layout, {{responsive: true}});
</script>

</body>
</html>
"""
    return html
