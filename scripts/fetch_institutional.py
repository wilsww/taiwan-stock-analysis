#!/usr/bin/env python3
"""
fetch_institutional.py — 台股三大法人買賣超自動抓取

資料來源：TWSE 公開 JSON API
  - 當日彙整：https://www.twse.com.tw/fund/T86?response=json&date={YYYYMMDD}&selectType=ALLBUT0999
  - 近 60 日彙整（個股）：https://www.twse.com.tw/fund/TDCC?response=json

用法：
  python3 scripts/fetch_institutional.py                        # 抓今日所有追蹤標的
  python3 scripts/fetch_institutional.py --ticker 2408 2344    # 抓指定標的
  python3 scripts/fetch_institutional.py --date 20260410       # 指定日期
  python3 scripts/fetch_institutional.py --days 5              # 最近 N 個交易日
"""

import argparse
import csv
import json
import sqlite3
import time
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

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


def init_db():
    """建立 institutional_flow 表（若不存在）"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS institutional_flow (
            ticker        TEXT NOT NULL,
            trade_date    TEXT NOT NULL,   -- YYYY-MM-DD
            foreign_net   REAL,            -- 外資買賣超（千股）
            invest_net    REAL,            -- 投信買賣超（千股）
            dealer_net    REAL,            -- 自營商買賣超（千股）
            total_net     REAL,            -- 三大法人合計（千股）
            updated_at    TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.commit()
    conn.close()


def fetch_t86(trade_date: str) -> dict:
    """
    抓取當日三大法人彙整資料（T86）
    trade_date 格式：YYYYMMDD
    回傳：{ticker: {"foreign": X, "invest": X, "dealer": X, "total": X}, ...}
    """
    url = (
        f"https://www.twse.com.tw/fund/T86"
        f"?response=json&date={trade_date}&selectType=ALLBUT0999"
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
        print(f"  ⚠️  T86 API 錯誤（{trade_date}）：{e}")
        return {}

    if data.get("stat") != "OK" or not data.get("data"):
        print(f"  ⚠️  T86 無資料（{trade_date}）：stat={data.get('stat')}")
        return {}

    result = {}
    # T86 欄位說明（fields）：
    # 0=證券代號 1=證券名稱 2=外資買進 3=外資賣出 4=外資買賣超
    # 5=投信買進 6=投信賣出 7=投信買賣超
    # 8=自營商買進 9=自營商賣出 10=自營商買賣超 11=三大法人買賣超
    for row in data["data"]:
        ticker = row[0].strip()
        if ticker not in COMPANY_NAMES:
            continue
        def parse_num(s) -> float:
            if isinstance(s, (int, float)):
                return float(s)
            return float(str(s).replace(",", "").replace("--", "0") or 0)

        result[ticker] = {
            "foreign": parse_num(row[4]),   # 外資買賣超（千股）
            "invest":  parse_num(row[7]),   # 投信買賣超
            "dealer":  parse_num(row[10]),  # 自營商買賣超
            "total":   parse_num(row[11]),  # 三大合計
        }

    return result


def save_to_db(rows: list[dict]):
    """將資料寫入 SQLite"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.now().isoformat()
    for r in rows:
        c.execute("""
            INSERT OR REPLACE INTO institutional_flow
            (ticker, trade_date, foreign_net, invest_net, dealer_net, total_net, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            r["ticker"], r["trade_date"],
            r["foreign"], r["invest"], r["dealer"], r["total"], now
        ))
    conn.commit()
    conn.close()


def save_to_csv(rows: list[dict], trade_date: str):
    """輸出 CSV 快照"""
    ym = f"{trade_date[:4]}-{trade_date[4:6]}"
    out_dir = DATA_DIR / "institutional" / ym
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"institutional_{trade_date}.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "ticker", "company", "trade_date",
            "foreign_net", "invest_net", "dealer_net", "total_net"
        ])
        writer.writeheader()
        for r in rows:
            writer.writerow({
                "ticker":      r["ticker"],
                "company":     COMPANY_NAMES.get(r["ticker"], r["ticker"]),
                "trade_date":  r["trade_date"],
                "foreign_net": r["foreign"],
                "invest_net":  r["invest"],
                "dealer_net":  r["dealer"],
                "total_net":   r["total"],
            })
    print(f"  📄 CSV 輸出：{path}")
    return path


def get_trading_dates(n_days: int) -> list[str]:
    """產生最近 n_days 個交易日（跳過週末，不排除假日）"""
    result = []
    d = date.today()
    while len(result) < n_days:
        if d.weekday() < 5:  # 0=Mon ... 4=Fri
            result.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return result


def print_summary(rows: list[dict]):
    """終端機顯示彙整表格"""
    if not rows:
        print("  （無資料）")
        return
    print(f"\n  {'代碼':<6} {'公司':<12} {'外資':>10} {'投信':>8} {'自營':>8} {'合計':>10}")
    print("  " + "-" * 58)
    for r in sorted(rows, key=lambda x: abs(x["total"]), reverse=True):
        company = COMPANY_NAMES.get(r["ticker"], r["ticker"])
        sign = lambda v: f"+{v:,.0f}" if v >= 0 else f"{v:,.0f}"
        print(
            f"  {r['ticker']:<6} {company:<12} "
            f"{sign(r['foreign']):>10} {sign(r['invest']):>8} "
            f"{sign(r['dealer']):>8} {sign(r['total']):>10}"
        )
    print()


def main():
    parser = argparse.ArgumentParser(description="台股三大法人買賣超抓取")
    parser.add_argument("--ticker", nargs="+", help="指定股票代碼（空白分隔）")
    parser.add_argument("--date",   help="指定日期 YYYYMMDD（預設今日）")
    parser.add_argument("--days",   type=int, default=1, help="抓最近 N 個交易日（預設 1）")
    parser.add_argument("--no-db",  action="store_true", help="不寫入 SQLite")
    parser.add_argument("--no-csv", action="store_true", help="不輸出 CSV")
    args = parser.parse_args()

    init_db()

    # 目標標的
    target_tickers = set(args.ticker) if args.ticker else set(COMPANY_NAMES.keys())

    # 決定日期清單
    if args.date:
        dates = [args.date]
    else:
        dates = get_trading_dates(args.days)

    all_rows = []
    for trade_date in dates:
        print(f"\n📅 抓取 {trade_date[:4]}/{trade_date[4:6]}/{trade_date[6:]} 三大法人資料...")
        raw = fetch_t86(trade_date)

        if not raw:
            continue

        rows = []
        for ticker in target_tickers:
            if ticker in raw:
                rows.append({
                    "ticker":    ticker,
                    "trade_date": f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:]}",
                    **raw[ticker],
                })
            else:
                print(f"  ⚠️  {ticker}（{COMPANY_NAMES.get(ticker, '')}）無資料")

        print_summary(rows)

        if not args.no_db:
            save_to_db(rows)
            print(f"  ✅ 已寫入 SQLite（{len(rows)} 筆）")

        if not args.no_csv:
            save_to_csv(rows, trade_date)

        all_rows.extend(rows)
        time.sleep(0.5)  # 避免 API 過快

    print(f"\n🎉 完成，共 {len(all_rows)} 筆紀錄")


if __name__ == "__main__":
    main()
