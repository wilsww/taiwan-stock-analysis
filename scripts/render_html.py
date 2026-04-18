#!/usr/bin/env python3
"""
render_html.py — 靜態 HTML 儀表板產生器（方案B）
深色主題 #0f172a，單一自包含 HTML 檔案
"""

from datetime import datetime


def _color_pct(val, threshold: float = 0.0) -> str:
    """回傳帶顏色的百分比字串（HTML span）"""
    if val is None:
        return '<span class="na">N/A</span>'
    color = "#4ade80" if val > threshold else ("#f87171" if val < threshold else "#94a3b8")
    sign  = "+" if val > 0 else ""
    return f'<span style="color:{color};font-weight:600">{sign}{val:.2f}%</span>'


def _color_val(val, fmt: str = ".1f") -> str:
    if val is None:
        return '<span class="na">N/A</span>'
    color = "#4ade80" if val > 0 else ("#f87171" if val < 0 else "#94a3b8")
    sign  = "+" if val > 0 else ""
    return f'<span style="color:{color}">{sign}{val:{fmt}}</span>'


def _rsi_badge(rsi) -> str:
    if rsi is None:
        return '<span class="badge gray">N/A</span>'
    if rsi >= 70:
        color, label = "#f87171", "超買"
    elif rsi <= 30:
        color, label = "#4ade80", "超賣"
    elif rsi >= 55:
        color, label = "#fb923c", "偏強"
    elif rsi <= 45:
        color, label = "#60a5fa", "偏弱"
    else:
        color, label = "#94a3b8", "中性"
    return (f'<span style="background:{color}22;color:{color};'
            f'padding:2px 8px;border-radius:4px;font-size:0.8em">'
            f'{rsi} {label}</span>')


def _alert_chip(flags: list[str]) -> str:
    chips = []
    for f in flags:
        if f == "large_move":
            chips.append('<span class="chip red">大波動</span>')
        elif f == "revenue_update":
            chips.append('<span class="chip green">營收更新</span>')
        elif f == "overbought":
            chips.append('<span class="chip orange">超買</span>')
        elif f == "oversold":
            chips.append('<span class="chip blue">超賣</span>')
        elif f == "below_ma60":
            chips.append('<span class="chip red">跌破MA60</span>')
    return " ".join(chips) if chips else '<span class="na">—</span>'


def generate_html(
    prices: list[dict],
    revenues: dict,
    indicators: dict,
    alerts: dict,
    report_date: str,
) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ── 股價表格列 ──
    price_rows = ""
    for r in prices:
        sym    = r["代碼"]
        ticker = sym.split(".")[0]
        flags  = alerts.get(ticker, [])
        row_class = "row-alert" if flags else ""
        chg_pct = r.get("漲跌幅", "N/A")
        # 解析顏色
        try:
            pct_val = float(chg_pct.replace("%", "").replace("+", ""))
            pct_color = "#4ade80" if pct_val >= 0 else "#f87171"
        except Exception:
            pct_color = "#94a3b8"
            pct_val   = 0
        price_rows += f"""
        <tr class="{row_class}">
            <td><code>{sym}</code></td>
            <td>{r['公司']}</td>
            <td class="num">{r['收盤價']}</td>
            <td class="num" style="color:{pct_color}">{r['漲跌']}</td>
            <td class="num" style="color:{pct_color};font-weight:600">{chg_pct}</td>
            <td class="num">{r.get('市值','N/A')}</td>
            <td>{_alert_chip(flags)}</td>
        </tr>"""

    # ── 月營收表格列 ──
    rev_rows = ""
    for ticker, rv in revenues.items():
        if rv is None:
            rev_rows += f"""
        <tr>
            <td><code>{ticker}</code></td>
            <td colspan="6" class="na">無資料</td>
        </tr>"""
            continue
        fresh_dot = '<span style="color:#4ade80">●</span>' if rv.get("fresh") else '<span style="color:#60a5fa">○</span>'
        rev_rows += f"""
        <tr>
            <td><code>{ticker}</code></td>
            <td>{rv['company']}</td>
            <td class="num">{rv['year']}年{rv['month']:02d}月</td>
            <td class="num"><strong>NT${rv['revenue_b']:.2f}億</strong></td>
            <td class="num">{_color_pct(rv.get('mom_pct'))}</td>
            <td class="num">{_color_pct(rv.get('yoy_pct'))}</td>
            <td>{fresh_dot} {rv['source']}</td>
        </tr>"""

    # ── 技術指標表格列 ──
    ind_rows = ""
    for sym, ind in indicators.items():
        ticker = sym.split(".")[0]
        if "error" in ind:
            ind_rows += f"""
        <tr>
            <td><code>{ticker}</code></td>
            <td colspan="6" class="na">ERROR: {ind['error'][:40]}</td>
        </tr>"""
            continue
        ma20d = _color_val(ind.get("ma20_diff"), ".1f")
        ma60d = _color_val(ind.get("ma60_diff"), ".1f")
        macd_color = "#4ade80" if "金叉" in ind.get("macd_dir","") else "#f87171"
        ind_rows += f"""
        <tr>
            <td><code>{ticker}</code></td>
            <td>{_rsi_badge(ind.get('rsi14'))}</td>
            <td style="color:{macd_color};font-weight:600">{ind.get('macd_dir','N/A')}</td>
            <td class="num">{ind.get('ma20','N/A')}</td>
            <td class="num">{ma20d}%</td>
            <td class="num">{ma60d}%</td>
            <td>{ind.get('trend','N/A')}</td>
        </tr>"""

    # ── 警示卡片 ──
    alert_cards = ""
    all_flags = [(t, f) for t, fs in alerts.items() for f in fs]
    if all_flags:
        for ticker, flag in all_flags:
            ind = indicators.get(
                next((s for s in indicators if s.startswith(ticker)), ""), {}
            )
            rev = revenues.get(ticker)
            if flag == "large_move":
                pr = next((r for r in prices if r["代碼"].startswith(ticker)), {})
                alert_cards += f"""
            <div class="alert-card red">
                <div class="alert-title">⚡ 大波動警示 — {ticker}</div>
                <div>今日漲跌幅：<strong>{pr.get('漲跌幅','N/A')}</strong>（閾值 ±3%）</div>
            </div>"""
            elif flag == "revenue_update" and rev:
                yoy_s = f"{rev['yoy_pct']:+.1f}%" if rev.get("yoy_pct") is not None else "N/A"
                alert_cards += f"""
            <div class="alert-card green">
                <div class="alert-title">📊 月營收更新 — {ticker} {rev['company']}</div>
                <div>{rev['year']}年{rev['month']:02d}月 NT${rev['revenue_b']:.2f}億｜YoY <strong>{yoy_s}</strong></div>
            </div>"""
            elif flag == "overbought":
                rsi_val = ind.get("rsi14", "N/A")
                alert_cards += f"""
            <div class="alert-card orange">
                <div class="alert-title">🔺 RSI 超買 — {ticker}</div>
                <div>RSI(14) = <strong>{rsi_val}</strong>，留意短線回檔</div>
            </div>"""
            elif flag == "oversold":
                rsi_val = ind.get("rsi14", "N/A")
                alert_cards += f"""
            <div class="alert-card blue">
                <div class="alert-title">🔻 RSI 超賣 — {ticker}</div>
                <div>RSI(14) = <strong>{rsi_val}</strong>，留意反彈機會</div>
            </div>"""
            elif flag == "below_ma60":
                ma60d = ind.get("ma60_diff", 0)
                alert_cards += f"""
            <div class="alert-card red">
                <div class="alert-title">📉 跌破 MA60 — {ticker}</div>
                <div>股價低於 MA60 達 <strong>{ma60d:.1f}%</strong>，中期趨勢偏弱</div>
            </div>"""
    else:
        alert_cards = '<div class="no-alert">✅ 本日無特殊技術面或基本面警示</div>'

    html = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>台股追蹤日報 — {report_date}</title>
<style>
  :root {{
    --bg:      #0f172a;
    --bg2:     #1e293b;
    --bg3:     #334155;
    --text:    #e2e8f0;
    --muted:   #94a3b8;
    --accent:  #38bdf8;
    --border:  #334155;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
    padding: 24px;
  }}
  h1 {{
    font-size: 1.4em;
    color: var(--accent);
    margin-bottom: 4px;
  }}
  .subtitle {{ color: var(--muted); font-size: 0.85em; margin-bottom: 24px; }}
  h2 {{
    font-size: 1em;
    color: var(--accent);
    margin: 28px 0 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
    letter-spacing: 0.05em;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 8px;
  }}
  thead th {{
    background: var(--bg3);
    color: var(--muted);
    padding: 8px 12px;
    text-align: left;
    font-weight: 500;
    font-size: 0.8em;
    letter-spacing: 0.06em;
  }}
  tbody tr {{ border-bottom: 1px solid var(--border); }}
  tbody tr:hover {{ background: var(--bg2); }}
  tbody tr.row-alert {{ background: #1e293b88; }}
  td {{
    padding: 8px 12px;
    color: var(--text);
    vertical-align: middle;
  }}
  td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  code {{
    background: var(--bg3);
    padding: 1px 5px;
    border-radius: 3px;
    font-size: 0.9em;
    color: var(--accent);
  }}
  .na {{ color: var(--muted); }}
  .chip {{
    display: inline-block;
    padding: 1px 7px;
    border-radius: 4px;
    font-size: 0.75em;
    font-weight: 600;
    margin: 1px;
  }}
  .chip.red    {{ background: #f8717122; color: #f87171; }}
  .chip.green  {{ background: #4ade8022; color: #4ade80; }}
  .chip.orange {{ background: #fb923c22; color: #fb923c; }}
  .chip.blue   {{ background: #60a5fa22; color: #60a5fa; }}
  .alerts-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
    margin-top: 12px;
  }}
  .alert-card {{
    background: var(--bg2);
    border-radius: 8px;
    padding: 14px 16px;
    border-left: 3px solid;
  }}
  .alert-card.red    {{ border-color: #f87171; }}
  .alert-card.green  {{ border-color: #4ade80; }}
  .alert-card.orange {{ border-color: #fb923c; }}
  .alert-card.blue   {{ border-color: #60a5fa; }}
  .alert-title {{
    font-weight: 700;
    margin-bottom: 4px;
    font-size: 0.9em;
  }}
  .no-alert {{
    color: #4ade80;
    background: #4ade8011;
    border: 1px solid #4ade8033;
    border-radius: 6px;
    padding: 10px 16px;
  }}
  .footer {{
    margin-top: 40px;
    color: var(--muted);
    font-size: 0.8em;
    border-top: 1px solid var(--border);
    padding-top: 12px;
  }}
  strong {{ color: #f1f5f9; }}
</style>
</head>
<body>
<h1>📊 台股追蹤日報 — {report_date}</h1>
<div class="subtitle">自動產生：{now_str}　｜　方案B 平行擷取版</div>

<h2>⚠️ 今日警示</h2>
<div class="alerts-grid">
{alert_cards}
</div>

<h2>1. 股價快照</h2>
<table>
  <thead>
    <tr>
      <th>代碼</th><th>公司</th><th>收盤價</th><th>漲跌</th><th>漲跌幅</th><th>市值</th><th>標記</th>
    </tr>
  </thead>
  <tbody>{price_rows}</tbody>
</table>

<h2>2. 最新月營收（即時爬取）</h2>
<table>
  <thead>
    <tr>
      <th>代碼</th><th>公司</th><th>月份</th><th>營收</th><th>MoM%</th><th>YoY%</th><th>來源</th>
    </tr>
  </thead>
  <tbody>{rev_rows}</tbody>
</table>
<div style="color:var(--muted);font-size:0.8em;margin-top:4px">
  ● 本次即時爬取　○ 來自本地資料庫
</div>

<h2>3. 技術指標</h2>
<table>
  <thead>
    <tr>
      <th>代碼</th><th>RSI(14)</th><th>MACD</th><th>MA20</th><th>MA20 偏離</th><th>MA60 偏離</th><th>趨勢</th>
    </tr>
  </thead>
  <tbody>{ind_rows}</tbody>
</table>

<h2>4. 催化劑提醒</h2>
<table>
  <thead><tr><th>時間軸</th><th>事件</th><th>相關標的</th></tr></thead>
  <tbody>
    <tr><td>短線（M+0）</td><td>台股月營收公布（每月10日前後）</td><td>全部</td></tr>
    <tr><td>短線（M+1）</td><td>Hyperscaler Q1 法說會（4月底）</td><td>南亞科、光通訊鏈</td></tr>
    <tr><td>中線（Q2）</td><td>南亞科 2026 CapEx NT$500億 董事會決議</td><td><code>2408</code></td></tr>
    <tr><td>中線（Q2）</td><td>華邦電 16nm CMS 量產進度</td><td><code>2344</code></td></tr>
    <tr><td>長線</td><td>上詮 1.6T CPO FAU 系統廠驗證結果</td><td><code>3363</code></td></tr>
  </tbody>
</table>

<div class="footer">
  Plan B 輕量版自動日報　｜　資料來源：yfinance + winvest.tw + histock.tw + revenue.db
</div>
</body>
</html>"""
    return html
