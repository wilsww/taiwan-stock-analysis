"""
fetch_prices.py — 台股追蹤標的即時/歷史股價擷取工具
使用 yfinance，支援上市（.TW）與上櫃（.TWO）
"""
import yfinance as yf
import warnings
import argparse
from datetime import datetime

warnings.filterwarnings("ignore")

# ── 核心追蹤標的（依 CLAUDE.md 設定）──────────────────────────────────
WATCHLIST = {
    # 第一圈：主要持倉候選
    "2408.TW":  "南亞科技",
    "2344.TW":  "華邦電子",
    # 第二圈：光通訊供應鏈（原有）
    "3363.TWO": "上詮光纖",
    "2455.TW":  "全新光電",
    "4979.TWO": "華星光通",
    "3081.TWO": "聯亞光電",
    "3105.TWO": "穩懋半導體",
    # 第二圈：光通訊供應鏈（新增）
    "6442.TW":  "光聖",
    "4977.TW":  "眾達-KY",
    "3163.TWO": "波若威",
    "2345.TW":  "智邦",
    "6223.TWO": "旺矽",
    # 子公司參考
    "4919.TW":  "新唐科技",
    # 第三圈：IC 載板 PCB
    "3037.TW":  "欣興電子",
    "8046.TW":  "南亞電路板",
    "3189.TW":  "景碩科技",
}

def fetch_snapshot(tickers: dict = WATCHLIST) -> list[dict]:
    """抓取所有標的最新收盤價與基本估值"""
    rows = []
    for sym, name in tickers.items():
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="2d")
            if hist.empty:
                rows.append({"代碼": sym, "公司": name, "收盤價": "N/A",
                             "漲跌": "N/A", "漲跌幅": "N/A", "市值": "N/A", "狀態": "無資料"})
                continue
            close     = hist["Close"].iloc[-1]
            prev      = hist["Close"].iloc[-2] if len(hist) >= 2 else close
            chg       = close - prev
            chg_pct   = chg / prev * 100

            # 嘗試取 BPS / Market Cap（部分小型股可能無資料）
            info      = tk.fast_info
            mkt_cap   = getattr(info, "market_cap", None)
            mkt_cap_b = f"NT${mkt_cap/1e8:.0f}億" if mkt_cap else "N/A"

            rows.append({
                "代碼":   sym,
                "公司":   name,
                "收盤價":  f"NT${close:.1f}",
                "漲跌":    f"{'+' if chg>=0 else ''}{chg:.1f}",
                "漲跌幅":  f"{'+' if chg_pct>=0 else ''}{chg_pct:.2f}%",
                "市值":    mkt_cap_b,
                "狀態":   "✅",
            })
        except Exception as e:
            rows.append({"代碼": sym, "公司": name, "收盤價": "ERR",
                         "漲跌": "", "漲跌幅": "", "市值": "", "狀態": str(e)[:40]})
    return rows


def fetch_history(sym: str, period: str = "3mo") -> None:
    """印出單一標的歷史 K 線（週頻）"""
    tk   = yf.Ticker(sym)
    hist = tk.history(period=period, interval="1wk")
    if hist.empty:
        print(f"{sym}: 無歷史資料")
        return
    print(f"\n{'='*50}")
    print(f"{sym} 週K（近 {period}）")
    print(f"{'='*50}")
    print(hist[["Open","High","Low","Close","Volume"]].to_string())


def print_table(rows: list[dict]) -> None:
    print(f"\n{'='*65}")
    print(f"  台股追蹤標的快照  ｜  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*65}")
    hdr = f"{'代碼':<12} {'公司':<10} {'收盤價':>10} {'漲跌':>8} {'漲跌幅':>8} {'市值':>12}"
    print(hdr)
    print("-" * 65)
    for r in rows:
        print(f"{r['代碼']:<12} {r['公司']:<10} {r['收盤價']:>10} "
              f"{r['漲跌']:>8} {r['漲跌幅']:>8} {r['市值']:>12}")
    print("="*65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="台股追蹤標的股價工具")
    parser.add_argument("--history", metavar="SYM",
                        help="顯示單一標的歷史K線，例如 2344.TW")
    parser.add_argument("--period", default="3mo",
                        help="歷史期間，例如 1mo 3mo 6mo 1y（預設 3mo）")
    args = parser.parse_args()

    if args.history:
        fetch_history(args.history, args.period)
    else:
        rows = fetch_snapshot()
        print_table(rows)
