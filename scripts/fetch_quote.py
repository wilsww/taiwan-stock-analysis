"""即時五檔 / 成交 快取查詢 (MIS API).

用法:
    from fetch_quote import fetch_quote
    q = fetch_quote("2330")          # TSE / OTC 自動嘗試
    q["price"], q["bids"], q["asks"]

不落地; 由 dashboard 端用 st.cache_data(ttl=5) 做記憶體快取.

本檔通過 P3 小樣本驗證:
- 2330 (TSE) / 6488 (OTC) / 3037 (TSE) 欄位正確
- 不存在代號 (9999) 回 rtcode=0000 但 c 為空字串, 以此判別

SSL 備註:
    TWSE 憑證缺 Subject Key Identifier; Python 3.13 OpenSSL 3.5 預設
    VERIFY_X509_STRICT 會擋. 在本機 Session 關掉 strict flag, 但仍驗證鏈.
"""
from __future__ import annotations

import ssl
import time
from dataclasses import dataclass
from typing import Optional

import requests
from requests.adapters import HTTPAdapter


MIS_ENDPOINT = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
MIS_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://mis.twse.com.tw/stock/index.jsp",
}


class _TwseLegacyAdapter(HTTPAdapter):
    """關閉 X509_STRICT 以相容 TWSE 舊憑證 (缺 SKI)."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


_session: Optional[requests.Session] = None


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.mount("https://", _TwseLegacyAdapter())
        _session = s
    return _session


@dataclass
class QuoteLevel:
    price: float
    volume: int


def _parse_levels(price_str: Optional[str], vol_str: Optional[str]) -> list[QuoteLevel]:
    if not price_str or not vol_str:
        return []
    prices = [p for p in price_str.split("_") if p]
    vols = [v for v in vol_str.split("_") if v]
    out: list[QuoteLevel] = []
    for p, v in zip(prices, vols):
        try:
            out.append(QuoteLevel(price=float(p), volume=int(v)))
        except ValueError:
            continue
    return out


def _to_float(x) -> Optional[float]:
    if x in (None, "", "-"):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _to_int(x) -> Optional[int]:
    if x in (None, "", "-"):
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def fetch_quote(ticker: str, timeout: float = 5.0) -> Optional[dict]:
    """一次查詢 TSE + OTC, 回傳成交 + 買賣五檔.

    回傳 None = 查無此代號.
    """
    ticker = str(ticker).strip()
    if not ticker:
        return None
    ch = f"tse_{ticker}.tw|otc_{ticker}.tw"
    params = {
        "ex_ch": ch,
        "json": "1",
        "delay": "0",
        "_": str(int(time.time() * 1000)),
    }
    try:
        r = _get_session().get(MIS_ENDPOINT, params=params, headers=MIS_HEADERS, timeout=timeout)
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        return {"error": str(exc), "ticker": ticker}

    if data.get("rtcode") != "0000":
        return {"error": f"MIS rtcode={data.get('rtcode')} {data.get('rtmessage')}", "ticker": ticker}

    rows = [m for m in data.get("msgArray", []) if m.get("c")]
    if not rows:
        return None
    m = rows[0]

    last_price = _to_float(m.get("z"))
    prev_close = _to_float(m.get("y"))
    change = None
    change_pct = None
    if last_price is not None and prev_close:
        change = last_price - prev_close
        change_pct = change / prev_close * 100

    return {
        "ticker": m.get("c"),
        "name": m.get("n"),
        "full_name": m.get("nf"),
        "exchange": m.get("ex"),
        "last": last_price,
        "prev_close": prev_close,
        "open": _to_float(m.get("o")),
        "high": _to_float(m.get("h")),
        "low": _to_float(m.get("l")),
        "volume": _to_int(m.get("v")),
        "change": change,
        "change_pct": change_pct,
        "asks": _parse_levels(m.get("a"), m.get("f")),  # 賣五 (由低到高)
        "bids": _parse_levels(m.get("b"), m.get("g")),  # 買五 (由高到低)
        "trade_date": m.get("d"),
        "trade_time": m.get("t"),
        "updated_at": m.get("%"),
        "tlong": _to_int(m.get("tlong")),
    }


if __name__ == "__main__":
    import json
    import sys

    tks = sys.argv[1:] or ["2330", "6488", "3037", "9999"]
    for t in tks:
        q = fetch_quote(t)
        print(f"--- {t} ---")
        print(json.dumps(q, ensure_ascii=False, indent=2, default=lambda o: o.__dict__))
