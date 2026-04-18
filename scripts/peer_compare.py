#!/usr/bin/env python3
"""
peer_compare.py — 台灣追蹤標的 vs 美股同業相關性對照

功能：
  1. 抓取美股參考標的（MU、SNDK、LITE、COHR、NVDA）最新股價與近期表現
  2. 抓取台灣核心追蹤標的近期表現
  3. 計算 60 日價格相關性矩陣
  4. 輸出 Markdown 報告 → reports/peer_compare_{YYYYMMDD}.md

用法：
  python3 scripts/peer_compare.py
  python3 scripts/peer_compare.py --days 30    # 改用 30 日相關性
  python3 scripts/peer_compare.py --no-report  # 只顯示，不寫檔
"""

import argparse
import warnings
from datetime import datetime, date, timedelta
from pathlib import Path

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
except ImportError:
    print("❌ 需要安裝 yfinance：pip install yfinance")
    raise

# ── 設定 ──────────────────────────────────────────────────────
REPORT_DIR = Path(__file__).parent.parent / "reports"

# 美股參考標的
US_PEERS = {
    "MU":    "Micron（DRAM/HBM 全球指標）",
    "SNDK":  "SanDisk（NAND 週期參照）",
    "LITE":  "Lumentum（CPO 光通訊）",
    "COHR":  "Coherent（CPO 光通訊）",
    "NVDA":  "NVIDIA（AI CapEx 領先指標）",
}

# 台灣核心標的（按主題分組）
TW_CORE = {
    # DRAM
    "2408.TW":  ("南亞科技", "DRAM"),
    "2344.TW":  ("華邦電子", "DRAM"),
    # CPO
    "3363.TWO": ("上詮光纖", "CPO"),
    "2455.TW":  ("全新光電", "CPO"),
    "4979.TWO": ("華星光通", "CPO"),
    "3081.TWO": ("聯亞光電", "CPO"),
    "3105.TWO": ("穩懋半導體", "CPO"),
    # ABF
    "3037.TW":  ("欣興電子", "ABF"),
    "8046.TW":  ("南電", "ABF"),
    "3189.TW":  ("景碩科技", "ABF"),
}

# 相關性解讀
CORR_LABELS = {
    (0.7, 1.0):   "強正相關 ↑",
    (0.4, 0.7):   "中正相關 ↗",
    (0.0, 0.4):   "弱相關 →",
    (-0.4, 0.0):  "弱負相關 ←",
    (-1.0, -0.4): "強負相關 ↓",
}


def corr_label(c: float) -> str:
    for (lo, hi), label in CORR_LABELS.items():
        if lo <= c <= hi:
            return label
    return "—"


def fetch_prices(symbols: list[str], days: int) -> "dict[str, list[float]]":
    """用 yfinance 批量抓收盤價，回傳 {symbol: [price...]}"""
    end   = date.today()
    start = end - timedelta(days=days + 10)  # 多抓幾天補假日

    try:
        raw = yf.download(
            symbols,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        print(f"  ⚠️  yfinance 下載失敗：{e}")
        return {}

    if raw.empty:
        return {}

    close = raw["Close"] if len(symbols) > 1 else raw[["Close"]].rename(columns={"Close": symbols[0]})
    result = {}
    for sym in symbols:
        if sym in close.columns:
            series = close[sym].dropna().tail(days).tolist()
            result[sym] = series
    return result


def compute_correlation(price_a: list[float], price_b: list[float]) -> float:
    """計算 Pearson 相關係數（使用日漲跌幅）"""
    n = min(len(price_a), len(price_b))
    if n < 5:
        return float("nan")

    # 日漲跌幅
    def pct_changes(prices):
        return [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]

    a = pct_changes(price_a[-n:])
    b = pct_changes(price_b[-n:])
    nn = min(len(a), len(b))
    a, b = a[:nn], b[:nn]

    mean_a = sum(a) / nn
    mean_b = sum(b) / nn
    cov  = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(nn)) / nn
    std_a = (sum((x - mean_a) ** 2 for x in a) / nn) ** 0.5
    std_b = (sum((x - mean_b) ** 2 for x in b) / nn) ** 0.5

    if std_a == 0 or std_b == 0:
        return float("nan")
    return round(cov / (std_a * std_b), 3)


def pct_change_total(prices: list[float]) -> float:
    """計算區間總漲跌幅 %"""
    if len(prices) < 2:
        return float("nan")
    return round((prices[-1] - prices[0]) / prices[0] * 100, 1)


def generate_report(us_data: dict, tw_data: dict, days: int) -> str:
    today = date.today().strftime("%Y-%m-%d")

    lines = [
        f"# 同業比較報告 — {today}（{days} 日）",
        "",
        "> 美股領先指標 vs 台灣追蹤標的 | 資料來源：Yahoo Finance",
        "",
        "---",
        "",
        "## 美股同業近期表現",
        "",
        f"| 代號 | 說明 | 現價 | {days} 日漲跌 |",
        "|------|------|------|-------------|",
    ]

    for sym, desc in US_PEERS.items():
        prices = us_data.get(sym, [])
        if prices:
            chg = pct_change_total(prices)
            sign = "+" if chg >= 0 else ""
            lines.append(f"| {sym} | {desc} | ${prices[-1]:.2f} | {sign}{chg}% |")
        else:
            lines.append(f"| {sym} | {desc} | — | — |")

    lines += [
        "",
        "---",
        "",
        "## 台灣核心標的近期表現",
        "",
        f"| 代碼 | 公司 | 主題 | 現價 | {days} 日漲跌 |",
        "|------|------|------|------|-------------|",
    ]

    for sym, (name, theme) in TW_CORE.items():
        prices = tw_data.get(sym, [])
        ticker = sym.split(".")[0]
        if prices:
            chg = pct_change_total(prices)
            sign = "+" if chg >= 0 else ""
            lines.append(f"| {ticker} | {name} | {theme} | NT${prices[-1]:.1f} | {sign}{chg}% |")
        else:
            lines.append(f"| {ticker} | {name} | {theme} | — | — |")

    # 相關性矩陣：核心美股 vs 台灣標的
    lines += [
        "",
        "---",
        "",
        "## 相關性矩陣（美股 vs 台股，日漲跌幅）",
        "",
        f"> 計算期間：最近 {days} 個交易日",
        "",
    ]

    key_us = ["MU", "NVDA", "LITE", "COHR"]
    header = "| 台股 \\ 美股 |" + "".join(f" {sym} |" for sym in key_us)
    sep    = "|------------|" + "".join(" ------- |" for _ in key_us)
    lines += [header, sep]

    for tw_sym, (name, theme) in TW_CORE.items():
        tw_prices = tw_data.get(tw_sym, [])
        ticker = tw_sym.split(".")[0]
        cells = [f"| **{ticker}** ({name}) |"]
        for us_sym in key_us:
            us_prices = us_data.get(us_sym, [])
            c = compute_correlation(us_prices, tw_prices)
            if c != c:  # nan
                cells.append(" — |")
            else:
                label = corr_label(c)
                cells.append(f" {c:.2f} {label} |")
        lines.append("".join(cells))

    lines += [
        "",
        "---",
        "",
        "## 解讀框架",
        "",
        "| 相關性 | 含義 |",
        "|--------|------|",
        "| MU ↑ 強正相關台股 | DRAM 週期高度同步，MU 法說可作為台股先行指標 |",
        "| NVDA ↑ 強正相關台股 | AI CapEx 直接傳導，NVDA 股價為 AI 供應鏈 beta |",
        "| LITE/COHR ↑ 強正相關 CPO 標的 | CPO 需求端與供給端高度連動 |",
        "| 相關性突然下降 | 台股開始 de-coupling，注意個股特殊因素 |",
        "",
        f"*生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}*",
    ]

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="同業比較與相關性分析")
    parser.add_argument("--days",      type=int, default=60, help="相關性計算天數（預設 60）")
    parser.add_argument("--no-report", action="store_true",  help="不寫入報告")
    args = parser.parse_args()

    today_str = date.today().strftime("%Y%m%d")

    print(f"📊 抓取美股同業資料（最近 {args.days} 日）...")
    us_syms   = list(US_PEERS.keys())
    us_data   = fetch_prices(us_syms, args.days)

    print(f"📊 抓取台灣核心標的資料...")
    tw_syms   = list(TW_CORE.keys())
    tw_data   = fetch_prices(tw_syms, args.days)

    print("🔢 計算相關性矩陣...")
    report_md = generate_report(us_data, tw_data, args.days)

    if not args.no_report:
        REPORT_DIR.mkdir(exist_ok=True)
        out_path = REPORT_DIR / f"peer_compare_{today_str}.md"
        out_path.write_text(report_md, encoding="utf-8")
        print(f"\n✅ 報告已寫入：{out_path}")

        # 顯示摘要（僅美股近期表現）
        print("\n── 美股同業摘要 ──")
        for sym in US_PEERS:
            prices = us_data.get(sym, [])
            if prices:
                chg = pct_change_total(prices)
                sign = "+" if chg >= 0 else ""
                print(f"  {sym:<6}  ${prices[-1]:.2f}  {sign}{chg}%（{args.days}日）")
    else:
        print(report_md)


if __name__ == "__main__":
    main()
