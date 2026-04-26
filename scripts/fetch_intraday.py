"""日內 5m K 線抓取 (yfinance) → intraday_price.

P5 設計：
- 只儲存原生 5m；10m / 30m / 40m / 1H / 4H 由 pandas 即時 resample
- 1W 由 daily_price resample
- TSE: <ticker>.TW    OTC: <ticker>.TWO
- 時區一律存 ISO8601 +08:00 (Asia/Taipei)，不轉 UTC（K 線易讀）
- 小樣本驗證後再做批次

CLI:
    python3 scripts/fetch_intraday.py --ticker 2330             # 預設 5d
    python3 scripts/fetch_intraday.py --ticker 6488 --period 30d
"""
from __future__ import annotations

import argparse
import sqlite3
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "revenue" / "revenue.db"

VALID_INTRADAY_TF = {"5m", "10m", "30m", "40m", "1H", "4H"}
PRIMITIVE_TF = "5m"


# ── DB ─────────────────────────────────────────────────────────────
def ensure_intraday_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS intraday_price (
            ticker     TEXT NOT NULL,
            ts         TEXT NOT NULL,   -- ISO8601 with tz, e.g. 2026-04-17T13:20:00+08:00
            tf         TEXT NOT NULL,   -- '5m' (僅原生)
            open       REAL,
            high       REAL,
            low        REAL,
            close      REAL,
            volume     REAL,
            updated_at TEXT,
            PRIMARY KEY (ticker, ts, tf)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_intra_ticker_ts ON intraday_price(ticker, ts)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_intra_ts ON intraday_price(ts)")
    conn.commit()


# ── Yahoo route ───────────────────────────────────────────────────
def yahoo_symbol(ticker: str) -> list[str]:
    """先試 .TW (TSE)，失敗再試 .TWO (OTC)；本函式只回候選清單，由 caller 決定。"""
    return [f"{ticker}.TW", f"{ticker}.TWO"]


# ── Fetch ──────────────────────────────────────────────────────────
def fetch_intraday(ticker: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    """回傳 DataFrame index=ts (Asia/Taipei tz), cols=[open, high, low, close, volume].

    抓不到回 empty df。
    """
    import yfinance as yf  # 延遲 import

    for sym in yahoo_symbol(ticker):
        try:
            df = yf.Ticker(sym).history(period=period, interval=interval, auto_adjust=False)
        except Exception:
            df = pd.DataFrame()
        if not df.empty:
            df = df.rename(
                columns={
                    "Open": "open",
                    "High": "high",
                    "Low": "low",
                    "Close": "close",
                    "Volume": "volume",
                }
            )[["open", "high", "low", "close", "volume"]]
            df["volume"] = df["volume"] / 1000.0
            df.index.name = "ts"
            return df
    return pd.DataFrame()


# ── Persist ──────────────────────────────────────────────────────
def upsert_intraday(conn: sqlite3.Connection, ticker: str, df: pd.DataFrame, tf: str = PRIMITIVE_TF) -> int:
    if df.empty:
        return 0
    updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for ts, row in df.iterrows():
        if pd.isna(row.get("close")):
            continue
        rows.append(
            (
                ticker,
                ts.isoformat(),  # tz-aware ISO8601
                tf,
                float(row["open"]) if pd.notna(row["open"]) else None,
                float(row["high"]) if pd.notna(row["high"]) else None,
                float(row["low"]) if pd.notna(row["low"]) else None,
                float(row["close"]),
                float(row["volume"]) if pd.notna(row["volume"]) else None,
                updated_at,
            )
        )
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR REPLACE INTO intraday_price "
        "(ticker, ts, tf, open, high, low, close, volume, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def load_intraday(
    conn: sqlite3.Connection,
    ticker: str,
    tf: str = PRIMITIVE_TF,
    since: Optional[str] = None,
) -> pd.DataFrame:
    sql = "SELECT ts, open, high, low, close, volume FROM intraday_price WHERE ticker = ? AND tf = ?"
    params: list = [ticker, tf]
    if since:
        sql += " AND ts >= ?"
        params.append(since)
    sql += " ORDER BY ts ASC"
    df = pd.read_sql_query(sql, conn, params=params)
    if df.empty:
        return df
    df["ts"] = pd.to_datetime(df["ts"], utc=False)
    return df.set_index("ts")


def fetch_and_store(ticker: str, period: str = "5d") -> dict:
    df = fetch_intraday(ticker, period=period, interval=PRIMITIVE_TF)
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_intraday_table(conn)
        added = upsert_intraday(conn, ticker, df, tf=PRIMITIVE_TF)
        total = conn.execute(
            "SELECT COUNT(*) FROM intraday_price WHERE ticker = ? AND tf = ?",
            (ticker, PRIMITIVE_TF),
        ).fetchone()[0]
    finally:
        conn.close()
    return {
        "ticker": ticker,
        "fetched": len(df),
        "upserted": added,
        "total_in_db": total,
        "first_ts": str(df.index.min()) if not df.empty else None,
        "last_ts": str(df.index.max()) if not df.empty else None,
    }


# ── CLI ───────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--period", default="5d", help="yfinance period: 1d / 5d / 1mo / 60d ...")
    ap.add_argument("--show", type=int, default=3)
    args = ap.parse_args()
    summary = fetch_and_store(args.ticker, period=args.period)
    print(summary)
    if args.show:
        conn = sqlite3.connect(DB_PATH)
        try:
            df = load_intraday(conn, args.ticker)
        finally:
            conn.close()
        if not df.empty:
            print(df.tail(args.show))


if __name__ == "__main__":
    main()
