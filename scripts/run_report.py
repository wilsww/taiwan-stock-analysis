#!/usr/bin/env python3
"""
run_report.py — Plan A 輕量版主入口
自動彙整：股價快照 + 月營收 + 技術指標 → Markdown 日報
輸出至 reports/YYYY-MM-DD_日報.md
"""

import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# 確保可 import 同目錄模組
sys.path.insert(0, str(Path(__file__).parent))

from fetch_prices import fetch_snapshot, WATCHLIST
from indicators import get_indicators

DATA_DIR   = Path(__file__).parent.parent / "data"
REVENUE_DIR = DATA_DIR / "revenue"
REPORT_DIR = Path(__file__).parent.parent / "reports" / "daily"
DB_PATH    = REVENUE_DIR / "revenue.db"

COMPANY_NAMES = {
    "2408": "南亞科技",
    "2344": "華邦電子",
    "3363": "上詮光纖",
    "2455": "全新光電",
    "4979": "華星光通",
    "3081": "聯亞光電",
    "3105": "穩懋半導體",
    "4919": "新唐科技",
    # 新增 CPO 光通訊標的
    "6442": "光聖",
    "4977": "眾達-KY",
    "3163": "波若威",
    "2345": "智邦",
    "6223": "旺矽",
    # IC 載板 PCB 標的
    "3037": "欣興電子",
    "8046": "南亞電路板",
    "3189": "景碩科技",
}

# ticker → yfinance symbol 映射（反查用）
TICKER_TO_SYM = {sym.split(".")[0]: sym for sym in WATCHLIST}


# ── 讀取 revenue.db ──────────────────────────────────────────
def load_latest_institutional(tickers: list[str]) -> dict:
    """從 revenue.db 讀取各標的最新一筆三大法人買賣超"""
    if not DB_PATH.exists():
        return {}
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # 確認資料表存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='institutional_flow'")
        if not c.fetchone():
            conn.close()
            return {}
        result = {}
        for ticker in tickers:
            c.execute("""
                SELECT trade_date, foreign_net, invest_net, dealer_net, total_net
                FROM institutional_flow
                WHERE ticker = ?
                ORDER BY trade_date DESC
                LIMIT 1
            """, (ticker,))
            row = c.fetchone()
            if row:
                result[ticker] = {
                    "trade_date":  row[0],
                    "foreign_net": row[1],
                    "invest_net":  row[2],
                    "dealer_net":  row[3],
                    "total_net":   row[4],
                }
        conn.close()
        return result
    except Exception:
        return {}


def load_latest_revenues(tickers: list[str]) -> dict:
    """從 revenue.db 讀取各標的最新一筆月營收"""
    if not DB_PATH.exists():
        return {}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    result = {}
    for ticker in tickers:
        c.execute("""
            SELECT year, month, revenue_m, mom_pct, yoy_pct, source
            FROM monthly_revenue
            WHERE ticker = ?
            ORDER BY year DESC, month DESC
            LIMIT 1
        """, (ticker,))
        row = c.fetchone()
        if row:
            result[ticker] = {
                "year":      row[0],
                "month":     row[1],
                "revenue_m": row[2],
                "mom_pct":   row[3],
                "yoy_pct":   row[4],
                "source":    row[5],
            }
    conn.close()
    return result


# ── 產生 Markdown 報告 ───────────────────────────────────────
def generate_report(
    prices: list[dict],
    revenues: dict,
    indicators: dict,
    report_date: str,
    institutional: Optional[dict] = None,
) -> str:
    lines = []
    lines.append(f"# 台股追蹤日報 — {report_date}")
    lines.append(f"\n> 自動產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("\n---\n")

    # ── 1. 股價快照 ──
    lines.append("## 1. 股價快照\n")
    lines.append("| 代碼 | 公司 | 收盤價 | 漲跌 | 漲跌幅 | 市值 |")
    lines.append("|------|------|-------:|-----:|-------:|------|")
    for r in prices:
        lines.append(
            f"| {r['代碼']} | {r['公司']} | {r['收盤價']} | "
            f"{r['漲跌']} | {r['漲跌幅']} | {r.get('市值','N/A')} |"
        )

    # ── 2. 月營收摘要 ──
    lines.append("\n## 2. 最新月營收（資料庫）\n")
    has_rev = any(t in revenues for t in COMPANY_NAMES)
    if has_rev:
        lines.append("| 代碼 | 公司 | 最新月份 | 營收（億） | MoM% | YoY% | 來源 |")
        lines.append("|------|------|----------|----------:|-----:|-----:|------|")
        for ticker, name in COMPANY_NAMES.items():
            rev = revenues.get(ticker)
            if rev:
                rev_b = rev["revenue_m"] / 1000 if rev["revenue_m"] else 0
                mom_s = f"{rev['mom_pct']:+.1f}%" if rev["mom_pct"] is not None else "N/A"
                yoy_s = f"{rev['yoy_pct']:+.1f}%" if rev["yoy_pct"] is not None else "N/A"
                lines.append(
                    f"| {ticker} | {name} | {rev['year']}年{rev['month']:02d}月 "
                    f"| **{rev_b:.2f}億** | {mom_s} | {yoy_s} | {rev['source']} |"
                )
            else:
                lines.append(f"| {ticker} | {name} | — | — | — | — | 無資料 |")
    else:
        lines.append("> ⚠️ revenue.db 無資料，請先執行 `fetch_revenue.py`")

    # ── 3. 技術指標 ──
    lines.append("\n## 3. 技術指標\n")
    lines.append("| 代碼 | RSI14 | 狀態 | MACD方向 | MA20偏離 | MA60偏離 | 趨勢判斷 |")
    lines.append("|------|------:|------|----------|--------:|--------:|----------|")
    for sym, ind in indicators.items():
        ticker = sym.split(".")[0]
        name   = COMPANY_NAMES.get(ticker, ticker)
        if "error" in ind:
            lines.append(f"| {ticker} | — | {ind['error'][:20]} | — | — | — | — |")
            continue
        ma20d = f"{ind['ma20_diff']:+.1f}%" if ind["ma20_diff"] is not None else "N/A"
        ma60d = f"{ind['ma60_diff']:+.1f}%" if ind["ma60_diff"] is not None else "N/A"
        lines.append(
            f"| {ticker} | {ind['rsi14']} | {ind['rsi_label']} | "
            f"{ind['macd_dir']} | {ma20d} | {ma60d} | {ind['trend']} |"
        )

    # ── 4. 風險預警 ──
    lines.append("\n## 4. 風險預警\n")
    warnings_list = []
    for sym, ind in indicators.items():
        if "error" in ind:
            continue
        ticker = sym.split(".")[0]
        name   = COMPANY_NAMES.get(ticker, ticker)
        if ind["rsi14"] >= 70:
            warnings_list.append(f"- ⚠️ **{name}（{ticker}）** RSI={ind['rsi14']}，進入超買區間，留意短線回檔風險")
        elif ind["rsi14"] <= 30:
            warnings_list.append(f"- 🟢 **{name}（{ticker}）** RSI={ind['rsi14']}，進入超賣區間，留意反彈機會")
        if ind["ma60_diff"] is not None and ind["ma60_diff"] < -10:
            warnings_list.append(f"- 🔴 **{name}（{ticker}）** 股價低於MA60達 {ind['ma60_diff']:.1f}%，中期趨勢偏弱")

    if warnings_list:
        lines.extend(warnings_list)
    else:
        lines.append("本日無特殊技術面預警。")

    # ── 5. 三大法人動向 ──
    lines.append("\n## 5. 三大法人動向\n")
    institutional = institutional or {}
    if institutional:
        # 取最新資料日期（取所有標的中最新的）
        latest_date = max(v["trade_date"] for v in institutional.values())
        lines.append(f"> 資料日期：{latest_date}　（單位：千股，正數=買超，負數=賣超）\n")
        lines.append("| 代碼 | 公司 | 外資 | 投信 | 自營商 | 三大合計 | 方向 |")
        lines.append("|------|------|-----:|-----:|-------:|---------:|------|")
        for ticker, name in COMPANY_NAMES.items():
            inst = institutional.get(ticker)
            if inst:
                foreign = inst["foreign_net"] or 0
                invest  = inst["invest_net"]  or 0
                dealer  = inst["dealer_net"]  or 0
                total   = inst["total_net"]   or 0
                direction = "↑ 買超" if total > 0 else ("↓ 賣超" if total < 0 else "→ 持平")
                lines.append(
                    f"| {ticker} | {name} | {foreign:,} | {invest:,} | {dealer:,} "
                    f"| **{total:,}** | {direction} |"
                )
            else:
                lines.append(f"| {ticker} | {name} | — | — | — | — | 無資料 |")
    else:
        lines.append("> ⚠️ 無三大法人資料，請先執行 `fetch_institutional.py`")

    # ── 6. 催化劑提醒（固定模板）──
    lines.append("\n## 6. 近期催化劑提醒\n")
    lines.append("| 時間軸 | 事件 | 相關標的 |")
    lines.append("|--------|------|---------|")
    lines.append("| 短線（M+0） | 台股月營收公布（每月10日前後） | 全部 |")
    lines.append("| 短線（M+1） | Hyperscaler Q1 法說會（4月底） | 南亞科、光通訊鏈 |")
    lines.append("| 中線（Q2） | 南亞科 2026 CapEx NT$500億董事會決議 | 2408 |")
    lines.append("| 中線（Q2） | 華邦電 16nm CMS 量產進度更新 | 2344 |")
    lines.append("| 長線 | 上詮 1.6T CPO FAU 系統廠驗證結果 | 3363 |")

    # ── 7. 操作備忘 ──
    lines.append("\n## 7. 操作備忘\n")
    lines.append("```bash")
    lines.append("# 更新月營收資料庫")
    lines.append("python3 scripts/fetch_revenue.py --ticker 3363 2455 4979 3081 3105 6442 4977 3163 2345 6223")
    lines.append("")
    lines.append("# 重新產生日報")
    lines.append("python3 scripts/run_report.py")
    lines.append("")
    lines.append("# 查看特定標的歷史 K 線")
    lines.append("python3 scripts/fetch_prices.py --history 2344.TW --period 6mo")
    lines.append("```")

    lines.append("\n---")
    lines.append(f"\n*Plan A 輕量版自動日報 | 資料來源：yfinance + revenue.db*")

    return "\n".join(lines)


# ── 主程式 ───────────────────────────────────────────────────
def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n🚀 台股追蹤日報產生中... ({today})")

    # Step 1: 股價
    print("  📈 抓取股價快照...")
    prices = fetch_snapshot()

    # Step 2: 月營收
    print("  💰 讀取月營收資料庫...")
    tickers = list(COMPANY_NAMES.keys())
    revenues = load_latest_revenues(tickers)
    rev_count = len(revenues)
    print(f"     → 找到 {rev_count} 筆記錄")

    # Step 3: 三大法人動向
    print("  🏦 讀取三大法人資料庫...")
    institutional = load_latest_institutional(tickers)
    inst_count = len(institutional)
    print(f"     → 找到 {inst_count} 筆記錄")

    # Step 4: 技術指標
    print("  📊 計算技術指標...")
    indicators = {}
    for sym in WATCHLIST:
        ticker = sym.split(".")[0]
        print(f"     → {sym}...", end=" ", flush=True)
        ind = get_indicators(sym)
        indicators[sym] = ind
        if "error" in ind:
            print(f"ERROR: {ind['error'][:30]}")
        else:
            print(f"RSI={ind['rsi14']} {ind['trend']}")

    # Step 5: 產生報告
    print("  📝 產生 Markdown 報告...")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_text = generate_report(prices, revenues, indicators, today, institutional)

    output_path = REPORT_DIR / f"{today}_日報.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\n✅ 報告已儲存：{output_path}")
    print(f"   股價：{len(prices)} 筆 | 月營收：{rev_count} 筆 | 三大法人：{inst_count} 筆 | 技術指標：{len(indicators)} 筆")
    print()

    # 預覽前 30 行
    preview_lines = report_text.split("\n")[:30]
    print("── 報告預覽（前30行）" + "─" * 40)
    print("\n".join(preview_lines))
    print("─" * 60)


if __name__ == "__main__":
    main()
