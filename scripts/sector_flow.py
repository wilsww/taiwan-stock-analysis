#!/usr/bin/env python3
"""
sector_flow.py — 主力資金類股輪動分析

資料來源：TWSE T86（三大法人買賣超）+ SQLite 快取
輸出：reports/sector_flow_{start}_{end}.md（預設）
      data/sector_flow_{start}_{end}.json（--json）

用法：
  python3 scripts/sector_flow.py --start 2026-03-01 --end 2026-04-16
  python3 scripts/sector_flow.py --start 2026-01-01 --end 2026-04-16 --split month
  python3 scripts/sector_flow.py --start 2026-01-01 --end 2026-04-16 --split week
  python3 scripts/sector_flow.py --start 2026-03-01 --end 2026-04-16 --no-fetch
  python3 scripts/sector_flow.py --start 2026-01-01 --end 2026-04-16 --tier ai_supply_chain --json
  python3 scripts/sector_flow.py --start 2026-01-01 --end 2026-04-16 --tier all --split month
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import time
import urllib.request
from datetime import datetime, date, timedelta
from itertools import groupby
from pathlib import Path

# ── 路徑設定 ──────────────────────────────────────────────────
ROOT_DIR      = Path(__file__).parent.parent
DATA_DIR      = ROOT_DIR / "data"
REVENUE_DIR   = DATA_DIR / "revenue"
REPORTS_DIR   = ROOT_DIR / "reports"
DB_PATH       = REVENUE_DIR / "revenue.db"
UNIVERSE_PATH = ROOT_DIR / "research" / "stock_universe.json"

# ── 類股分類（fallback：stock_universe.json 不存在時使用）──────
_FALLBACK_CATEGORIES = {
    "DRAM 記憶體": {
        "2408": "南亞科技",
        "2344": "華邦電子",
    },
    "CPO 光通訊核心": {
        "3363": "上詮光纖",
        "2455": "全新光電",
        "4979": "華星光通",
        "3081": "聯亞光電",
        "3105": "穩懋半導體",
    },
    "CPO 光通訊周邊": {
        "6442": "光聖",
        "4977": "眾達-KY",
        "3163": "波若威",
        "2345": "智邦",
        "6223": "旺矽",
    },
    "IC 載板 PCB": {
        "3037": "欣興電子",
        "8046": "南亞電路板",
        "3189": "景碩科技",
    },
}


def load_universe(tier: str = "ai_supply_chain") -> tuple[dict, dict, dict, str]:
    """
    讀取 research/stock_universe.json，回傳:
      categories   : {cat_name: {ticker: name}}
      all_tickers  : {ticker: name}
      ticker_to_cat: {ticker: cat_name}
      tier_label   : str（顯示用）

    tier: 'ai_supply_chain' | 'broad_themes' | 'all'
    若 JSON 不存在則使用 fallback（15 檔 / 4 類股）。
    """
    if not UNIVERSE_PATH.exists():
        cats = _FALLBACK_CATEGORIES
        all_t = {t: n for c in cats.values() for t, n in c.items()}
        t2c   = {t: cat for cat, stks in cats.items() for t in stks}
        return cats, all_t, t2c, "預設分類（fallback）"

    universe = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
    companies = universe["companies"]  # {ticker: {"name": ...}}
    tiers_def = universe["tiers"]

    if tier == "all":
        # 合併所有 tier
        merged_cats: dict[str, list] = {}
        for tier_data in tiers_def.values():
            for cat_name, ticker_list in tier_data["categories"].items():
                merged_cats.setdefault(cat_name, []).extend(ticker_list)
        tier_label = "全部標的"
        raw_cats = merged_cats
    else:
        tier_data = tiers_def[tier]
        tier_label = tier_data["label"]
        raw_cats = tier_data["categories"]  # {cat_name: [ticker, ...]}

    # 建立 categories dict（去重）
    categories: dict[str, dict] = {}
    seen: set = set()
    for cat_name, ticker_list in raw_cats.items():
        cat_dict: dict = {}
        for ticker in ticker_list:
            if ticker in seen:
                continue
            seen.add(ticker)
            name = companies.get(ticker, {}).get("name", ticker)
            cat_dict[ticker] = name
        if cat_dict:
            categories[cat_name] = cat_dict

    all_tickers   = {t: n for c in categories.values() for t, n in c.items()}
    ticker_to_cat = {t: cat for cat, stks in categories.items() for t in stks}

    return categories, all_tickers, ticker_to_cat, tier_label


# ── DB 初始化 ──────────────────────────────────────────────────
def _ensure_daily_price_columns(conn: sqlite3.Connection) -> None:
    """讓舊版 DB 也具備日 OHLCV 欄位。"""
    for col in ("open", "high", "low", "volume"):
        try:
            conn.execute(f"ALTER TABLE daily_price ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass


def init_db():
    REVENUE_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS institutional_flow (
            ticker        TEXT NOT NULL,
            trade_date    TEXT NOT NULL,
            foreign_net   REAL,
            invest_net    REAL,
            dealer_net    REAL,
            total_net     REAL,
            foreign_value REAL,
            invest_value  REAL,
            dealer_value  REAL,
            total_value   REAL,
            updated_at    TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    # 舊 DB 升級：補上 *_value 欄位（ALTER TABLE 若已存在會報錯，吞掉）
    for col in ("foreign_value", "invest_value", "dealer_value", "total_value"):
        try:
            conn.execute(f"ALTER TABLE institutional_flow ADD COLUMN {col} REAL")
        except sqlite3.OperationalError:
            pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_price (
            ticker      TEXT NOT NULL,
            trade_date  TEXT NOT NULL,
            open        REAL,
            high        REAL,
            low         REAL,
            close       REAL,
            volume      REAL,
            updated_at  TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    _ensure_daily_price_columns(conn)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_date
        ON daily_price(trade_date)
    """)
    # 融資融券（單位：張，1 張 = 1000 股）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS margin_flow (
            ticker          TEXT NOT NULL,
            trade_date      TEXT NOT NULL,
            margin_buy      REAL,   -- 融資買進
            margin_sell     REAL,   -- 融資賣出
            margin_balance  REAL,   -- 融資今日餘額
            margin_prev     REAL,   -- 融資前日餘額
            short_sell      REAL,   -- 融券賣出
            short_cover     REAL,   -- 融券買進（回補）
            short_balance   REAL,   -- 融券今日餘額
            short_prev      REAL,   -- 融券前日餘額
            updated_at      TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_margin_date ON margin_flow(trade_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_margin_ticker_date ON margin_flow(ticker, trade_date)")
    # 券商分點（單位：張）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS broker_flow (
            ticker        TEXT NOT NULL,
            trade_date    TEXT NOT NULL,
            broker_name   TEXT NOT NULL,
            buy_lots      REAL,    -- 買張
            sell_lots     REAL,    -- 賣張
            net_lots      REAL,    -- 買超（淨）
            avg_price     REAL,
            updated_at    TEXT,
            PRIMARY KEY (ticker, trade_date, broker_name)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_broker_date ON broker_flow(trade_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_broker_tkr ON broker_flow(ticker, trade_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_broker_name ON broker_flow(broker_name, trade_date)")
    # 外資持股（TWSE MI_QFIIS）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS foreign_ownership (
            ticker          TEXT NOT NULL,
            trade_date      TEXT NOT NULL,
            issued_shares   REAL,     -- 發行股數
            foreign_shares  REAL,     -- 全體外資及陸資持有股數
            foreign_pct     REAL,     -- 持股比率 %
            remaining_pct   REAL,     -- 尚可投資比率 %
            limit_pct       REAL,     -- 法令上限 %
            updated_at      TEXT,
            PRIMARY KEY (ticker, trade_date)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_qfii_date ON foreign_ownership(trade_date)")
    # 期貨未平倉（TAIFEX 三大法人，單位：口）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS futures_oi (
            trade_date     TEXT NOT NULL,
            contract       TEXT NOT NULL,     -- TXF/MTX/TEF/TFF
            role           TEXT NOT NULL,     -- foreign/invest/dealer
            long_oi        REAL,              -- 多方未平倉口數
            short_oi       REAL,              -- 空方未平倉口數
            net_oi         REAL,              -- 多空淨額
            long_value     REAL,              -- 多方契約金額（千元）
            short_value    REAL,
            net_value      REAL,
            updated_at     TEXT,
            PRIMARY KEY (trade_date, contract, role)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_fut_date ON futures_oi(trade_date)")
    # TDCC 集保持股分級（週資料）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS shareholder_distribution (
            ticker       TEXT NOT NULL,
            data_date    TEXT NOT NULL,   -- YYYY-MM-DD
            tier_code    INTEGER NOT NULL,  -- 1..15 / 16 差異 / 17 合計
            holders      INTEGER,
            shares       REAL,
            pct          REAL,
            updated_at   TEXT,
            PRIMARY KEY (ticker, data_date, tier_code)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tdcc_date ON shareholder_distribution(data_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tdcc_ticker ON shareholder_distribution(ticker, data_date)")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trading_calendar (
            trade_date  TEXT PRIMARY KEY,
            updated_at  TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_flow_date
        ON institutional_flow(trade_date)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_flow_ticker_date
        ON institutional_flow(ticker, trade_date)
    """)
    conn.commit()
    conn.close()


# ── TWSE 開盤日曆 ─────────────────────────────────────────────
def fetch_twse_calendar(year: int, month: int) -> list[str]:
    """
    從 TWSE FMTQIK API 取得指定月份實際有交易的日期清單。
    回傳: ["YYYY-MM-DD", ...]（已排序）
    """
    ym = f"{year}{month:02d}01"
    url = (
        f"https://www.twse.com.tw/exchangeReport/FMTQIK"
        f"?response=json&date={ym}&selectType=MS"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
        "Referer": "https://www.twse.com.tw/",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ TWSE 月曆 API 錯誤 ({year}/{month:02d}): {e}")
        return []

    if data.get("stat") != "OK" or not data.get("data"):
        return []

    result = []
    for row in data["data"]:
        # row[0]: 民國年/月/日，例如 "115/01/02"
        parts = row[0].split("/")
        if len(parts) == 3:
            try:
                y = int(parts[0]) + 1911
                m = int(parts[1])
                d = int(parts[2])
                result.append(f"{y}-{m:02d}-{d:02d}")
            except ValueError:
                continue
    return sorted(result)


def ensure_calendar(start: date, end: date) -> list[str]:
    """
    確保 [start, end] 內每個月的開盤日都在 trading_calendar DB 中。
    若 DB 缺該月資料則從 TWSE 抓取並寫入。
    回傳：該區間內所有實際開盤日（YYYY-MM-DD）。
    """
    # 收集需要查詢的年月
    months_needed: set[tuple[int, int]] = set()
    d = start.replace(day=1)
    while d <= end:
        months_needed.add((d.year, d.month))
        # 下個月
        if d.month == 12:
            d = d.replace(year=d.year + 1, month=1)
        else:
            d = d.replace(month=d.month + 1)

    conn = sqlite3.connect(DB_PATH)

    # 查 DB 中已有哪些月份的資料（聚合查詢，避免全表掃描）
    cached_months = {
        (int(y), int(m))
        for y, m in conn.execute(
            "SELECT DISTINCT strftime('%Y', trade_date), strftime('%m', trade_date) "
            "FROM trading_calendar"
        ).fetchall()
    }

    # 缺漏月份從 TWSE 補抓
    missing_months = months_needed - cached_months
    now = datetime.now().isoformat()
    for year, month in sorted(missing_months):
        # 未來月份不抓（TWSE 無資料）
        today = date.today()
        if date(year, month, 1) > today:
            continue
        print(f"  抓取 TWSE 月曆 {year}/{month:02d}...", end=" ", flush=True)
        open_dates = fetch_twse_calendar(year, month)
        time.sleep(0.3)
        if open_dates:
            conn.executemany(
                "INSERT OR REPLACE INTO trading_calendar (trade_date, updated_at) VALUES (?, ?)",
                [(d, now) for d in open_dates],
            )
            conn.commit()
            print(f"{len(open_dates)} 個開盤日")
        else:
            print("無資料")

    # 從 DB 取出 [start, end] 範圍內開盤日
    start_str = start.strftime("%Y-%m-%d")
    end_str   = end.strftime("%Y-%m-%d")
    rows = conn.execute(
        "SELECT trade_date FROM trading_calendar WHERE trade_date BETWEEN ? AND ? ORDER BY trade_date",
        (start_str, end_str),
    ).fetchall()
    conn.close()

    return [r[0] for r in rows]


# ── TWSE T86 API ──────────────────────────────────────────────
def fetch_t86(trade_date_str: str, all_tickers: dict) -> dict:
    """
    抓 T86 當日三大法人買賣超。
    trade_date_str: YYYYMMDD
    回傳: {ticker: {foreign, invest, dealer, total}}
    """
    url = (
        f"https://www.twse.com.tw/fund/T86"
        f"?response=json&date={trade_date_str}&selectType=ALLBUT0999"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
        "Referer": "https://www.twse.com.tw/",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ T86 API 錯誤 ({trade_date_str}): {e}")
        return {}

    if data.get("stat") != "OK" or not data.get("data"):
        return {}

    def p(s) -> float:
        if isinstance(s, (int, float)):
            return float(s)
        return float(str(s).replace(",", "").replace("--", "0") or 0)

    # T86 欄位（2022-2026 穩定 19 欄）:
    #  [0] 證券代號   [1] 證券名稱
    #  [4] 外陸資買賣超（不含外資自營）
    #  [7] 外資自營商買賣超
    #  [10] 投信買賣超
    #  [11] 自營商買賣超（合計 = 自行 + 避險）
    #  [14] 自營商買賣超（自行買賣）
    #  [17] 自營商買賣超（避險）
    #  [18] 三大法人買賣超
    # 外資合計 = row[4] + row[7]（外陸資 + 外資自營商）
    result = {}
    for row in data["data"]:
        if not row or len(row) < 19:
            continue
        ticker = row[0].strip()
        if ticker in all_tickers:
            foreign = p(row[4]) + p(row[7])
            invest  = p(row[10])
            dealer  = p(row[11])
            total   = p(row[18])
            result[ticker] = {
                "foreign": foreign,
                "invest":  invest,
                "dealer":  dealer,
                "total":   total,
            }
    return result


# ── TPEx 上櫃三大法人 ─────────────────────────────────────────
def fetch_tpex_institutional(trade_date_str: str, all_tickers: dict) -> dict:
    """
    抓 TPEx（上櫃）當日三大法人買賣超。
    trade_date_str: YYYYMMDD（西元）；內部轉民國 YYY/MM/DD
    回傳: {ticker: {foreign, invest, dealer, total}}

    TPEx 端點：24 欄位 group
      [0]代號 [1]名稱
      [2:5]外資 買/賣/買賣超
      [5:8]陸資
      [8:11]外資+陸資合計
      [11:14]投信
      [14:17]自營商自行
      [17:20]自營商避險
      [20:23]自營商合計
      [23]三大法人買賣超
    外資口徑對齊 TWSE：採 row[10]（外資+陸資合計）
    """
    y = int(trade_date_str[:4]) - 1911
    m = trade_date_str[4:6]
    d = trade_date_str[6:8]
    roc_date = f"{y}/{m}/{d}"
    url = (
        f"https://www.tpex.org.tw/web/stock/3insti/DAILY_TradE/"
        f"3itrade_hedge_result.php?d={roc_date}&t=D&s=0,asc,0&l=zh-tw"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ TPEx 3insti API 錯誤 ({trade_date_str}): {e}")
        return {}

    tables = data.get("tables") or []
    if not tables:
        return {}
    rows = tables[0].get("data") or []

    def p(s) -> float:
        if isinstance(s, (int, float)):
            return float(s)
        return float(str(s).replace(",", "").replace("--", "0") or 0)

    result = {}
    for row in rows:
        if not row or len(row) < 24:
            continue
        ticker = row[0].strip()
        if ticker in all_tickers:
            foreign = p(row[10])   # 外資+陸資合計
            invest  = p(row[13])   # 投信
            dealer  = p(row[22])   # 自營商合計
            total   = p(row[23])   # 三大法人合計
            result[ticker] = {
                "foreign": foreign,
                "invest":  invest,
                "dealer":  dealer,
                "total":   total,
            }
    return result


# ── TWSE 全市場收盤價 ─────────────────────────────────────────
def fetch_close_prices(trade_date_str: str, all_tickers: dict) -> dict:
    """
    抓某日全市場收盤價。TWSE STOCK_DAY_ALL 僅提供「當日」；
    歷史日期用 STOCK_DAY（逐股查月資料）— 這裡採當日批次 + 月資料回補兩套。

    trade_date_str: YYYYMMDD
    回傳: {ticker: close}
    """
    today_compact = date.today().strftime("%Y%m%d")
    if trade_date_str == today_compact:
        url = "https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json"
    else:
        # 歷史用 MI_INDEX 全市場日收盤（含當日所有個股）
        url = (
            f"https://www.twse.com.tw/exchangeReport/MI_INDEX"
            f"?response=json&date={trade_date_str}&type=ALLBUT0999"
        )
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Accept": "application/json",
        "Referer": "https://www.twse.com.tw/",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ 收盤價 API 錯誤 ({trade_date_str}): {e}")
        return {}

    def p(s) -> float:
        if isinstance(s, (int, float)):
            return float(s)
        s = str(s).replace(",", "").replace("--", "0").strip()
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    result = {}
    if trade_date_str == today_compact:
        if data.get("stat") != "OK" or not data.get("data"):
            return {}
        # STOCK_DAY_ALL fields: [證券代號,證券名稱,成交股數,成交金額,開盤,高,低,收盤,...]
        for row in data["data"]:
            ticker = row[0].strip()
            if ticker in all_tickers:
                close = p(row[7])
                if close > 0:
                    result[ticker] = close
    else:
        # MI_INDEX 回傳多張表，找欄位含「證券代號」「收盤價」的 tables
        tables = data.get("tables") or []
        if not tables and data.get("data9"):
            # 舊格式 fallback
            for row in data.get("data9", []):
                ticker = row[0].strip() if row else ""
                if ticker in all_tickers and len(row) > 8:
                    close = p(row[8])
                    if close > 0:
                        result[ticker] = close
        for tbl in tables:
            fields = tbl.get("fields") or []
            if "證券代號" not in fields or "收盤價" not in fields:
                continue
            idx_t = fields.index("證券代號")
            idx_c = fields.index("收盤價")
            for row in tbl.get("data", []):
                if len(row) <= max(idx_t, idx_c):
                    continue
                ticker = str(row[idx_t]).strip()
                if ticker in all_tickers:
                    close = p(row[idx_c])
                    if close > 0:
                        result[ticker] = close
    return result


def fetch_tpex_close_prices(trade_date_str: str, all_tickers: dict) -> dict:
    """抓 TPEx 當日個股收盤價。trade_date_str: YYYYMMDD。"""
    y = int(trade_date_str[:4]) - 1911
    m = trade_date_str[4:6]
    d = trade_date_str[6:8]
    roc_date = f"{y}/{m}/{d}"
    url = (
        f"https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/"
        f"stk_quote_result.php?d={roc_date}&se=AL&s=0,asc,0&l=zh-tw"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ TPEx 收盤價 API 錯誤 ({trade_date_str}): {e}")
        return {}

    tables = data.get("tables") or []
    if not tables:
        return {}
    rows = tables[0].get("data") or []

    def p(s) -> float:
        if isinstance(s, (int, float)):
            return float(s)
        s = str(s).replace(",", "").replace("--", "0").strip()
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    result = {}
    for row in rows:
        if not row or len(row) < 3:
            continue
        ticker = str(row[0]).strip()
        if ticker in all_tickers:
            close = p(row[2])
            if close > 0:
                result[ticker] = close
    return result


# ── 融資融券（TWSE MI_MARGN + TPEx margin_bal） ────────────────
def _p_num(s) -> float:
    if isinstance(s, (int, float)):
        return float(s)
    s = str(s).replace(",", "").replace("--", "0").strip()
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def fetch_twse_margin(trade_date_str: str, all_tickers: dict) -> dict:
    """TWSE 融資融券（MI_MARGN）單位：張。
    欄位順序：[0]代號 [1]名稱
              [2]資買 [3]資賣 [4]現償 [5]資前餘 [6]資今餘
              [8]券買 [9]券賣 [10]券現償 [11]券前餘 [12]券今餘
    """
    url = (
        f"https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
        f"?date={trade_date_str}&selectType=ALL&response=json"
    )
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.twse.com.tw/"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ TWSE MI_MARGN 錯誤 ({trade_date_str}): {e}")
        return {}

    tables = data.get("tables") or []
    rows = []
    for tb in tables:
        if tb.get("fields") and "代號" in tb["fields"]:
            rows = tb.get("data", [])
            break
    result = {}
    for row in rows:
        if not row or len(row) < 14:
            continue
        ticker = str(row[0]).strip()
        if ticker in all_tickers:
            result[ticker] = {
                "margin_buy":     _p_num(row[2]),
                "margin_sell":    _p_num(row[3]),
                "margin_prev":    _p_num(row[5]),
                "margin_balance": _p_num(row[6]),
                "short_buy":      _p_num(row[8]),   # 券買（回補）
                "short_sell":     _p_num(row[9]),
                "short_prev":     _p_num(row[11]),
                "short_balance":  _p_num(row[12]),
            }
    return result


def fetch_tpex_margin(trade_date_str: str, all_tickers: dict) -> dict:
    """TPEx 融資融券（margin_bal）單位：張。
    欄位：[0]代號 [1]名稱
          [2]前資餘 [3]資買 [4]資賣 [5]現償 [6]資餘額
          [10]前券餘 [11]券賣 [12]券買 [13]券償 [14]券餘額
    """
    y = int(trade_date_str[:4]) - 1911
    m = trade_date_str[4:6]
    d = trade_date_str[6:8]
    roc_date = f"{y}/{m}/{d}"
    url = (
        f"https://www.tpex.org.tw/web/stock/margin_trading/margin_balance/"
        f"margin_bal_result.php?d={roc_date}&l=zh-tw"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ TPEx margin 錯誤 ({trade_date_str}): {e}")
        return {}

    tables = data.get("tables") or []
    if not tables:
        return {}
    rows = tables[0].get("data") or []
    result = {}
    for row in rows:
        if not row or len(row) < 15:
            continue
        ticker = str(row[0]).strip()
        if ticker in all_tickers:
            result[ticker] = {
                "margin_prev":    _p_num(row[2]),
                "margin_buy":     _p_num(row[3]),
                "margin_sell":    _p_num(row[4]),
                "margin_balance": _p_num(row[6]),
                "short_prev":     _p_num(row[10]),
                "short_sell":     _p_num(row[11]),
                "short_buy":      _p_num(row[12]),
                "short_balance":  _p_num(row[14]),
            }
    return result


def load_margin_from_db(dates: list[str]) -> dict[tuple, dict]:
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT ticker, trade_date, margin_buy, margin_sell, margin_balance, margin_prev, "
        f"       short_sell, short_cover, short_balance, short_prev "
        f"FROM margin_flow WHERE trade_date IN ({placeholders})",
        dates,
    ).fetchall()
    conn.close()
    return {
        (r[0], r[1]): {
            "margin_buy": r[2], "margin_sell": r[3],
            "margin_balance": r[4], "margin_prev": r[5],
            "short_sell": r[6], "short_cover": r[7],
            "short_balance": r[8], "short_prev": r[9],
        } for r in rows
    }


def save_margin_to_db(rows: list[dict]):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO margin_flow
           (ticker, trade_date, margin_buy, margin_sell, margin_balance, margin_prev,
            short_sell, short_cover, short_balance, short_prev, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r["ticker"], r["trade_date"],
          r.get("margin_buy", 0), r.get("margin_sell", 0),
          r.get("margin_balance", 0), r.get("margin_prev", 0),
          r.get("short_sell", 0), r.get("short_buy", 0),
          r.get("short_balance", 0), r.get("short_prev", 0), now)
         for r in rows],
    )
    conn.commit()
    conn.close()


def ensure_margin_data(dates: list[str], all_tickers: dict, no_fetch: bool = False) -> dict[tuple, dict]:
    """確保融資融券資料。TWSE + TPEx 合併。"""
    cached = load_margin_from_db(dates)
    dates_with_data = {d for _, d in cached.keys()}
    missing = [d for d in dates if d not in dates_with_data]

    if missing and not no_fetch:
        print(f"  需補抓 {len(missing)} 個交易日融資融券...")
        new_rows = []
        for dt in missing:
            dt_compact = dt.replace("-", "")
            print(f"  margin {dt} ...", end=" ", flush=True)
            twse = fetch_twse_margin(dt_compact, all_tickers)
            time.sleep(0.4)
            tpex = fetch_tpex_margin(dt_compact, all_tickers)
            merged = {**twse, **tpex}
            if merged:
                for ticker, vals in merged.items():
                    new_rows.append({"ticker": ticker, "trade_date": dt, **vals})
                print(f"取得 {len(merged)} 筆（TWSE {len(twse)} + TPEx {len(tpex)}）")
            else:
                print("無資料")
            time.sleep(0.4)
        save_margin_to_db(new_rows)
        for r in new_rows:
            cached[(r["ticker"], r["trade_date"])] = {
                k: r.get(k, 0) for k in
                ("margin_buy","margin_sell","margin_balance","margin_prev",
                 "short_sell","short_buy","short_balance","short_prev")
            }
            # 欄名映射（save 用 short_buy，load 用 short_cover）
            cached[(r["ticker"], r["trade_date"])]["short_cover"] = r.get("short_buy", 0)
    return cached


# ── TDCC 集保分級（OpenData 1-5，週更新） ──────────────────
TDCC_TIER_LABELS = {
    1: "1~999 股", 2: "1,000~5,000", 3: "5,001~10,000", 4: "10,001~15,000",
    5: "15,001~20,000", 6: "20,001~30,000", 7: "30,001~40,000", 8: "40,001~50,000",
    9: "50,001~100,000", 10: "100,001~200,000", 11: "200,001~400,000",
    12: "400,001~600,000", 13: "600,001~800,000", 14: "800,001~1,000,000",
    15: ">1,000,000（大戶 ≥1000 張）",
    16: "差異數調整", 17: "合計",
}


def fetch_tdcc_distribution(all_tickers: dict) -> list[dict]:
    """
    TDCC OpenData 1-5：集保持股分級（每週五更新上週資料）。
    URL 固定；回傳全部上市櫃，只留 all_tickers 中的。
    """
    url = "https://opendata.tdcc.com.tw/getOD.ashx?id=1-5"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"  ⚠ TDCC 1-5 錯誤: {e}")
        return []
    text = raw.decode("utf-8", errors="ignore").lstrip("\ufeff")
    lines = text.splitlines()
    if len(lines) < 2:
        return []
    result = []
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 6:
            continue
        d8, ticker, tier_s, holders_s, shares_s, pct_s = parts[:6]
        ticker = ticker.strip()
        if ticker not in all_tickers:
            continue
        if len(d8) != 8:
            continue
        iso_d = f"{d8[:4]}-{d8[4:6]}-{d8[6:8]}"
        try:
            tier_code = int(tier_s)
        except ValueError:
            continue
        result.append({
            "ticker":    ticker,
            "data_date": iso_d,
            "tier_code": tier_code,
            "holders":   int(_p_num(holders_s)),
            "shares":    _p_num(shares_s),
            "pct":       _p_num(pct_s),
        })
    return result


def save_tdcc_to_db(rows: list[dict]):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO shareholder_distribution
           (ticker, data_date, tier_code, holders, shares, pct, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [(r["ticker"], r["data_date"], r["tier_code"],
          r["holders"], r["shares"], r["pct"], now) for r in rows],
    )
    conn.commit()
    conn.close()


def load_tdcc_latest(tickers: list[str]) -> dict:
    """回傳 {ticker: {tier_code: {holders, shares, pct, data_date}}}（最新週）。"""
    if not tickers:
        return {}
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(tickers))
    # 各 ticker 最新 data_date
    rows = conn.execute(
        f"""WITH latest AS (
              SELECT ticker, MAX(data_date) AS d FROM shareholder_distribution
              WHERE ticker IN ({placeholders}) GROUP BY ticker
            )
            SELECT s.ticker, s.data_date, s.tier_code, s.holders, s.shares, s.pct
            FROM shareholder_distribution s JOIN latest l
              ON s.ticker=l.ticker AND s.data_date=l.d
        """, tickers,
    ).fetchall()
    conn.close()
    out: dict = {}
    for tk, d, tier, holders, shares, pct in rows:
        out.setdefault(tk, {})[tier] = {
            "holders": holders, "shares": shares, "pct": pct, "data_date": d,
        }
    return out


def ensure_tdcc_data(all_tickers: dict, no_fetch: bool = False):
    """週資料；若 DB 中 < 7 天則重抓。"""
    if no_fetch:
        return
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT MAX(data_date) FROM shareholder_distribution").fetchone()
    conn.close()
    latest_db = row[0] if row and row[0] else None
    need_fetch = True
    if latest_db:
        try:
            latest_dt = datetime.strptime(latest_db, "%Y-%m-%d").date()
            if (date.today() - latest_dt).days < 7:
                need_fetch = False
        except Exception:
            pass
    if need_fetch:
        print("  TDCC 1-5 下載中...", end=" ", flush=True)
        rows = fetch_tdcc_distribution(all_tickers)
        if rows:
            save_tdcc_to_db(rows)
            print(f"取得 {len(rows)} 筆")
        else:
            print("無")


# ── 期貨未平倉（TAIFEX futContractsDateDown 下載 CSV） ───────
_FUT_ROLE_MAP = {
    "自營商":    "dealer",
    "投信":      "invest",
    "外資及陸資": "foreign",
    "外資":      "foreign",
}
_FUT_CONTRACT_MAP = {
    "臺股期貨":     "TXF",
    "小型臺指期貨": "MXF",
    "電子期貨":     "EXF",
    "金融期貨":     "FXF",
}


def fetch_taifex_oi(trade_date_str: str, contract_id: str = "TXF") -> list[dict]:
    """TAIFEX 三大法人期貨未平倉 CSV。
    trade_date_str: YYYYMMDD
    contract_id: TXF(臺指)/MTX(小台)/TEF(電子)/TFF(金融)
    """
    import urllib.parse
    y = trade_date_str[:4]; m = trade_date_str[4:6]; d = trade_date_str[6:8]
    url = "https://www.taifex.com.tw/cht/3/futContractsDateDown"
    data = urllib.parse.urlencode({
        "queryStartDate": f"{y}/{m}/{d}",
        "queryEndDate":   f"{y}/{m}/{d}",
        "commodityId":    contract_id,
    }).encode()
    try:
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
    except Exception as e:
        print(f"  ⚠ TAIFEX {contract_id} 錯誤 ({trade_date_str}): {e}")
        return []
    try:
        text = raw.decode("big5")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="ignore")

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []
    result = []
    for ln in lines[1:]:
        parts = [p.strip() for p in ln.split(",")]
        if len(parts) < 15:
            continue
        dt_str      = parts[0].replace("/", "-")
        contract_cn = parts[1]
        role_cn     = parts[2]
        contract    = _FUT_CONTRACT_MAP.get(contract_cn, contract_id)
        role        = _FUT_ROLE_MAP.get(role_cn)
        if role is None:
            continue
        result.append({
            "trade_date":  dt_str,
            "contract":    contract,
            "role":        role,
            "long_oi":     _p_num(parts[9]),
            "long_value":  _p_num(parts[10]),
            "short_oi":    _p_num(parts[11]),
            "short_value": _p_num(parts[12]),
            "net_oi":      _p_num(parts[13]),
            "net_value":   _p_num(parts[14]),
        })
    return result


def save_futures_to_db(rows: list[dict]):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO futures_oi
           (trade_date, contract, role, long_oi, short_oi, net_oi,
            long_value, short_value, net_value, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r["trade_date"], r["contract"], r["role"],
          r.get("long_oi", 0), r.get("short_oi", 0), r.get("net_oi", 0),
          r.get("long_value", 0), r.get("short_value", 0), r.get("net_value", 0), now)
         for r in rows],
    )
    conn.commit()
    conn.close()


def load_futures_from_db(dates: list[str], contracts: list[str] = None) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    placeholders_d = ",".join("?" * len(dates))
    q = f"SELECT trade_date, contract, role, long_oi, short_oi, net_oi, net_value FROM futures_oi WHERE trade_date IN ({placeholders_d})"
    params = list(dates)
    if contracts:
        placeholders_c = ",".join("?" * len(contracts))
        q += f" AND contract IN ({placeholders_c})"
        params += contracts
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [
        {"trade_date": r[0], "contract": r[1], "role": r[2],
         "long_oi": r[3], "short_oi": r[4], "net_oi": r[5], "net_value": r[6]}
        for r in rows
    ]


def ensure_futures_data(dates: list[str], contracts: list[str] = None,
                        no_fetch: bool = False) -> None:
    """確保指定日期期貨 OI 在 DB。contracts 預設 [TXF, TEF]。"""
    if contracts is None:
        contracts = ["TXF", "EXF"]  # 臺指期 + 電子期
    cached = load_futures_from_db(dates, contracts)
    existing = {(r["trade_date"], r["contract"]) for r in cached}
    missing = [(dt, c) for dt in dates for c in contracts if (dt, c) not in existing]
    if missing and not no_fetch:
        print(f"  需補抓 {len(missing)} 筆期貨 OI...")
        new_rows = []
        for dt, c in missing:
            dt_compact = dt.replace("-", "")
            rows = fetch_taifex_oi(dt_compact, c)
            # TAIFEX 回傳日期可能已加斜線，規整為 YYYY-MM-DD
            for r in rows:
                r["trade_date"] = r["trade_date"].replace("/", "-")
            new_rows.extend(rows)
            time.sleep(0.5)
        save_futures_to_db(new_rows)


# ── 外資持股（TWSE MI_QFIIS） ────────────────────────────────
def fetch_foreign_ownership(trade_date_str: str, all_tickers: dict) -> dict:
    """TWSE MI_QFIIS 外資/陸資持股比例。
    欄位：[0]代號 [3]發行股數 [4]尚可投資股數 [5]持有股數
          [6]尚可投資比率% [7]持股比率% [8]法令上限%
    """
    url = (
        f"https://www.twse.com.tw/fund/MI_QFIIS"
        f"?response=json&date={trade_date_str}&selectType=ALLBUT0999"
    )
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.twse.com.tw/"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ MI_QFIIS 錯誤 ({trade_date_str}): {e}")
        return {}

    if data.get("stat") != "OK" or not data.get("data"):
        return {}

    result = {}
    for row in data["data"]:
        if not row or len(row) < 9:
            continue
        ticker = str(row[0]).strip()
        if ticker not in all_tickers:
            continue
        result[ticker] = {
            "issued_shares":  _p_num(row[3]),
            "foreign_shares": _p_num(row[5]),
            "remaining_pct":  _p_num(row[6]),
            "foreign_pct":    _p_num(row[7]),
            "limit_pct":      _p_num(row[8]),
        }
    return result


def fetch_tpex_foreign_ownership(all_tickers: dict) -> dict:
    """TPEx 外資持股（OpenAPI v1，回傳當日最新）。
    欄位：Date/SecuritiesCompanyCode/NumberOfSharesIssued/
          CurrentlySharesOC/FIHeld/PercentageOfAvailableInvestmentForOC/FI/
          PercentageOfSharesOC/FMIHeld/UpperLimitOfRegulatedInvestment
    """
    url = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_qfii"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as e:
        print(f"  ⚠ TPEx QFII 錯誤: {e}")
        return {}

    def pct(s: str) -> float:
        s = str(s).replace("%", "").replace(",", "").strip()
        try:
            return float(s) if s else 0.0
        except ValueError:
            return 0.0

    result = {}
    for row in data or []:
        ticker = row.get("SecuritiesCompanyCode", "").strip()
        if ticker not in all_tickers:
            continue
        # Date 格式民國 YYYMMDD（如 1150417）
        d_roc = row.get("Date", "")
        if len(d_roc) == 7:
            iso_date = f"{int(d_roc[:3])+1911}-{d_roc[3:5]}-{d_roc[5:7]}"
        else:
            iso_date = ""
        result[ticker] = {
            "issued_shares":  _p_num(row.get("NumberOfSharesIssued", 0)),
            "foreign_shares": _p_num(row.get("CurrentlySharesOC/FIHeld", 0)),
            "remaining_pct":  pct(row.get("PercentageOfAvailableInvestmentForOC/FI", 0)),
            "foreign_pct":    pct(row.get("PercentageOfSharesOC/FMIHeld", 0)),
            "limit_pct":      pct(row.get("UpperLimitOfRegulatedInvestment", 0)),
            "_date":          iso_date,
        }
    return result


def save_qfii_to_db(rows: list[dict]):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO foreign_ownership
           (ticker, trade_date, issued_shares, foreign_shares, foreign_pct,
            remaining_pct, limit_pct, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r["ticker"], r["trade_date"],
          r.get("issued_shares", 0), r.get("foreign_shares", 0),
          r.get("foreign_pct", 0), r.get("remaining_pct", 0),
          r.get("limit_pct", 0), now) for r in rows],
    )
    conn.commit()
    conn.close()


def load_qfii_from_db(dates: list[str]) -> dict[tuple, dict]:
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT ticker, trade_date, issued_shares, foreign_shares, foreign_pct, "
        f"       remaining_pct, limit_pct "
        f"FROM foreign_ownership WHERE trade_date IN ({placeholders})",
        dates,
    ).fetchall()
    conn.close()
    return {
        (r[0], r[1]): {
            "issued_shares": r[2], "foreign_shares": r[3],
            "foreign_pct": r[4], "remaining_pct": r[5], "limit_pct": r[6],
        } for r in rows
    }


def ensure_qfii_data(dates: list[str], all_tickers: dict, no_fetch: bool = False):
    cached = load_qfii_from_db(dates)
    dates_with_data = {d for _, d in cached.keys()}
    missing = [d for d in dates if d not in dates_with_data]
    if missing and not no_fetch:
        print(f"  需補抓 {len(missing)} 個交易日外資持股...")
        new_rows = []
        # TPEx 只提供當日快照，對所有 missing 日期都用當前資料（持股變化慢）
        tpex_snap = fetch_tpex_foreign_ownership(all_tickers)
        time.sleep(0.4)
        for dt in missing:
            dt_compact = dt.replace("-", "")
            print(f"  QFII {dt} ...", end=" ", flush=True)
            got = fetch_foreign_ownership(dt_compact, all_tickers)
            # 合併 TPEx 當日快照（覆蓋 OTC 標的）
            for tk, v in tpex_snap.items():
                got.setdefault(tk, {k: v[k] for k in v if not k.startswith("_")})
            if got:
                for tk, v in got.items():
                    new_rows.append({"ticker": tk, "trade_date": dt,
                                     **{k: v[k] for k in v if not k.startswith("_")}})
                print(f"{len(got)} 筆")
            else:
                print("無")
            time.sleep(0.4)
        save_qfii_to_db(new_rows)
        for r in new_rows:
            cached[(r["ticker"], r["trade_date"])] = {
                k: r[k] for k in ("issued_shares","foreign_shares","foreign_pct","remaining_pct","limit_pct")
            }
    return cached


# ── 券商分點（HiStock branch.aspx） ──────────────────────────
def fetch_broker_histock(ticker: str) -> list[dict]:
    """
    抓 HiStock 單股當日分點前 15 大（買方 + 賣方）。
    無日期參數，僅回傳當日資料。
    回傳 [{broker_name, buy_lots, sell_lots, net_lots, avg_price}, ...]
    """
    url = f"https://histock.tw/stock/branch.aspx?no={ticker}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        "Referer": "https://histock.tw/",
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"  ⚠ HiStock branch 錯誤 ({ticker}): {e}")
        return []

    tables = re.findall(r"<table[^>]*>(.*?)</table>", html, re.S)
    target = next((t for t in tables if "券商名稱" in t), None)
    if not target:
        return []
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", target, re.S)
    result = []
    for r in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)
        vals = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        # 每列 10 欄：[賣方券商, 買, 賣, 賣超, 均價, 買方券商, 買, 賣, 買超, 均價]
        if len(vals) < 10 or vals[0] == "券商名稱":
            continue

        def n(s):
            s = s.replace(",", "").replace("--", "0").strip()
            try:
                return float(s) if s else 0.0
            except ValueError:
                return 0.0

        # 賣方（左）
        sell_broker = vals[0]
        if sell_broker and sell_broker != "-":
            result.append({
                "broker_name": sell_broker,
                "buy_lots":  n(vals[1]),
                "sell_lots": n(vals[2]),
                "net_lots":  n(vals[3]),   # 賣超（通常為負）
                "avg_price": n(vals[4]),
            })
        # 買方（右）
        buy_broker = vals[5]
        if buy_broker and buy_broker != "-":
            result.append({
                "broker_name": buy_broker,
                "buy_lots":  n(vals[6]),
                "sell_lots": n(vals[7]),
                "net_lots":  n(vals[8]),   # 買超
                "avg_price": n(vals[9]),
            })
    return result


def save_broker_to_db(rows: list[dict]):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO broker_flow
           (ticker, trade_date, broker_name, buy_lots, sell_lots, net_lots, avg_price, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r["ticker"], r["trade_date"], r["broker_name"],
          r.get("buy_lots", 0), r.get("sell_lots", 0),
          r.get("net_lots", 0), r.get("avg_price", 0), now)
         for r in rows],
    )
    conn.commit()
    conn.close()


def load_broker_from_db(tickers: list[str], start_date: str, end_date: str) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(tickers))
    rows = conn.execute(
        f"SELECT ticker, trade_date, broker_name, buy_lots, sell_lots, net_lots, avg_price "
        f"FROM broker_flow WHERE ticker IN ({placeholders}) "
        f"AND trade_date BETWEEN ? AND ?",
        (*tickers, start_date, end_date),
    ).fetchall()
    conn.close()
    return [
        {"ticker": r[0], "trade_date": r[1], "broker_name": r[2],
         "buy_lots": r[3], "sell_lots": r[4], "net_lots": r[5], "avg_price": r[6]}
        for r in rows
    ]


def fetch_broker_today(all_tickers: dict, today_iso: str, sleep_sec: float = 2.5) -> int:
    """批次抓 all_tickers 當日分點（寫進 DB）。sleep 間隔避免 HiStock 反爬。回傳筆數。"""
    new_rows = []
    for i, ticker in enumerate(all_tickers.keys(), 1):
        print(f"  [{i}/{len(all_tickers)}] 分點 {ticker} ...", end=" ", flush=True)
        rows = fetch_broker_histock(ticker)
        if rows:
            for r in rows:
                new_rows.append({"ticker": ticker, "trade_date": today_iso, **r})
            print(f"{len(rows)} 家")
        else:
            print("無資料")
        time.sleep(sleep_sec)
    save_broker_to_db(new_rows)
    return len(new_rows)


def load_prices_from_db(dates: list[str]) -> dict[tuple, float]:
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT ticker, trade_date, close FROM daily_price "
        f"WHERE trade_date IN ({placeholders})",
        dates,
    ).fetchall()
    conn.close()
    return {(r[0], r[1]): r[2] for r in rows}


def load_daily_ohlcv(
    ticker: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    query = (
        "SELECT ticker, trade_date, open, high, low, close, volume "
        "FROM daily_price WHERE ticker = ?"
    )
    params: list[str] = [ticker]
    if start_date:
        query += " AND trade_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND trade_date <= ?"
        params.append(end_date)
    query += " ORDER BY trade_date"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [
        {
            "ticker": r[0],
            "trade_date": r[1],
            "open": r[2],
            "high": r[3],
            "low": r[4],
            "close": r[5],
            "volume": r[6],
        }
        for r in rows
    ]


def save_prices_to_db(rows: list[dict]):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """
        INSERT INTO daily_price (
            ticker, trade_date, close, open, high, low, volume, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, trade_date) DO UPDATE SET
            close = excluded.close,
            open = COALESCE(excluded.open, daily_price.open),
            high = COALESCE(excluded.high, daily_price.high),
            low = COALESCE(excluded.low, daily_price.low),
            volume = COALESCE(excluded.volume, daily_price.volume),
            updated_at = excluded.updated_at
        """,
        [
            (
                r["ticker"],
                r["trade_date"],
                r.get("close"),
                r.get("open"),
                r.get("high"),
                r.get("low"),
                r.get("volume"),
                now,
            )
            for r in rows
        ],
    )
    conn.commit()
    conn.close()


def ensure_prices(dates: list[str], all_tickers: dict, no_fetch: bool = False) -> dict[tuple, float]:
    """
    確保指定日期的收盤價在 DB。缺則抓 MI_INDEX / STOCK_DAY_ALL。
    回傳 {(ticker, date): close}
    """
    cached = load_prices_from_db(dates)
    # 按 (date) 判斷是否該日已有任何資料（有資料 = 該日已抓過）
    dates_with_data = {d for _, d in cached.keys()}
    missing_dates = [d for d in dates if d not in dates_with_data]

    if missing_dates and not no_fetch:
        print(f"  需補抓 {len(missing_dates)} 個交易日收盤價...")
        new_rows = []
        for dt in missing_dates:
            dt_compact = dt.replace("-", "")
            print(f"  收盤價 {dt} ...", end=" ", flush=True)
            prices = fetch_close_prices(dt_compact, all_tickers)
            time.sleep(0.4)
            # 補抓 TPEx（上櫃）
            tpex_prices = fetch_tpex_close_prices(dt_compact, all_tickers)
            # TPEx 優先（若兩邊都有；通常互斥）
            merged = {**prices, **tpex_prices}
            if merged:
                for ticker, close in merged.items():
                    new_rows.append({"ticker": ticker, "trade_date": dt, "close": close})
                print(f"取得 {len(merged)} 筆（TWSE {len(prices)} + TPEx {len(tpex_prices)}）")
            else:
                print("無資料")
            time.sleep(0.4)
        save_prices_to_db(new_rows)
        for r in new_rows:
            cached[(r["ticker"], r["trade_date"])] = r["close"]
    return cached


# ── 日期工具 ──────────────────────────────────────────────────
def trading_dates_in_range(start: date, end: date) -> list[str]:
    """
    回傳 [start, end] 內台股實際開盤日（YYYY-MM-DD）。
    優先查 trading_calendar DB（由 ensure_calendar 填充）；
    若 DB 無資料（首次或未補抓），fallback 到跳週末邏輯。
    """
    conn = sqlite3.connect(DB_PATH)
    # 確認 trading_calendar 表存在
    tbl_exists = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name='trading_calendar'"
    ).fetchone()[0]

    if tbl_exists:
        start_str = start.strftime("%Y-%m-%d")
        end_str   = end.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT trade_date FROM trading_calendar WHERE trade_date BETWEEN ? AND ? ORDER BY trade_date",
            (start_str, end_str),
        ).fetchall()
        conn.close()
        if rows:
            return [r[0] for r in rows]
    else:
        conn.close()

    # fallback：跳週末
    result = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            result.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=1)
    return result


def split_into_periods(dates: list[str], split: str) -> list[tuple[str, list[str]]]:
    """
    將日期清單切成子區間。
    split: 'none' | 'week' | 'month'
    回傳: [(label, [dates]), ...]
    """
    if split == "none" or not dates:
        label = f"{dates[0]} ~ {dates[-1]}" if dates else "全期"
        return [(label, dates)]

    if split == "day":
        return [(d, [d]) for d in dates]

    if split == "month":
        key_fn = lambda d: d[:7]  # YYYY-MM
    else:  # week
        key_fn = lambda d: (
            datetime.strptime(d, "%Y-%m-%d").isocalendar()[:2]
        )

    groups = []
    for k, g in groupby(dates, key=key_fn):
        day_list = list(g)
        if split == "month":
            label = k  # "2026-03"
        else:
            y, w = k
            label = f"{y}-W{w:02d}"
        groups.append((label, day_list))
    return groups


# ── DB 讀取 / 寫入 ─────────────────────────────────────────────
def load_from_db(dates: list[str]) -> dict[tuple, dict]:
    """
    讀 DB 中已有的資料。
    回傳: {(ticker, trade_date): {foreign, invest, dealer, total,
                                 foreign_value, invest_value, dealer_value, total_value}}
    """
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT ticker, trade_date, foreign_net, invest_net, dealer_net, total_net, "
        f"       foreign_value, invest_value, dealer_value, total_value "
        f"FROM institutional_flow WHERE trade_date IN ({placeholders})",
        dates,
    ).fetchall()
    conn.close()
    return {
        (r[0], r[1]): {
            "foreign": r[2], "invest": r[3], "dealer": r[4], "total": r[5],
            "foreign_value": r[6] or 0.0, "invest_value": r[7] or 0.0,
            "dealer_value":  r[8] or 0.0, "total_value":  r[9] or 0.0,
        }
        for r in rows
    }


def save_to_db(rows: list[dict]):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()
    conn.executemany(
        """INSERT OR REPLACE INTO institutional_flow
           (ticker, trade_date, foreign_net, invest_net, dealer_net, total_net,
            foreign_value, invest_value, dealer_value, total_value, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(r["ticker"], r["trade_date"],
          r["foreign"], r["invest"], r["dealer"], r["total"],
          r.get("foreign_value", 0.0), r.get("invest_value", 0.0),
          r.get("dealer_value",  0.0), r.get("total_value",  0.0),
          now)
         for r in rows],
    )
    conn.commit()
    conn.close()


# ── 資料抓取（含快取邏輯）────────────────────────────────────
def ensure_data(
    dates: list[str],
    no_fetch: bool,
    all_tickers=None,
) -> dict[tuple, dict]:
    """
    從 DB 取已有資料；缺漏的日期從 TWSE 補抓（除非 --no-fetch）。
    all_tickers: {ticker: name}，None 時用 load_universe() 預設值。
    """
    if all_tickers is None:
        _, all_tickers, _, _ = load_universe()

    cached = load_from_db(dates)
    cached_dates = set(d for _, d in cached.keys())
    missing = [d for d in dates if d not in cached_dates]

    fetched_count = 0
    if missing and not no_fetch:
        print(f"  需補抓 {len(missing)} 個交易日...")
        # 先抓收盤價（整批），供 value 計算用
        price_map = ensure_prices(missing, all_tickers, no_fetch=False)

        new_rows = []
        for dt in missing:
            dt_compact = dt.replace("-", "")
            print(f"  抓取 T86 {dt} ...", end=" ", flush=True)
            raw = fetch_t86(dt_compact, all_tickers)
            time.sleep(0.4)
            tpex = fetch_tpex_institutional(dt_compact, all_tickers)
            # TPEx 補位（TWSE/TPEx 互斥，但以 TPEx 覆寫若同 ticker）
            raw = {**raw, **tpex}
            if raw:
                for ticker, vals in raw.items():
                    close = price_map.get((ticker, dt), 0.0)
                    # 金額（千元）= 股數 × 收盤價 / 1000
                    fv = vals["foreign"] * close / 1000
                    iv = vals["invest"]  * close / 1000
                    dv = vals["dealer"]  * close / 1000
                    tv = vals["total"]   * close / 1000
                    new_rows.append({
                        "ticker": ticker, "trade_date": dt,
                        **vals,
                        "foreign_value": fv, "invest_value": iv,
                        "dealer_value":  dv, "total_value":  tv,
                    })
                n_tpex = len(tpex)
                n_twse = len(raw) - n_tpex
                print(f"取得 {len(raw)} 筆（TWSE {n_twse} + TPEx {n_tpex}）")
            else:
                print("無資料（可能假日）")
            time.sleep(0.4)

        if new_rows:
            save_to_db(new_rows)
            fetched_count = len(new_rows)
            for r in new_rows:
                cached[(r["ticker"], r["trade_date"])] = {
                    "foreign": r["foreign"],
                    "invest":  r["invest"],
                    "dealer":  r["dealer"],
                    "total":   r["total"],
                    "foreign_value": r["foreign_value"],
                    "invest_value":  r["invest_value"],
                    "dealer_value":  r["dealer_value"],
                    "total_value":   r["total_value"],
                }

    elif missing and no_fetch:
        print(f"  ⚠ --no-fetch 模式，略過 {len(missing)} 個缺漏日期")

    return cached, fetched_count


# ── 彙整計算 ──────────────────────────────────────────────────
def aggregate_by_category(
    data: dict[tuple, dict],
    dates: list[str],
    categories: dict,
    ticker_to_cat: dict,
) -> dict[str, dict]:
    """
    按類股加總指定日期範圍的買賣超（股）。
    回傳: {category: {foreign, invest, dealer, total, stocks: {ticker: total}}}
    """
    result = {cat: {"foreign": 0.0, "invest": 0.0, "dealer": 0.0, "total": 0.0,
                    "foreign_value": 0.0, "invest_value": 0.0,
                    "dealer_value":  0.0, "total_value":  0.0,
                    "stocks": {}} for cat in categories}

    date_set = set(dates)
    for (ticker, trade_date), vals in data.items():
        if trade_date not in date_set:
            continue
        cat = ticker_to_cat.get(ticker)
        if not cat:
            continue
        result[cat]["foreign"] += vals["foreign"]
        result[cat]["invest"]  += vals["invest"]
        result[cat]["dealer"]  += vals["dealer"]
        result[cat]["total"]   += vals["total"]
        result[cat]["foreign_value"] += vals.get("foreign_value", 0.0)
        result[cat]["invest_value"]  += vals.get("invest_value",  0.0)
        result[cat]["dealer_value"]  += vals.get("dealer_value",  0.0)
        result[cat]["total_value"]   += vals.get("total_value",   0.0)
        # 個股合計：同時累加股數與金額（千元），下游依單位選擇
        prev = result[cat]["stocks"].get(ticker)
        if prev is None:
            result[cat]["stocks"][ticker] = {
                "shares": vals["total"],
                "value":  vals.get("total_value", 0.0),
            }
        else:
            prev["shares"] += vals["total"]
            prev["value"]  += vals.get("total_value", 0.0)

    return result


# ── JSON 輸出 ─────────────────────────────────────────────────
def export_json(
    period_results: list[tuple[str, list[str], dict]],
    meta: dict,
    out_path: Path,
):
    """
    輸出標準 JSON 格式供 Dashboard 使用。
    period_results: [(label, dates, cat_agg), ...]
    """
    categories = list(meta["categories"].keys())
    periods_out = []
    for label, dates, cat_agg in period_results:
        period_data = {}
        for cat in categories:
            vals = cat_agg.get(cat, {"foreign": 0, "invest": 0, "dealer": 0, "total": 0})
            period_data[cat] = {
                "foreign": vals["foreign"],
                "invest":  vals["invest"],
                "dealer":  vals["dealer"],
                "total":   vals["total"],
            }
        periods_out.append({
            "label":      label,
            "date_range": [dates[0], dates[-1]] if dates else [],
            "data":       period_data,
        })

    output = {
        "meta": {
            "start":       meta["start"],
            "end":         meta["end"],
            "split":       meta["split"],
            "tier":        meta["tier"],
            "tier_label":  meta["tier_label"],
            "generated_at": datetime.now().isoformat(),
        },
        "categories": categories,
        "periods":    periods_out,
    }

    DATA_DIR.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  💾 JSON 已寫入：{out_path}")
    return output


# ── Markdown 報告 ─────────────────────────────────────────────
def fmt_k(val: float) -> str:
    """股 → 帶正負號的字串（四捨五入到整數）"""
    return f"{val:+,.0f}"


def rotation_arrow(cur: float, prev) -> str:
    """相對上期，流入增加用 ▲，減少用 ▼"""
    if prev is None:
        return ""
    diff = cur - prev
    if diff > 1000:
        return " ▲"
    elif diff < -1000:
        return " ▼"
    return ""


def build_report(
    period_results: list[tuple[str, list[str], dict]],
    start: str,
    end: str,
    split: str,
    categories: dict,
    all_tickers: dict,
    tier_label: str,
) -> str:
    lines = []
    lines.append("# 主力資金類股輪動報告")
    lines.append(
        f"\n> 分析區間：{start} ～ {end}　｜　分組：{split}　｜　"
        f"標的範圍：{tier_label}　｜　單位：股（TWSE T86 原始值）"
    )
    lines.append(f"\n產生時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n")

    for i, (label, dates, cat_agg) in enumerate(period_results):
        prev_agg = period_results[i - 1][2] if i > 0 else None

        lines.append(f"\n## {label}\n")
        lines.append("| 類股 | 外資（股） | 投信 | 自營 | **合計** | 方向 |")
        lines.append("|------|------------:|-----:|-----:|---------:|:----:|")

        sorted_cats = sorted(cat_agg.items(), key=lambda x: x[1]["total"], reverse=True)
        for cat, vals in sorted_cats:
            prev_total = prev_agg[cat]["total"] if prev_agg else None
            arrow = rotation_arrow(vals["total"], prev_total)
            lines.append(
                f"| {cat} "
                f"| {fmt_k(vals['foreign'])} "
                f"| {fmt_k(vals['invest'])} "
                f"| {fmt_k(vals['dealer'])} "
                f"| **{fmt_k(vals['total'])}** "
                f"| {arrow or '—'} |"
            )

        lines.append("\n<details><summary>個股明細</summary>\n")
        lines.append("| 類股 | 代碼 | 公司 | 合計（股） |")
        lines.append("|------|------|------|------------:|")
        for cat, vals in sorted_cats:
            for ticker, sdat in sorted(vals["stocks"].items(), key=lambda x: x[1]["shares"], reverse=True):
                total = sdat["shares"]
                name = all_tickers.get(ticker, ticker)
                lines.append(f"| {cat} | {ticker} | {name} | {fmt_k(total)} |")
        lines.append("\n</details>")

    if len(period_results) >= 2:
        lines.append("\n---\n\n## 輪動摘要\n")
        first_agg = period_results[0][2]
        last_agg  = period_results[-1][2]

        gainers = []
        losers  = []
        for cat in categories:
            diff = last_agg[cat]["total"] - first_agg[cat]["total"]
            if diff > 0:
                gainers.append((cat, diff))
            elif diff < 0:
                losers.append((cat, diff))

        gainers.sort(key=lambda x: x[1], reverse=True)
        losers.sort(key=lambda x: x[1])

        if gainers:
            lines.append("**資金流入（相較首期）**")
            for cat, diff in gainers:
                lines.append(f"- {cat}：{fmt_k(diff)} 股")

        if losers:
            lines.append("\n**資金流出（相較首期）**")
            for cat, diff in losers:
                lines.append(f"- {cat}：{fmt_k(diff)} 股")

        if gainers and losers:
            lines.append(
                f"\n> **資金從** {losers[0][0]} **移轉至** {gainers[0][0]}"
            )

    lines.append("\n---\n\n*資料來源：臺灣證交所 T86 三大法人買賣超*")
    return "\n".join(lines)


# ── 主程式 ────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="主力資金類股輪動分析")
    parser.add_argument("--start",    required=True, help="開始日期 YYYY-MM-DD")
    parser.add_argument("--end",      required=True, help="結束日期 YYYY-MM-DD")
    parser.add_argument("--split",    choices=["none", "day", "week", "month"],
                        default="none", help="時間分組（預設 none）")
    parser.add_argument("--tier",     choices=["ai_supply_chain", "broad_themes", "all"],
                        default="ai_supply_chain", help="標的層級（預設 ai_supply_chain）")
    parser.add_argument("--no-fetch", action="store_true",
                        help="只用 DB 快取，不補抓 TWSE")
    parser.add_argument("--no-save",  action="store_true",
                        help="不寫報告到 reports/（只印到終端）")
    parser.add_argument("--json",     action="store_true",
                        help="同時輸出 data/sector_flow_{start}_{end}.json")
    parser.add_argument("--include-margin", action="store_true",
                        help="同步抓取融資融券資料（MI_MARGN / TPEx margin_bal）")
    parser.add_argument("--fetch-broker-today", action="store_true",
                        help="抓今日券商分點（HiStock branch.aspx，每股 sleep ~2.5s）")
    parser.add_argument("--include-qfii", action="store_true",
                        help="同步抓取外資持股比例（MI_QFIIS）")
    parser.add_argument("--include-futures", action="store_true",
                        help="同步抓取期貨未平倉（TAIFEX TXF/EXF）")
    parser.add_argument("--include-tdcc", action="store_true",
                        help="同步抓取 TDCC 集保分級（週資料）")
    args = parser.parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d").date()
    end_dt   = datetime.strptime(args.end,   "%Y-%m-%d").date()

    # 載入標的分類
    categories, all_tickers, ticker_to_cat, tier_label = load_universe(args.tier)
    print(f"\n📊 類股輪動分析：{args.start} ～ {args.end}（分組：{args.split}，範圍：{tier_label}）")
    print(f"   類股數：{len(categories)}，標的數：{len(all_tickers)}")

    init_db()

    # 1. 取得所有交易日
    all_dates = trading_dates_in_range(start_dt, end_dt)
    if not all_dates:
        print("❌ 無有效交易日")
        return

    print(f"   共 {len(all_dates)} 個交易日")

    # 2. 確保資料到位
    data, _ = ensure_data(all_dates, args.no_fetch, all_tickers)
    if args.include_margin:
        ensure_margin_data(all_dates, all_tickers, args.no_fetch)
    if args.include_qfii:
        ensure_qfii_data(all_dates, all_tickers, args.no_fetch)
    if args.include_futures:
        ensure_futures_data(all_dates, ["TXF", "EXF"], args.no_fetch)
    if args.include_tdcc:
        ensure_tdcc_data(all_tickers, args.no_fetch)
    if args.fetch_broker_today:
        today_iso = date.today().strftime("%Y-%m-%d")
        print(f"\n🏦 抓取券商分點（{today_iso}，{len(all_tickers)} 檔，每檔 sleep 2.5s，預估 {len(all_tickers)*2.5/60:.1f} 分鐘）")
        n = fetch_broker_today(all_tickers, today_iso, sleep_sec=2.5)
        print(f"   共寫入 {n} 筆分點資料")

    # 3. 切分期間
    date_groups = split_into_periods(all_dates, args.split)

    # 4. 各期彙整（回傳 label, dates, cat_agg）
    period_results = []
    for label, dates in date_groups:
        agg = aggregate_by_category(data, dates, categories, ticker_to_cat)
        period_results.append((label, dates, agg))

    # 5. 產生 Markdown 報告
    report_md = build_report(
        period_results, args.start, args.end, args.split,
        categories, all_tickers, tier_label,
    )

    if not args.no_save:
        sector_flow_dir = REPORTS_DIR / "sector_flow"
        sector_flow_dir.mkdir(parents=True, exist_ok=True)
        fn = f"sector_flow_{args.start}_{args.end}.md"
        out_path = sector_flow_dir / fn
        out_path.write_text(report_md, encoding="utf-8")
        print(f"\n✅ 報告已寫入：{out_path}")

        # 印摘要（全期合計）
        full_agg = aggregate_by_category(data, all_dates, categories, ticker_to_cat)
        print(f"\n{'類股':<18} {'外資（股）':>14} {'投信':>12} {'自營':>12} {'合計':>14}")
        print("-" * 74)
        for cat, vals in sorted(full_agg.items(), key=lambda x: x[1]["total"], reverse=True):
            print(
                f"{cat:<18} {fmt_k(vals['foreign']):>12} "
                f"{fmt_k(vals['invest']):>10} {fmt_k(vals['dealer']):>10} "
                f"{fmt_k(vals['total']):>12}"
            )
    else:
        print(report_md)

    # 6. 輸出 JSON（可選）
    if args.json:
        json_name = f"sector_flow_{args.start}_{args.end}.json"
        json_path = DATA_DIR / json_name
        export_json(
            period_results,
            meta={
                "start":      args.start,
                "end":        args.end,
                "split":      args.split,
                "tier":       args.tier,
                "tier_label": tier_label,
                "categories": categories,
            },
            out_path=json_path,
        )


if __name__ == "__main__":
    main()
