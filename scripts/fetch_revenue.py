#!/usr/bin/env python3
"""
台灣月營收自動抓取腳本
用途：抓取指定標的最新月營收並存入本地資料庫
使用：python3 scripts/fetch_revenue.py --ticker 2408 2344 3363 2455
"""

import argparse
import json
import sqlite3
import urllib.request
import urllib.parse
import re
import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict

# ── 設定 ──────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
REVENUE_DIR = DATA_DIR / "revenue"
DB_PATH = REVENUE_DIR / "revenue.db"

# 公司中文名稱對照
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


def init_db():
    """初始化 SQLite 資料庫"""
    REVENUE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS monthly_revenue (
            ticker      TEXT NOT NULL,
            year        INTEGER NOT NULL,
            month       INTEGER NOT NULL,
            revenue_m   REAL,        -- 當月營收（百萬台幣）
            mom_pct     REAL,        -- 月增率 %
            yoy_pct     REAL,        -- 年增率 %
            cum_revenue REAL,        -- 累計營收（百萬台幣）
            cum_yoy_pct REAL,        -- 累計年增率 %
            source      TEXT,        -- 資料來源
            updated_at  TEXT,        -- 更新時間
            PRIMARY KEY (ticker, year, month)
        )
    """)
    conn.commit()
    conn.close()
    print(f"✅ 資料庫初始化完成：{DB_PATH}")


def search_revenue_web(ticker: str) -> Optional[Dict]:
    """
    透過 web search 抓取月營收
    回傳格式：{"year": 2026, "month": 2, "revenue_m": 15607, "mom_pct": 1.94, "yoy_pct": 586.71}
    """
    company = COMPANY_NAMES.get(ticker, ticker)
    today = date.today()

    # 嘗試不同查詢策略
    queries = [
        f"{company} {ticker} {today.year}年{today.month}月 月營收",
        f"{ticker} {company} monthly revenue {today.year}",
        f"site:winvest.tw {ticker}",
    ]

    print(f"  🔍 搜尋 {company}（{ticker}）月營收...")

    # 在 Claude Code 環境中使用 web_search
    # 此腳本設計為在 Claude Code 的 bash 工具內執行
    # 實際抓取邏輯由 Claude Code 的 web_search 工具輔助

    # ── 嘗試直接抓取 winvest.tw ──
    url = f"https://winvest.tw/Stock/Symbol/Comment/{ticker}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # 解析月營收 — 先去除 HTML 標籤，再 regex（winvest.tw 部分股票用 <span> 包住增/減）
        # 格式範例：最新 2026 年 2 月營收 116.00 億，月減 9.14%，年增 16.18%
        clean = re.sub(r"<[^>]+>", "", html)
        pattern = r"最新\s*(\d{4})\s*年\s*(\d{1,2})\s*月營收\s*([\d,\.]+)\s*億.*?月(增|減)\s*([\d\.]+)%.*?年(增|減)\s*([\d\.]+)%"
        m = re.search(pattern, clean, re.DOTALL)
        if m:
            year = int(m.group(1))
            month = int(m.group(2))
            rev_b = float(m.group(3).replace(",", ""))  # 億元
            mom = float(m.group(5)) * (1 if m.group(4) == "增" else -1)
            yoy = float(m.group(7)) * (1 if m.group(6) == "增" else -1)
            result = {
                "ticker": ticker,
                "company": company,
                "year": year,
                "month": month,
                "revenue_m": round(rev_b * 1000, 1),  # 億→百萬
                "mom_pct": mom,
                "yoy_pct": yoy,
                "source": "winvest.tw",
            }
            print(f"  ✅ {company}（{ticker}）{year}年{month}月 = NT${rev_b:.2f}億 "
                  f"(MoM {mom:+.1f}%, YoY {yoy:+.1f}%)")
            return result

    except Exception as e:
        print(f"  ⚠️  winvest.tw 抓取失敗：{e}")

    # ── 備用：histock.tw ──
    url2 = f"https://histock.tw/stock/{ticker}/%E8%B2%A1%E5%8B%99%E5%A0%B1%E8%A1%A8"
    try:
        req2 = urllib.request.Request(url2, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            html2 = resp2.read().decode("utf-8", errors="ignore")
        # histock 格式解析（簡易）
        pattern2 = r"(\d{4})/(\d{2})\s+([\d,]+)\s+([-\d\.]+)\s+([-\d\.]+)"
        matches = re.findall(pattern2, html2)
        if matches:
            latest = matches[0]
            year, month = int(latest[0]), int(latest[1])
            rev_k = float(latest[2].replace(",", ""))  # 千元
            mom = float(latest[3])
            yoy = float(latest[4])
            result = {
                "ticker": ticker,
                "company": company,
                "year": year,
                "month": month,
                "revenue_m": round(rev_k / 1000, 1),  # 千→百萬
                "mom_pct": mom,
                "yoy_pct": yoy,
                "source": "histock.tw",
            }
            print(f"  ✅ {company}（{ticker}）{year}年{month}月 = NT${rev_k/1000:.0f}百萬 "
                  f"(MoM {mom:+.1f}%, YoY {yoy:+.1f}%)")
            return result
    except Exception as e2:
        print(f"  ⚠️  histock.tw 抓取失敗：{e2}")

    print(f"  ❌ {company}（{ticker}）自動抓取失敗，請手動輸入")
    return None


def save_to_db(data: dict):
    """存入 SQLite"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO monthly_revenue
        (ticker, year, month, revenue_m, mom_pct, yoy_pct, source, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["ticker"],
        data["year"],
        data["month"],
        data.get("revenue_m"),
        data.get("mom_pct"),
        data.get("yoy_pct"),
        data.get("source", "manual"),
        datetime.now().isoformat(),
    ))
    conn.commit()
    conn.close()


def print_summary(tickers: list):
    """印出資料庫現有最新數據摘要"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    print("\n" + "═" * 70)
    print("  台股月營收資料庫摘要")
    print("═" * 70)
    print(f"  {'代碼':<6} {'公司':<10} {'最新月份':<10} {'營收(億)':<12} {'MoM%':<8} {'YoY%':<8}")
    print("─" * 70)
    for ticker in tickers:
        c.execute("""
            SELECT year, month, revenue_m, mom_pct, yoy_pct
            FROM monthly_revenue
            WHERE ticker = ?
            ORDER BY year DESC, month DESC
            LIMIT 1
        """, (ticker,))
        row = c.fetchone()
        company = COMPANY_NAMES.get(ticker, ticker)
        if row:
            yr, mo, rev, mom, yoy = row
            rev_b = rev / 1000 if rev else 0
            mom_s = f"{mom:+.1f}%" if mom is not None else "N/A"
            yoy_s = f"{yoy:+.1f}%" if yoy is not None else "N/A"
            print(f"  {ticker:<6} {company:<10} {yr}年{mo:02d}月   {rev_b:>8.2f}億  {mom_s:<8} {yoy_s:<8}")
        else:
            print(f"  {ticker:<6} {company:<10} {'無資料':<10}")
    print("═" * 70)
    conn.close()


def manual_input(ticker: str) -> Optional[Dict]:
    """手動輸入月營收數據"""
    company = COMPANY_NAMES.get(ticker, ticker)
    print(f"\n📝 手動輸入 {company}（{ticker}）月營收")
    try:
        year = int(input("  年份（如 2026）: "))
        month = int(input("  月份（如 2）: "))
        rev_str = input("  當月營收（億台幣，如 156.07）: ")
        rev_b = float(rev_str)
        mom = float(input("  月增率 %（如 1.94）: "))
        yoy = float(input("  年增率 %（如 586.71）: "))
        return {
            "ticker": ticker,
            "company": company,
            "year": year,
            "month": month,
            "revenue_m": round(rev_b * 1000, 1),
            "mom_pct": mom,
            "yoy_pct": yoy,
            "source": "manual",
        }
    except (ValueError, KeyboardInterrupt):
        print("  取消輸入")
        return None


# ── 主程式 ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="台灣月營收抓取工具")
    parser.add_argument("--ticker", nargs="+", default=list(COMPANY_NAMES.keys()),
                        help="股票代碼列表（預設全部）")
    parser.add_argument("--manual", action="store_true", help="強制手動輸入模式")
    parser.add_argument("--summary", action="store_true", help="只顯示資料庫摘要")
    args = parser.parse_args()

    init_db()

    if args.summary:
        print_summary(args.ticker)
        return

    print(f"\n🚀 開始抓取 {len(args.ticker)} 支標的月營收...")
    print(f"   標的：{', '.join(args.ticker)}\n")

    results = []
    failed = []

    for ticker in args.ticker:
        if args.manual:
            data = manual_input(ticker)
        else:
            data = search_revenue_web(ticker)
            if data is None:
                data = manual_input(ticker)

        if data:
            save_to_db(data)
            results.append(data)
        else:
            failed.append(ticker)

    print_summary(args.ticker)

    if failed:
        print(f"\n⚠️  以下標的抓取失敗，請稍後重試：{', '.join(failed)}")

    # 輸出 JSON 供後續分析使用
    REVENUE_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REVENUE_DIR / f"revenue_{datetime.now().strftime('%Y%m')}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n💾 資料已存至：{output_path}")


if __name__ == "__main__":
    main()
