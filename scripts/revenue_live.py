#!/usr/bin/env python3
"""
revenue_live.py — 即時月營收爬取模組（方案B）
從 winvest.tw 直接抓取，不依賴本地 revenue.db
可獨立執行，也可被 run_report_b.py import
"""

import urllib.request
import re
import sqlite3
from datetime import datetime, date
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
REVENUE_DIR = DATA_DIR / "revenue"
DB_PATH  = REVENUE_DIR / "revenue.db"

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

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def _fetch_html(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_winvest(ticker: str):
    """從 winvest.tw 抓取最新月營收"""
    url = f"https://winvest.tw/Stock/Symbol/Comment/{ticker}"
    try:
        html = _fetch_html(url)
        # 格式範例：最新 2026 年 2 月營收 156.07 億，月增 1.94%，年增 586.71%
        # 先去除 HTML 標籤（winvest.tw 部分股票用 <span> 包住增/減方向詞）
        clean = re.sub(r"<[^>]+>", "", html)
        pat = (
            r"最新\s*(\d{4})\s*年\s*(\d{1,2})\s*月營收\s*([\d,\.]+)\s*億"
            r".*?月(增|減)\s*([\d\.]+)%.*?年(增|減)\s*([\d\.]+)%"
        )
        m = re.search(pat, clean, re.DOTALL)
        if m:
            year  = int(m.group(1))
            month = int(m.group(2))
            rev_b = float(m.group(3).replace(",", ""))
            mom   = float(m.group(5)) * (1 if m.group(4) == "增" else -1)
            yoy   = float(m.group(7)) * (1 if m.group(6) == "增" else -1)
            return {
                "ticker":    ticker,
                "company":   COMPANY_NAMES.get(ticker, ticker),
                "year":      year,
                "month":     month,
                "revenue_b": rev_b,           # 億元（顯示用）
                "revenue_m": round(rev_b * 1000, 1),  # 百萬元（DB 用）
                "mom_pct":   mom,
                "yoy_pct":   yoy,
                "source":    "winvest.tw",
                "fresh":     True,
            }
    except Exception as e:
        pass
    return None


def fetch_histock(ticker: str):
    """備用：histock.tw"""
    url = f"https://histock.tw/stock/{ticker}/%E8%B2%A1%E5%8B%99%E5%A0%B1%E8%A1%A8"
    try:
        html = _fetch_html(url)
        pat  = r"(\d{4})/(\d{2})\s+([\d,]+)\s+([-\d\.]+)\s+([-\d\.]+)"
        matches = re.findall(pat, html)
        if matches:
            row  = matches[0]
            year, month = int(row[0]), int(row[1])
            rev_k = float(row[2].replace(",", ""))  # 千元
            mom   = float(row[3])
            yoy   = float(row[4])
            rev_b = rev_k / 1e5  # 千元 → 億元
            return {
                "ticker":    ticker,
                "company":   COMPANY_NAMES.get(ticker, ticker),
                "year":      year,
                "month":     month,
                "revenue_b": round(rev_b, 2),
                "revenue_m": round(rev_k / 1000, 1),
                "mom_pct":   mom,
                "yoy_pct":   yoy,
                "source":    "histock.tw",
                "fresh":     True,
            }
    except Exception:
        pass
    return None


def fetch_revenue_live(ticker: str):
    """嘗試 winvest → histock，失敗則從本地 DB 讀取"""
    result = fetch_winvest(ticker)
    if result:
        return result
    result = fetch_histock(ticker)
    if result:
        return result
    # 降級：本地 DB
    return _load_from_db(ticker)


def _load_from_db(ticker: str):
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            SELECT year, month, revenue_m, mom_pct, yoy_pct, source
            FROM monthly_revenue WHERE ticker = ?
            ORDER BY year DESC, month DESC LIMIT 1
        """, (ticker,))
        row = c.fetchone()
        conn.close()
        if row:
            rev_m = row[2] or 0
            return {
                "ticker":    ticker,
                "company":   COMPANY_NAMES.get(ticker, ticker),
                "year":      row[0],
                "month":     row[1],
                "revenue_b": round(rev_m / 1000, 2),
                "revenue_m": rev_m,
                "mom_pct":   row[3],
                "yoy_pct":   row[4],
                "source":    f"{row[5]}（本地DB）",
                "fresh":     False,
            }
    except Exception:
        pass
    return None


def save_to_db(data: dict):
    """存回 revenue.db（可選）"""
    REVENUE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS monthly_revenue (
            ticker TEXT, year INTEGER, month INTEGER,
            revenue_m REAL, mom_pct REAL, yoy_pct REAL,
            source TEXT, updated_at TEXT,
            PRIMARY KEY (ticker, year, month)
        )
    """)
    c.execute("""
        INSERT OR REPLACE INTO monthly_revenue
        (ticker, year, month, revenue_m, mom_pct, yoy_pct, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["ticker"], data["year"], data["month"],
        data.get("revenue_m"), data.get("mom_pct"), data.get("yoy_pct"),
        data.get("source"), datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("\n即時月營收爬取測試")
    print("=" * 60)
    for ticker in COMPANY_NAMES:
        r = fetch_revenue_live(ticker)
        if r:
            yoy_s = f"{r['yoy_pct']:+.1f}%" if r["yoy_pct"] is not None else "N/A"
            mom_s = f"{r['mom_pct']:+.1f}%" if r["mom_pct"] is not None else "N/A"
            fresh = "🟢" if r.get("fresh") else "🔵"
            print(f"{fresh} {ticker} {r['company']:<10} "
                  f"{r['year']}年{r['month']:02d}月 "
                  f"NT${r['revenue_b']:.2f}億  "
                  f"MoM {mom_s}  YoY {yoy_s}  [{r['source']}]")
        else:
            print(f"❌ {ticker} 無資料")
    print("=" * 60)
