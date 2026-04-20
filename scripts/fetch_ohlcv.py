#!/usr/bin/env python3
"""
fetch_ohlcv.py — 回填 daily_price 的日 OHLCV

預設以目前追蹤清單（AI 供應鏈精選）為範圍，依月份抓取：
- TWSE: STOCK_DAY
- TPEx: afterTrading/tradingStock
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import date

from sector_flow import init_db, load_universe, save_prices_to_db


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json",
    "Referer": "https://www.twse.com.tw/",
}
TPEX_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "application/json",
    "Referer": "https://www.tpex.org.tw/",
}


def _parse_num(value) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("--", "").replace("---", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _roc_date_to_iso(value: str) -> str:
    parts = str(value).split("/")
    if len(parts) != 3:
        raise ValueError(f"無法解析日期：{value}")
    year = int(parts[0]) + 1911
    month = int(parts[1])
    day = int(parts[2])
    return f"{year:04d}-{month:02d}-{day:02d}"


def _month_sequence(months: int) -> list[tuple[int, int]]:
    today = date.today()
    year = today.year
    month = today.month
    result: list[tuple[int, int]] = []
    for _ in range(months):
        result.append((year, month))
        month -= 1
        if month == 0:
            year -= 1
            month = 12
    result.reverse()
    return result


def _fetch_json(url: str, data: dict | None = None, headers: dict | None = None) -> dict:
    encoded = None
    if data is not None:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, headers=headers or HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="ignore"))


def _fetch_twse_month(ticker: str, year: int, month: int) -> list[dict] | None:
    url = (
        "https://www.twse.com.tw/exchangeReport/STOCK_DAY"
        f"?response=json&date={year}{month:02d}01&stockNo={ticker}"
    )
    try:
        payload = _fetch_json(url, headers=HEADERS)
    except Exception:
        return None
    if payload.get("stat") != "OK" or not payload.get("data"):
        return None

    rows: list[dict] = []
    for row in payload["data"]:
        if len(row) < 7:
            continue
        trade_date = _roc_date_to_iso(row[0])
        volume_lots = _parse_num(row[1]) / 1000.0
        rows.append(
            {
                "ticker": ticker,
                "trade_date": trade_date,
                "open": _parse_num(row[3]),
                "high": _parse_num(row[4]),
                "low": _parse_num(row[5]),
                "close": _parse_num(row[6]),
                "volume": volume_lots,
            }
        )
    return rows


def _fetch_tpex_month(ticker: str, year: int, month: int) -> list[dict] | None:
    url = "https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock"
    payload_data = {
        "code": ticker,
        "date": f"{year:04d}/{month:02d}/01",
        "response": "json",
    }
    try:
        payload = _fetch_json(url, data=payload_data, headers=TPEX_HEADERS)
    except Exception:
        return None
    if payload.get("stat") != "ok" or not payload.get("tables"):
        return None

    table = payload["tables"][0]
    rows: list[dict] = []
    for row in table.get("data", []):
        if len(row) < 7:
            continue
        trade_date = _roc_date_to_iso(row[0])
        rows.append(
            {
                "ticker": ticker,
                "trade_date": trade_date,
                "open": _parse_num(row[3]),
                "high": _parse_num(row[4]),
                "low": _parse_num(row[5]),
                "close": _parse_num(row[6]),
                "volume": _parse_num(row[1]),
            }
        )
    return rows


def _fetch_month_rows(
    ticker: str,
    year: int,
    month: int,
    market_hint: str | None,
) -> tuple[list[dict], str | None]:
    fetchers = [("twse", _fetch_twse_month), ("tpex", _fetch_tpex_month)]
    if market_hint == "tpex":
        fetchers.reverse()

    for market, fetcher in fetchers:
        rows = fetcher(ticker, year, month)
        if rows is not None:
            return rows, market
    return [], market_hint


def _resolve_tickers(args: argparse.Namespace) -> list[str]:
    if args.tickers:
        return args.tickers
    _cats, all_tickers, _t2c, _label = load_universe(args.tier)
    return list(all_tickers.keys())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="回填 daily_price 的日 OHLCV。")
    parser.add_argument(
        "--ticker",
        dest="tickers",
        nargs="*",
        help="指定股票代號；未指定時改用 tier 追蹤清單。",
    )
    parser.add_argument(
        "--tier",
        default="ai_supply_chain",
        choices=["ai_supply_chain", "broad_themes", "all"],
        help="未指定 --ticker 時，使用哪個 universe tier。",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=18,
        help="往回抓取幾個月份，預設 18 個月。",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=2.0,
        help="每次請求後暫停秒數，預設 2 秒。",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    init_db()
    tickers = _resolve_tickers(args)
    months = _month_sequence(args.months)
    print(f"追蹤標的：{len(tickers)} 檔")
    print(f"抓取月份：{months[0][0]}-{months[0][1]:02d} ～ {months[-1][0]}-{months[-1][1]:02d}")

    total_rows = 0
    for idx, ticker in enumerate(tickers, 1):
        market_hint: str | None = None
        ticker_rows: list[dict] = []
        print(f"[{idx}/{len(tickers)}] {ticker}")
        for year, month in months:
            rows, market_hint = _fetch_month_rows(ticker, year, month, market_hint)
            if rows:
                ticker_rows.extend(rows)
                print(
                    f"  {year}-{month:02d} {market_hint or 'unknown'}: {len(rows)} 筆",
                    flush=True,
                )
            else:
                print(
                    f"  {year}-{month:02d} {market_hint or 'unknown'}: 無資料",
                    flush=True,
                )
            time.sleep(args.sleep)

        if ticker_rows:
            save_prices_to_db(ticker_rows)
            total_rows += len(ticker_rows)
            print(f"  寫入 {len(ticker_rows)} 筆")
        else:
            print("  未寫入任何資料")

    print(f"完成，共寫入 {total_rows} 筆 OHLCV")


if __name__ == "__main__":
    main()
