"""個股新聞抓取（Google News RSS）→ news_cache 去重快取.

P4 設計原則：
- 純函式 + sqlite 快取，僅存標題 / URL / 來源 / 發布時間，不存全文
- dedupe key = (ticker, url)
- 小樣本驗證後再考慮 cron 批次
- 不引入 feedparser，使用 stdlib `xml.etree.ElementTree`

CLI:
    python3 scripts/fetch_news.py --ticker 2330 --name 台積電
    python3 scripts/fetch_news.py --ticker 2330 --name 台積電 --prune-days 90
"""
from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import quote
from xml.etree import ElementTree as ET

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "data" / "revenue" / "revenue.db"

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
HEADERS = {"User-Agent": "Mozilla/5.0"}


# ── DB schema ──────────────────────────────────────────────────────
def ensure_news_cache(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS news_cache (
            ticker        TEXT NOT NULL,
            url           TEXT NOT NULL,
            title         TEXT,
            source        TEXT,
            published_at  TEXT,
            summary       TEXT,
            fetched_at    TEXT,
            PRIMARY KEY (ticker, url)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_news_ticker_time "
        "ON news_cache(ticker, published_at DESC)"
    )
    conn.commit()


# ── Fetch ──────────────────────────────────────────────────────────
def _build_query(ticker: str, name: Optional[str]) -> str:
    if name:
        return f"{ticker} {name}"
    return ticker


def _parse_pubdate(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def fetch_google_news(ticker: str, name: Optional[str] = None, timeout: float = 10.0) -> list[dict]:
    """抓 Google News RSS, 回傳結構化清單; 不寫入 DB."""
    query = _build_query(ticker, name)
    params = {
        "q": query,
        "hl": "zh-TW",
        "gl": "TW",
        "ceid": "TW:zh-Hant",
    }
    url = f"{GOOGLE_NEWS_RSS}?q={quote(query)}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    root = ET.fromstring(r.content)

    out: list[dict] = []
    for item in root.findall(".//item"):
        link = item.findtext("link")
        if not link:
            continue
        title_raw = item.findtext("title") or ""
        src_node = item.find("source")
        source = src_node.text if src_node is not None else None
        # title 末尾「 - {來源}」去掉避免重複
        title = title_raw
        if source and title.endswith(f" - {source}"):
            title = title[: -(len(source) + 3)].rstrip()
        out.append(
            {
                "url": link,
                "title": title,
                "source": source,
                "published_at": _parse_pubdate(item.findtext("pubDate")),
            }
        )
    return out


# ── Persistence ───────────────────────────────────────────────────
def upsert_news(conn: sqlite3.Connection, ticker: str, items: Iterable[dict]) -> int:
    """INSERT OR IGNORE; 已存在的 (ticker, url) 不覆蓋. 回傳新增筆數."""
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [
        (
            ticker,
            it["url"],
            it.get("title"),
            it.get("source"),
            it.get("published_at"),
            None,
            fetched_at,
        )
        for it in items
        if it.get("url")
    ]
    before = conn.total_changes
    conn.executemany(
        "INSERT OR IGNORE INTO news_cache "
        "(ticker, url, title, source, published_at, summary, fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    return conn.total_changes - before


def load_news(
    conn: sqlite3.Connection,
    ticker: str,
    limit: int = 20,
    since: Optional[str] = None,
) -> list[dict]:
    sql = (
        "SELECT url, title, source, published_at, fetched_at "
        "FROM news_cache WHERE ticker = ? "
    )
    params: list = [ticker]
    if since:
        sql += "AND published_at >= ? "
        params.append(since)
    sql += "ORDER BY COALESCE(published_at, fetched_at) DESC LIMIT ?"
    params.append(limit)
    cur = conn.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def prune_news(conn: sqlite3.Connection, days: int) -> int:
    cutoff = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cur = conn.execute(
        "DELETE FROM news_cache WHERE published_at IS NOT NULL "
        "AND published_at < datetime(?, ?)",
        (cutoff, f"-{days} days"),
    )
    conn.commit()
    return cur.rowcount


def fetch_and_store(ticker: str, name: Optional[str] = None) -> dict:
    """Fetch + upsert; 回傳 summary."""
    items = fetch_google_news(ticker, name)
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_news_cache(conn)
        added = upsert_news(conn, ticker, items)
        total = conn.execute(
            "SELECT COUNT(*) FROM news_cache WHERE ticker = ?", (ticker,)
        ).fetchone()[0]
    finally:
        conn.close()
    return {"ticker": ticker, "fetched": len(items), "added": added, "total_in_db": total}


# ── CLI ─────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--name", default=None, help="公司中文簡稱 (提高搜尋相關性)")
    ap.add_argument("--prune-days", type=int, default=None)
    ap.add_argument("--show", type=int, default=5, help="抓完後印出最新 N 筆")
    args = ap.parse_args()

    summary = fetch_and_store(args.ticker, args.name)
    print(summary)

    if args.prune_days:
        conn = sqlite3.connect(DB_PATH)
        try:
            ensure_news_cache(conn)
            removed = prune_news(conn, args.prune_days)
        finally:
            conn.close()
        print(f"prune > {args.prune_days}d: removed {removed}")

    if args.show:
        conn = sqlite3.connect(DB_PATH)
        try:
            for n in load_news(conn, args.ticker, limit=args.show):
                print(f"  [{n['published_at']}] ({n['source']}) {n['title']}")
        finally:
            conn.close()


if __name__ == "__main__":
    main()
