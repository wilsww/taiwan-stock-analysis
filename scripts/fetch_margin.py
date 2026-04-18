#!/usr/bin/env python3
"""
fetch_margin.py — 台股融資融券餘額自動抓取

資料來源：TWSE 融資融券彙總（個股）
  URL: https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN?response=json&date={YYYYMMDD}&selectType=STOCK

用法：
  python3 scripts/fetch_margin.py                        # 抓今日所有追蹤標的
  python3 scripts/fetch_margin.py --ticker 2408 2344    # 指定標的
  python3 scripts/fetch_margin.py --date 20260410       # 指定日期
  python3 scripts/fetch_margin.py --days 5              # 最近 N 個交易日
"""

import argparse
import csv
import json
import sqlite3
import time
import urllib.request
from datetime import datetime, date, timedelta
from pathlib import Path

# ── 設定 ──────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH  = DATA_DIR / "revenue" / "revenue.db"

COMPANY_NAMES = {
    "2408": "南亞科技",
    "2344": "華邦電子",
    "3363": "上詮光纖",
    "2455": "全新光電",
    "4979": "華星光通",
    "3081": "聯亞光電",
    "3105": "穩懋半導體",
    "6442": "光聖",
    "4977": "眾達-KY",
    "3163": "波若威",
    "2345": "智邦",
    "6223": "旺矽",
    "3037": "欣興電子",
    "8046": "南亞電路板",
    "3189": "景碩科技",
}

# 融資餘額警示閾值（資券比，即融資餘額/融券餘額）
# 超過此值代表多頭籌碼過熱，需留意
MARGIN_RATIO_ALERT = 10.0


def init_db():
    """建立 margin_data 表（若不存在）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS margin_data (
            ticker          TEXT NOT NULL,
            trade_date      TEXT NOT NULL,    -- YYYY-MM-DD
            margin_balance  REAL,             -- 融資餘額（千股）
            margin_change   REAL,             -- 融資增減（千股）
            short_balance   REAL,             -- 融券餘額（千股）
            short_change    REAL,             -- 融券增減（千股）
            margin_ratio    REAL,             -- 資券比（融資/融券）
            updated_at      TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.commit()
    conn.close()


def fetch_margin_data(trade_date: str) -> dict:
    """
    抓取當日融資融券資料
    trade_date 格式：YYYYMMDD
    回傳：{ticker: {margin_balance, margin_change, short_balance, short_change, margin_ratio}}
    """
    url = (
        f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
        f"?response=json&date={trade_date}&selectType=STOCK"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
        "Referer": "https://www.twse.com.tw/",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
    except Exception as e:
        print(f"  ⚠️  MI_MARGN API 錯誤（{trade_date}）：{e}")
        return {}

    if data.get("stat") != "OK":
        print(f"  ⚠️  融資融券無資料（{trade_date}）：stat={data.get('stat')}")
        return {}

    # 嘗試從 tables 中找融資融券彙總表
    tables = data.get("tables", [data]) if "tables" in data else [data]
    result = {}

    for table in tables:
        rows = table.get("data", [])
        # 融資融券欄位（MI_MARGN STOCK 模式）：
        # 0=代號 1=名稱 2=融資買進 3=融資賣出 4=現金償還 5=融資餘額 6=融資限額
        # 7=融券賣出 8=融券買進 9=現券償還 10=融券餘額 11=融券限額 12=資券相抵
        for row in rows:
            if not row or len(row) < 11:
                continue
            ticker = str(row[0]).strip()
            if ticker not in COMPANY_NAMES:
                continue

            def p(s):
                try:
                    return float(str(s).replace(",", "").replace("--", "0") or 0)
                except ValueError:
                    return 0.0

            margin_bal = p(row[5])
            short_bal  = p(row[10])
            # 前期融資餘額 = 融資餘額 - (買進-賣出-現金償還)
            margin_chg = p(row[2]) - p(row[3]) - p(row[4])
            short_chg  = p(row[7]) - p(row[8]) - p(row[9])
            ratio = round(margin_bal / short_bal, 2) if short_bal > 0 else 0.0

            result[ticker] = {
                "margin_balance": margin_bal,
                "margin_change":  margin_chg,
                "short_balance":  short_bal,
                "short_change":   short_chg,
                "margin_ratio":   ratio,
            }

    return result


def save_to_db(rows: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    for r in rows:
        c.execute("""
            INSERT OR REPLACE INTO margin_data
            (ticker, trade_date, margin_balance, margin_change,
             short_balance, short_change, margin_ratio, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["ticker"], r["trade_date"],
            r["margin_balance"], r["margin_change"],
            r["short_balance"],  r["short_change"],
            r["margin_ratio"],   now
        ))
    conn.commit()
    conn.close()


def save_to_csv(rows: list[dict], trade_date: str):
    ym = f"{trade_date[:4]}-{trade_date[4:6]}"
    out_dir = DATA_DIR / "margin" / ym
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"margin_{trade_date}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ticker", "company", "trade_date",
            "margin_balance", "margin_change",
            "short_balance", "short_change", "margin_ratio", "alert"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "ticker":         r["ticker"],
                "company":        COMPANY_NAMES.get(r["ticker"], ""),
                "trade_date":     r["trade_date"],
                "margin_balance": r["margin_balance"],
                "margin_change":  r["margin_change"],
                "short_balance":  r["short_balance"],
                "short_change":   r["short_change"],
                "margin_ratio":   r["margin_ratio"],
                "alert":          "⚠️ 資券比過高" if r["margin_ratio"] > MARGIN_RATIO_ALERT else "",
            })
    print(f"  📄 CSV 輸出：{path}")


def get_trading_dates(n_days: int) -> list[str]:
    result = []
    d = date.today()
    while len(result) < n_days:
        if d.weekday() < 5:
            result.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return result


def print_summary(rows: list[dict]):
    if not rows:
        print("  （無資料）")
        return
    print(f"\n  {'代碼':<6} {'公司':<12} {'融資餘額':>10} {'融資增減':>8} {'融券餘額':>10} {'資券比':>6} {'警示':>6}")
    print("  " + "-" * 62)
    for r in sorted(rows, key=lambda x: x["margin_ratio"], reverse=True):
        company = COMPANY_NAMES.get(r["ticker"], r["ticker"])
        sign = lambda v: f"+{v:,.0f}" if v >= 0 else f"{v:,.0f}"
        alert = "⚠️" if r["margin_ratio"] > MARGIN_RATIO_ALERT else "  "
        print(
            f"  {r['ticker']:<6} {company:<12} "
            f"{r['margin_balance']:>10,.0f} {sign(r['margin_change']):>8} "
            f"{r['short_balance']:>10,.0f} {r['margin_ratio']:>6.1f} {alert}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(description="台股融資融券餘額抓取")
    parser.add_argument("--ticker", nargs="+", help="指定股票代碼")
    parser.add_argument("--date",   help="指定日期 YYYYMMDD（預設今日）")
    parser.add_argument("--days",   type=int, default=1, help="抓最近 N 個交易日")
    parser.add_argument("--no-db",  action="store_true")
    parser.add_argument("--no-csv", action="store_true")
    args = parser.parse_args()

    init_db()

    target_tickers = set(args.ticker) if args.ticker else set(COMPANY_NAMES.keys())
    dates = [args.date] if args.date else get_trading_dates(args.days)

    for trade_date in dates:
        print(f"\n📅 抓取 {trade_date[:4]}/{trade_date[4:6]}/{trade_date[6:]} 融資融券資料...")
        raw = fetch_margin_data(trade_date)

        if not raw:
            continue

        rows = []
        for ticker in target_tickers:
            if ticker in raw:
                rows.append({
                    "ticker":     ticker,
                    "trade_date": f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}",
                    **raw[ticker],
                })

        print_summary(rows)

        if not args.no_db:
            save_to_db(rows)
            print(f"  ✅ 已寫入 SQLite（{len(rows)} 筆）")

        if not args.no_csv:
            save_to_csv(rows, trade_date)

        time.sleep(0.5)

    print("\n🎉 完成")


if __name__ == "__main__":
    main()
