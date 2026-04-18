#!/usr/bin/env python3
"""
run_report_b.py — Plan B 主入口
平行擷取 + 即時月營收爬取 + 過濾閘門 + HTML + Markdown 輸出
Terminal 彩色輸出（ANSI）
"""

import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fetch_prices  import fetch_snapshot, WATCHLIST
from indicators    import get_indicators
from revenue_live  import fetch_revenue_live, save_to_db, COMPANY_NAMES
from render_html   import generate_html

REPORT_DIR = Path(__file__).parent.parent / "reports" / "daily"

# ── ANSI 色碼 ──────────────────────────────────────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    RED    = "\033[91m"
    GREEN  = "\033[92m"
    YELLOW = "\033[93m"
    CYAN   = "\033[96m"
    GRAY   = "\033[90m"
    WHITE  = "\033[97m"

def cprint(msg: str, color: str = C.WHITE):
    print(f"{color}{msg}{C.RESET}")

def pct_color(val) -> str:
    if val is None:
        return C.GRAY
    return C.GREEN if val > 0 else (C.RED if val < 0 else C.GRAY)


# ── 過濾閘門 ───────────────────────────────────────────────
LARGE_MOVE_THRESHOLD = 3.0  # % 絕對值

def apply_filter_gate(prices: list[dict], revenues: dict, indicators: dict) -> dict:
    """
    回傳 {ticker: [flag, ...]}
    flag: "large_move", "revenue_update", "overbought", "oversold", "below_ma60"
    """
    flags = {}
    # 解析漲跌幅
    for r in prices:
        ticker = r["代碼"].split(".")[0]
        try:
            pct = float(r["漲跌幅"].replace("%", "").replace("+", ""))
            if abs(pct) >= LARGE_MOVE_THRESHOLD:
                flags.setdefault(ticker, []).append("large_move")
        except Exception:
            pass

    # 月營收更新（fresh = 從網路即時取得）
    for ticker, rv in revenues.items():
        if rv and rv.get("fresh"):
            flags.setdefault(ticker, []).append("revenue_update")

    # RSI 超買/超賣
    for sym, ind in indicators.items():
        ticker = sym.split(".")[0]
        if "error" in ind:
            continue
        rsi = ind.get("rsi14")
        if rsi and rsi >= 70:
            flags.setdefault(ticker, []).append("overbought")
        elif rsi and rsi <= 30:
            flags.setdefault(ticker, []).append("oversold")
        ma60d = ind.get("ma60_diff")
        if ma60d is not None and ma60d < -10:
            flags.setdefault(ticker, []).append("below_ma60")

    return flags


# ── 平行擷取 ───────────────────────────────────────────────
def _fetch_one_revenue(ticker: str):
    return ticker, fetch_revenue_live(ticker)

def _fetch_one_indicator(sym: str):
    return sym, get_indicators(sym)

def parallel_fetch(tickers: list[str], symbols: list[str]) -> tuple:
    """同時抓月營收 + 技術指標，回傳 (revenues, indicators)"""
    revenues   = {}
    indicators = {}

    with ThreadPoolExecutor(max_workers=8) as ex:
        rev_futs = {ex.submit(_fetch_one_revenue, t): ("rev", t)  for t in tickers}
        ind_futs = {ex.submit(_fetch_one_indicator, s): ("ind", s) for s in symbols}
        all_futs = {**rev_futs, **ind_futs}

        for fut in as_completed(all_futs):
            kind, key = all_futs[fut]
            try:
                _, result = fut.result()
                if kind == "rev":
                    revenues[key] = result
                else:
                    indicators[key] = result
            except Exception as e:
                if kind == "rev":
                    revenues[key] = None
                else:
                    indicators[key] = {"sym": key, "error": str(e)[:50]}

    return revenues, indicators


# ── Terminal 彩色報表 ──────────────────────────────────────
def print_terminal_report(prices, revenues, indicators, alerts, report_date):
    print()
    cprint(f"{'═'*70}", C.CYAN)
    cprint(f"  台股追蹤日報　{report_date}　｜　Plan B", C.BOLD + C.CYAN)
    cprint(f"{'═'*70}", C.CYAN)

    # 股價
    cprint("\n  ── 股價快照 ──", C.YELLOW)
    cprint(f"  {'代碼':<12} {'公司':<10} {'收盤價':>10} {'漲跌':>8} {'漲跌幅':>9} {'市值':>10}", C.GRAY)
    cprint("  " + "─" * 62, C.GRAY)
    for r in prices:
        ticker = r["代碼"].split(".")[0]
        try:
            pct = float(r["漲跌幅"].replace("%","").replace("+",""))
            col = C.GREEN if pct >= 0 else C.RED
        except Exception:
            col = C.GRAY
        flag_str = " ⚡" if "large_move" in alerts.get(ticker, []) else ""
        cprint(f"  {r['代碼']:<12} {r['公司']:<10} {r['收盤價']:>10} "
               f"{r['漲跌']:>8} {r['漲跌幅']:>9} {r.get('市值','N/A'):>10}{flag_str}", col)

    # 月營收
    cprint("\n  ── 月營收（即時）──", C.YELLOW)
    cprint(f"  {'代碼':<6} {'公司':<10} {'月份':<12} {'營收':>10} {'MoM%':>8} {'YoY%':>8}  {'來源'}", C.GRAY)
    cprint("  " + "─" * 68, C.GRAY)
    for ticker in COMPANY_NAMES:
        rv = revenues.get(ticker)
        if rv:
            rev_b = rv.get("revenue_b", 0)
            mom   = rv.get("mom_pct")
            yoy   = rv.get("yoy_pct")
            mom_s = f"{mom:+.1f}%" if mom is not None else "N/A"
            yoy_s = f"{yoy:+.1f}%" if yoy is not None else "N/A"
            fresh = "🟢" if rv.get("fresh") else "🔵"
            yoy_col = pct_color(yoy)
            mom_col = pct_color(mom)
            line = (f"  {ticker:<6} {rv['company']:<10} "
                    f"{rv['year']}年{rv['month']:02d}月  NT${rev_b:>7.2f}億  ")
            print(f"{line}"
                  f"{C.RESET}{mom_col}{mom_s:>8}{C.RESET} "
                  f"{yoy_col}{yoy_s:>8}{C.RESET}  {fresh} {rv['source']}")
        else:
            cprint(f"  {ticker:<6} {COMPANY_NAMES[ticker]:<10} 無資料", C.GRAY)

    # 技術指標（僅有警示的標的）
    flagged = [sym for sym in indicators if any(
        f in alerts.get(sym.split(".")[0], [])
        for f in ("overbought","oversold","below_ma60","large_move")
    )]
    if flagged:
        cprint("\n  ── 技術指標（有警示標的）──", C.YELLOW)
        for sym in flagged:
            ind = indicators[sym]
            if "error" in ind:
                continue
            ticker = sym.split(".")[0]
            rsi    = ind.get("rsi14","N/A")
            trend  = ind.get("trend","N/A")
            ma60d  = ind.get("ma60_diff")
            ma60s  = f"{ma60d:+.1f}%" if ma60d is not None else "N/A"
            col    = C.RED if ma60d and ma60d < 0 else C.GREEN
            cprint(f"  {sym:<12}  RSI={rsi}  MA60偏離={ma60s}  {trend}", col)

    # 警示摘要
    if any(alerts.values()):
        cprint("\n  ── 警示摘要 ──", C.RED)
        for ticker, fs in alerts.items():
            if fs:
                label = COMPANY_NAMES.get(ticker, ticker)
                tags  = " | ".join(fs)
                cprint(f"  ⚡ {ticker} {label:<10} {tags}", C.RED)
    else:
        cprint("\n  ✅ 無特殊警示", C.GREEN)

    cprint(f"\n{'═'*70}\n", C.CYAN)


# ── Markdown 輸出 ─────────────────────────────────────────
def generate_md(prices, revenues, indicators, alerts, report_date):
    lines = [
        f"# 台股追蹤日報 — {report_date}（方案B）",
        f"\n> 自動產生：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "\n---\n",
    ]

    # 警示
    flagged_items = [(t, f) for t, fs in alerts.items() for f in fs]
    if flagged_items:
        lines.append("## ⚠️ 今日警示\n")
        for ticker, flag in flagged_items:
            name = COMPANY_NAMES.get(ticker, ticker)
            lines.append(f"- **{name}（{ticker}）** `{flag}`")
        lines.append("")

    # 股價
    lines += [
        "## 1. 股價快照\n",
        "| 代碼 | 公司 | 收盤價 | 漲跌 | 漲跌幅 | 市值 | 標記 |",
        "|------|------|-------:|-----:|-------:|------|------|",
    ]
    for r in prices:
        ticker = r["代碼"].split(".")[0]
        flag_str = ", ".join(alerts.get(ticker, [])) or "—"
        lines.append(
            f"| {r['代碼']} | {r['公司']} | {r['收盤價']} | "
            f"{r['漲跌']} | **{r['漲跌幅']}** | {r.get('市值','N/A')} | {flag_str} |"
        )

    # 月營收
    lines += [
        "\n## 2. 最新月營收（即時爬取）\n",
        "| 代碼 | 公司 | 月份 | 營收（億） | MoM% | YoY% | 來源 |",
        "|------|------|------|----------:|-----:|-----:|------|",
    ]
    for ticker in COMPANY_NAMES:
        rv = revenues.get(ticker)
        if rv:
            mom_s = f"{rv['mom_pct']:+.1f}%" if rv.get("mom_pct") is not None else "N/A"
            yoy_s = f"{rv['yoy_pct']:+.1f}%" if rv.get("yoy_pct") is not None else "N/A"
            fresh = "🟢" if rv.get("fresh") else "🔵"
            lines.append(
                f"| {ticker} | {rv['company']} | {rv['year']}年{rv['month']:02d}月 "
                f"| **{rv['revenue_b']:.2f}億** | {mom_s} | {yoy_s} | {fresh} {rv['source']} |"
            )
        else:
            lines.append(f"| {ticker} | {COMPANY_NAMES[ticker]} | — | — | — | — | 無資料 |")

    # 技術指標
    lines += [
        "\n## 3. 技術指標\n",
        "| 代碼 | RSI14 | 狀態 | MACD | MA20偏離 | MA60偏離 | 趨勢 |",
        "|------|------:|------|------|--------:|--------:|------|",
    ]
    for sym, ind in indicators.items():
        ticker = sym.split(".")[0]
        if "error" in ind:
            lines.append(f"| {ticker} | — | ERROR | — | — | — | — |")
            continue
        ma20d = f"{ind['ma20_diff']:+.1f}%" if ind.get("ma20_diff") is not None else "N/A"
        ma60d = f"{ind['ma60_diff']:+.1f}%" if ind.get("ma60_diff") is not None else "N/A"
        lines.append(
            f"| {ticker} | {ind['rsi14']} | {ind['rsi_label']} | "
            f"{ind['macd_dir']} | {ma20d} | {ma60d} | {ind['trend']} |"
        )

    lines += [
        "\n---",
        f"\n*Plan B 自動日報 | yfinance + winvest.tw + histock.tw*",
    ]
    return "\n".join(lines)


# ── 主程式 ───────────────────────────────────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    cprint(f"\n🚀  Plan B 日報產生中... ({today})", C.CYAN + C.BOLD)

    # Step 1: 股價（序列，yfinance batch 較快）
    cprint("  📈 抓取股價快照...", C.GRAY)
    prices = fetch_snapshot()
    cprint(f"     → {len(prices)} 筆", C.GRAY)

    # Step 2: 平行抓月營收 + 技術指標
    cprint("  ⚡ 平行擷取：月營收（winvest.tw）+ 技術指標（yfinance）...", C.GRAY)
    tickers = list(COMPANY_NAMES.keys())
    symbols = list(WATCHLIST.keys())
    revenues, indicators = parallel_fetch(tickers, symbols)

    rev_ok  = sum(1 for v in revenues.values() if v)
    ind_ok  = sum(1 for v in indicators.values() if "error" not in v)
    fresh_n = sum(1 for v in revenues.values() if v and v.get("fresh"))
    cprint(f"     → 月營收：{rev_ok}/{len(tickers)} 筆（即時：{fresh_n}）", C.GRAY)
    cprint(f"     → 技術指標：{ind_ok}/{len(symbols)} 筆", C.GRAY)

    # 將成功爬取的月營收存回 DB
    saved = 0
    for rv in revenues.values():
        if rv and rv.get("fresh"):
            try:
                save_to_db(rv)
                saved += 1
            except Exception:
                pass
    if saved:
        cprint(f"     → 已存回 revenue.db：{saved} 筆", C.GRAY)

    # Step 3: 過濾閘門
    alerts = apply_filter_gate(prices, revenues, indicators)
    total_alerts = sum(len(v) for v in alerts.values())
    cprint(f"  🚨 過濾閘門：{total_alerts} 項警示", C.YELLOW if total_alerts else C.GRAY)

    # Step 4: Terminal 彩色報表
    print_terminal_report(prices, revenues, indicators, alerts, today)

    # Step 5: 產生 Markdown
    md_text  = generate_md(prices, revenues, indicators, alerts, today)
    md_path  = REPORT_DIR / f"{today}_日報_B.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_text)

    # Step 6: 產生 HTML
    html_text = generate_html(prices, revenues, indicators, alerts, today)
    html_path = REPORT_DIR / f"{today}_日報_B.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)

    cprint(f"✅  Markdown：{md_path}", C.GREEN)
    cprint(f"✅  HTML    ：{html_path}", C.GREEN)
    cprint(f"   瀏覽器開啟：open '{html_path}'\n", C.GRAY)


if __name__ == "__main__":
    main()
