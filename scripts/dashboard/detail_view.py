from __future__ import annotations

import base64
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.helpers import GRID_COLOR, LEGEND_BG, NEG_COLOR, POS_COLOR
from fetch_news import ensure_news_cache, fetch_and_store, load_news
from fetch_quote import fetch_quote
from sector_flow import DB_PATH, load_daily_ohlcv, load_from_db, load_universe


TIMEFRAME_OPTIONS = ["5m", "10m", "30m", "40m", "1H", "4H", "1D", "1W"]
INTRADAY_TFS = {"5m", "10m", "30m", "40m", "1H", "4H"}
DAILY_TFS = {"1D", "1W"}

# 日 / 週用的顯示區間（依 plan §2.2）
DISPLAY_RANGE_OPTIONS_DAILY = ["最近 1 週", "最近 1 月", "最近 3 月", "最近 6 月", "最近 1 年", "全部"]
# 日內用的顯示區間
DISPLAY_RANGE_OPTIONS_INTRADAY = ["最近 1 日", "最近 5 日", "最近 10 日", "最近 20 日", "最近 1 月", "全部"]

DEFAULT_RANGE_BY_TF = {
    "5m": "最近 5 日",
    "10m": "最近 10 日",
    "30m": "最近 20 日",
    "40m": "最近 20 日",
    "1H": "最近 1 月",
    "4H": "最近 1 月",
    "1D": "最近 6 月",
    "1W": "最近 1 年",
}
DISPLAY_RANGE_DAYS = {
    "最近 1 日": 1,
    "最近 5 日": 5,
    "最近 10 日": 10,
    "最近 20 日": 20,
    "最近 1 週": 7,
    "最近 1 月": 31,
    "最近 3 月": 92,
    "最近 6 月": 183,
    "最近 1 年": 366,
}

# pandas resample rule + offset (對齊 09:00)
INTRADAY_RESAMPLE_RULE = {
    "5m": None,           # 原生
    "10m": ("10min", None),
    "30m": ("30min", None),
    "40m": ("40min", "9h"),  # 從 09:00 對齊
    "1H": ("60min", None),
    "4H": ("240min", "9h"),
}
MA_COLORS = {"MA5": "#60a5fa", "MA20": "#8b5cf6", "MA60": "#f59e0b"}
INSTITUTION_COLORS = {
    "foreign_net": "#2563eb",
    "invest_net": "#8b5cf6",
    "dealer_net": "#f97316",
    "total_net": "#0f766e",
}
REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = REPO_ROOT / "reports" / "stock_snapshot"
SNAPSHOT_DEFAULT_INDICATORS = ["MA5", "MA20", "MA60"]
PEER_COMPARE_WINDOWS = [5, 20, 60]
FUTURES_CONTEXT_TICKERS = {
    "2330", "2454", "2303", "2308", "2345", "2356", "2382",
    "2603", "2609", "2615", "2881", "2882", "2886", "3017", "3324",
}
FUTURES_CONTRACT_LABELS = {"TXF": "台指期", "EXF": "電子期"}
FUTURES_ROLE_LABELS = {"foreign": "外資", "invest": "投信", "dealer": "自營商"}


def render_stock_detail_tab(ctx) -> None:
    categories, companies, ticker_to_cat, _ = _load_all_universe()

    st.caption("提供搜尋、5m–1W K 線與量能、P2 籌碼面板、P3 即時五檔、P4 新聞面板、P6 延伸資訊。日內資料來源：yfinance（5m 原生 + pandas resample）。")
    ticker, tf = _render_search_bar(companies)
    if not ticker:
        st.info("輸入股票代號後按下查詢，即可載入個股日 K / 週 K 與量能。")
        return

    name = companies.get(ticker, ticker)
    category = ticker_to_cat.get(ticker, "未收錄於 universe")
    st.subheader(f"{ticker} {name}")
    st.caption(f"類股：{category}　｜　週期：{tf}")
    _render_quote_book(ticker)
    st.divider()
    _render_kline_volume(ticker, tf)
    st.divider()
    _render_chip_panel(ticker)
    st.divider()
    _render_news_feed(ticker, name)
    st.divider()
    _render_extras(ticker, name, category, categories, companies, tf)


def _render_search_bar(companies: dict[str, str]) -> tuple[str | None, str]:
    stored = st.session_state.get("detail_ticker", "")
    if stored and "detail_ticker_input" not in st.session_state:
        st.session_state["detail_ticker_input"] = stored
    col1, col2, col3 = st.columns([2, 1, 3])
    ticker_input = col1.text_input(
        "股票代號",
        key="detail_ticker_input",
        placeholder="例：2330",
    ).strip()
    submit = col2.button("🔍 查詢", type="primary", use_container_width=True)
    tf = col3.radio(
        "K 線週期",
        TIMEFRAME_OPTIONS,
        horizontal=True,
        key="detail_tf",
        index=0,
    )

    if submit:
        if not ticker_input:
            st.warning("請先輸入股票代號。")
            st.session_state.pop("detail_ticker", None)
            return None, tf
        if not _ticker_exists(ticker_input, companies):
            st.error("找不到此代號。請確認是否存在於 `research/stock_universe.json` 或 `daily_price`。")
            return None, tf
        st.session_state["detail_ticker"] = ticker_input

    ticker = st.session_state.get("detail_ticker", "").strip()
    if not ticker:
        return None, tf
    if not _ticker_exists(ticker, companies):
        st.error("目前儲存的查詢代號已無對應資料。")
        return None, tf
    return ticker, tf


def _render_kline_volume(ticker: str, tf: str) -> None:
    is_intraday = tf in INTRADAY_TFS
    full_df = _load_ohlcv(ticker, tf)
    if full_df.empty:
        if is_intraday:
            st.warning(
                "尚無此週期的日內資料。請先執行 "
                "`python3 scripts/fetch_intraday.py --ticker " + ticker + " --period 5d` 抓取 5m 資料。"
            )
            if st.button("📥 立刻抓取 5m（5 日）", key=f"intraday_fetch_{ticker}"):
                _fetch_intraday_now(ticker)
                _load_ohlcv.clear()
                st.rerun()
        else:
            st.warning("找不到這檔股票的價格資料。請先執行 `scripts/fetch_ohlcv.py` 回填日 OHLCV。")
        return

    if full_df[["open", "high", "low", "close"]].dropna().empty:
        st.warning("OHLCV 欄位皆為空。請先回填資料。")
        return

    range_options = (
        DISPLAY_RANGE_OPTIONS_INTRADAY if is_intraday else DISPLAY_RANGE_OPTIONS_DAILY
    )
    default_range = DEFAULT_RANGE_BY_TF[tf]
    range_index = range_options.index(default_range) if default_range in range_options else 0

    control_col1, control_col2 = st.columns([3, 2])
    range_label = control_col1.radio(
        "顯示區間",
        range_options,
        horizontal=True,
        key=f"detail_range_{ticker}_{tf}",
        index=range_index,
    )
    ma_choices = control_col2.multiselect(
        "均線 / 指標",
        ["MA5", "MA20", "MA60", "BBands"],
        default=["MA5", "MA20", "MA60"],
        key=f"detail_indicators_{ticker}_{tf}",
    )

    chart_df = _enrich_price_indicators(full_df)
    display_df = _apply_display_range(chart_df, range_label)
    display_df = display_df.dropna(subset=["open", "high", "low", "close"]).copy()
    if display_df.empty:
        st.warning("這個區間沒有可顯示的 OHLCV。")
        return

    latest = display_df.iloc[-1]
    prev_close = display_df.iloc[-2]["close"] if len(display_df) >= 2 else None
    delta = latest["close"] - prev_close if prev_close is not None else None
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("收盤", f"{latest['close']:,.2f}", None if delta is None else f"{delta:+.2f}")
    c2.metric("開盤", f"{latest['open']:,.2f}")
    c3.metric("高 / 低", f"{latest['high']:,.2f} / {latest['low']:,.2f}")
    c4.metric("成交量（張）", f"{latest['volume']:,.0f}" if pd.notna(latest["volume"]) else "—")

    fig = _build_price_chart_figure(display_df, tf, ma_choices)
    st.plotly_chart(fig, use_container_width=True)

def _render_chip_panel(ticker: str) -> None:
    snapshot = _fetch_chip_snapshot(ticker)
    if not any(
        not snapshot[key].empty
        for key in ("institutional", "margin", "broker_buy", "broker_sell", "tdcc_latest")
    ):
        st.info("這檔股票目前沒有足夠的籌碼資料。P2 面板只會讀現有資料表，不會自動補抓。")
        return

    st.subheader("當日籌碼")
    top_left, top_right = st.columns([1.55, 1.0])
    with top_left:
        _render_institutional_panel(snapshot["institutional"])
    with top_right:
        _render_margin_panel(snapshot["margin"])

    _render_broker_panel(snapshot["broker_buy"], snapshot["broker_sell"], snapshot["broker_date"])
    _render_tdcc_panel(snapshot["tdcc_latest"], snapshot["tdcc_prev"])


def _render_institutional_panel(df: pd.DataFrame) -> None:
    st.markdown("#### B1 三大法人")
    if df.empty:
        st.caption("institutional_flow 尚無資料。")
        return

    latest = df.iloc[-1]
    st.caption(f"最新交易日：{latest['trade_date'].strftime('%Y-%m-%d')}")
    metrics = st.columns(4)
    metric_defs = [
        ("外資", "foreign_net", "foreign_value"),
        ("投信", "invest_net", "invest_value"),
        ("自營", "dealer_net", "dealer_value"),
        ("合計", "total_net", "total_value"),
    ]
    for col, (label, net_key, value_key) in zip(metrics, metric_defs):
        col.metric(label, _format_signed_lots(latest[net_key]))
        col.caption(f"約 {_format_value_oku(latest[value_key])}")

    chart_df = df.copy()
    fig = go.Figure()
    for key, trace_name in (
        ("foreign_net", "外資"),
        ("invest_net", "投信"),
        ("dealer_net", "自營"),
        ("total_net", "合計"),
    ):
        fig.add_trace(
            go.Bar(
                x=chart_df["trade_date"],
                y=chart_df[key] / 1000.0,
                name=trace_name,
                marker_color=INSTITUTION_COLORS[key],
                hovertemplate="%{x|%Y-%m-%d}<br>" + trace_name + " %{y:,.0f} 張<extra></extra>",
            )
        )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#f1f5f9",
        plot_bgcolor="#f8fafc",
        margin=dict(t=24, b=18, l=12, r=12),
        height=260,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor=LEGEND_BG),
        font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif", color="#1e293b"),
        barmode="group",
    )
    fig.update_yaxes(title_text="張", gridcolor=GRID_COLOR, zerolinecolor=GRID_COLOR)
    fig.update_xaxes(gridcolor=GRID_COLOR)
    st.plotly_chart(fig, use_container_width=True)


def _render_margin_panel(df: pd.DataFrame) -> None:
    st.markdown("#### B2 融資融券")
    if df.empty:
        st.caption("margin_flow / margin_data 尚無資料。")
        return

    latest = df.iloc[-1]
    st.caption(f"最新交易日：{latest['trade_date'].strftime('%Y-%m-%d')}")
    c1, c2 = st.columns(2)
    c1.metric("融資餘額", f"{latest['margin_balance']:,.0f} 張", _format_delta_signed(latest["margin_change"], "張"))
    c2.metric("融券餘額", f"{latest['short_balance']:,.0f} 張", _format_delta_signed(latest["short_change"], "張"))
    ratio_text = "—" if pd.isna(latest["margin_ratio"]) else f"{latest['margin_ratio']:,.2f}"
    st.caption(f"資券比：{ratio_text}")

    history = df.tail(10).copy()
    if history.empty:
        return
    history["label"] = history["trade_date"].dt.strftime("%m-%d")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=history["label"],
            y=history["margin_balance"],
            mode="lines+markers",
            name="融資餘額",
            line=dict(color=POS_COLOR, width=2),
            hovertemplate="%{x}<br>融資餘額 %{y:,.0f} 張<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=history["label"],
            y=history["short_balance"],
            mode="lines+markers",
            name="融券餘額",
            line=dict(color=NEG_COLOR, width=2),
            hovertemplate="%{x}<br>融券餘額 %{y:,.0f} 張<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#f1f5f9",
        plot_bgcolor="#f8fafc",
        margin=dict(t=24, b=18, l=12, r=12),
        height=260,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor=LEGEND_BG),
        font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif", color="#1e293b"),
    )
    fig.update_yaxes(title_text="張", gridcolor=GRID_COLOR)
    fig.update_xaxes(gridcolor=GRID_COLOR)
    st.plotly_chart(fig, use_container_width=True)


def _render_broker_panel(buy_df: pd.DataFrame, sell_df: pd.DataFrame, broker_date: str | None) -> None:
    st.markdown("#### B3 分點進出 Top 15")
    if buy_df.empty and sell_df.empty:
        st.caption("broker_flow 尚無資料。")
        return

    if broker_date:
        st.caption(f"最新交易日：{broker_date}")
    left, right = st.columns(2)
    with left:
        st.caption("買超 Top 15")
        _render_broker_table(buy_df, pct_col="buy_pct")
    with right:
        st.caption("賣超 Top 15")
        _render_broker_table(sell_df, pct_col="sell_pct")


def _render_broker_table(df: pd.DataFrame, pct_col: str) -> None:
    if df.empty:
        st.caption("無資料")
        return

    display_df = df.copy()
    display_df = display_df.rename(
        columns={
            "broker_name": "券商",
            "buy_lots": "買張",
            "sell_lots": "賣張",
            "net_lots": "淨張",
            "avg_price": "均價",
        }
    )
    if pct_col in display_df:
        display_df["占成交%"] = display_df[pct_col].map(lambda v: "—" if pd.isna(v) else f"{v:.2f}%")
    for col in ("買張", "賣張", "淨張"):
        display_df[col] = display_df[col].map(lambda v: f"{v:,.0f}")
    display_df["均價"] = display_df["均價"].map(lambda v: "—" if pd.isna(v) or v <= 0 else f"{v:,.2f}")
    st.dataframe(
        display_df[["券商", "買張", "賣張", "淨張", "均價", "占成交%"]],
        hide_index=True,
        width="stretch",
    )


def _render_tdcc_panel(latest: pd.DataFrame, previous: pd.DataFrame) -> None:
    st.markdown("#### B4 集保分布")
    if latest.empty:
        st.caption("shareholder_distribution 尚無資料。")
        return

    latest_row = latest.iloc[0]
    st.caption(f"最新資料日：{latest_row['data_date']}")
    metrics = st.columns(3)
    metric_defs = [
        ("400 張以上", "pct_over_400"),
        ("1000 張以上", "pct_over_1000"),
        ("散戶 < 10 張", "pct_retail_lt10"),
    ]
    for col, (label, key) in zip(metrics, metric_defs):
        delta_text = None
        if not previous.empty:
            delta = latest_row[key] - previous.iloc[0][key]
            delta_text = f"{delta:+.2f} pct"
        col.metric(label, f"{latest_row[key]:.2f}%", delta_text)

    if not previous.empty:
        st.caption(f"對比前次資料日：{previous.iloc[0]['data_date']}")
    else:
        st.caption("目前只有最新一筆集保快照，尚無法比較前次變化。")


@st.cache_data(ttl=600)
def _fetch_chip_snapshot(ticker: str) -> dict[str, pd.DataFrame | str | None]:
    conn = sqlite3.connect(DB_PATH)
    try:
        institutional = pd.read_sql_query(
            """
            SELECT trade_date, foreign_net, invest_net, dealer_net, total_net,
                   foreign_value, invest_value, dealer_value, total_value
            FROM institutional_flow
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT 5
            """,
            conn,
            params=(ticker,),
        )
        institutional = _normalize_date_df(institutional, "trade_date")
        if not institutional.empty:
            institutional = institutional.sort_values("trade_date").reset_index(drop=True)

        margin = _load_margin_snapshot(conn, ticker)
        broker_buy, broker_sell, broker_date = _load_broker_snapshot(conn, ticker)
        tdcc_latest, tdcc_prev = _load_tdcc_snapshot(conn, ticker)
    finally:
        conn.close()

    return {
        "institutional": institutional,
        "margin": margin,
        "broker_buy": broker_buy,
        "broker_sell": broker_sell,
        "broker_date": broker_date,
        "tdcc_latest": tdcc_latest,
        "tdcc_prev": tdcc_prev,
    }


def _load_margin_snapshot(conn: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    if _table_has_rows(conn, "margin_flow", ticker, "trade_date"):
        df = pd.read_sql_query(
            """
            SELECT
                trade_date,
                margin_balance,
                (margin_balance - margin_prev) AS margin_change,
                short_balance,
                (short_balance - short_prev) AS short_change,
                CASE
                    WHEN short_balance IS NULL OR short_balance = 0 THEN NULL
                    ELSE margin_balance * 1.0 / short_balance
                END AS margin_ratio
            FROM margin_flow
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT 20
            """,
            conn,
            params=(ticker,),
        )
        df = _normalize_date_df(df, "trade_date")
        return df.sort_values("trade_date").reset_index(drop=True)

    if _table_has_rows(conn, "margin_data", ticker, "trade_date"):
        df = pd.read_sql_query(
            """
            SELECT trade_date, margin_balance, margin_change, short_balance, short_change, margin_ratio
            FROM margin_data
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT 20
            """,
            conn,
            params=(ticker,),
        )
        df = _normalize_date_df(df, "trade_date")
        return df.sort_values("trade_date").reset_index(drop=True)

    return pd.DataFrame()


def _load_broker_snapshot(
    conn: sqlite3.Connection,
    ticker: str,
) -> tuple[pd.DataFrame, pd.DataFrame, str | None]:
    if not _table_exists(conn, "broker_flow"):
        return pd.DataFrame(), pd.DataFrame(), None

    row = conn.execute(
        "SELECT MAX(trade_date) FROM broker_flow WHERE ticker = ?",
        (ticker,),
    ).fetchone()
    broker_date = row[0] if row and row[0] else None
    if not broker_date:
        return pd.DataFrame(), pd.DataFrame(), None

    buy_df = pd.read_sql_query(
        """
        SELECT
            bf.broker_name,
            bf.buy_lots,
            bf.sell_lots,
            bf.net_lots,
            bf.avg_price,
            CASE
                WHEN dp.volume IS NULL OR dp.volume = 0 THEN NULL
                ELSE bf.buy_lots * 100.0 / dp.volume
            END AS buy_pct
        FROM broker_flow bf
        LEFT JOIN daily_price dp
          ON dp.ticker = bf.ticker AND dp.trade_date = bf.trade_date
        WHERE bf.ticker = ? AND bf.trade_date = ? AND bf.net_lots > 0
        ORDER BY bf.net_lots DESC
        LIMIT 15
        """,
        conn,
        params=(ticker, broker_date),
    )
    sell_df = pd.read_sql_query(
        """
        SELECT
            bf.broker_name,
            bf.buy_lots,
            bf.sell_lots,
            bf.net_lots,
            bf.avg_price,
            CASE
                WHEN dp.volume IS NULL OR dp.volume = 0 THEN NULL
                ELSE bf.sell_lots * 100.0 / dp.volume
            END AS sell_pct
        FROM broker_flow bf
        LEFT JOIN daily_price dp
          ON dp.ticker = bf.ticker AND dp.trade_date = bf.trade_date
        WHERE bf.ticker = ? AND bf.trade_date = ? AND bf.net_lots < 0
        ORDER BY bf.net_lots ASC
        LIMIT 15
        """,
        conn,
        params=(ticker, broker_date),
    )
    return buy_df, sell_df, broker_date


def _load_tdcc_snapshot(conn: sqlite3.Connection, ticker: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not _table_exists(conn, "shareholder_distribution"):
        return pd.DataFrame(), pd.DataFrame()

    dates = [
        row[0]
        for row in conn.execute(
            """
            SELECT DISTINCT data_date
            FROM shareholder_distribution
            WHERE ticker = ?
            ORDER BY data_date DESC
            LIMIT 2
            """,
            (ticker,),
        ).fetchall()
    ]
    if not dates:
        return pd.DataFrame(), pd.DataFrame()

    latest = _summarize_tdcc(conn, ticker, dates[0])
    previous = _summarize_tdcc(conn, ticker, dates[1]) if len(dates) > 1 else pd.DataFrame()
    return latest, previous


def _summarize_tdcc(conn: sqlite3.Connection, ticker: str, data_date: str) -> pd.DataFrame:
    df = pd.read_sql_query(
        """
        SELECT tier_code, pct
        FROM shareholder_distribution
        WHERE ticker = ? AND data_date = ?
        """,
        conn,
        params=(ticker, data_date),
    )
    if df.empty:
        return pd.DataFrame()
    pct_map = df.set_index("tier_code")["pct"]
    summary = pd.DataFrame(
        [
            {
                "data_date": data_date,
                "pct_over_400": pct_map.reindex([12, 13, 14, 15]).fillna(0).sum(),
                "pct_over_1000": float(pct_map.get(15, 0.0)),
                "pct_retail_lt10": pct_map.reindex([1, 2, 3]).fillna(0).sum(),
            }
        ]
    )
    return summary


def _normalize_date_df(df: pd.DataFrame, column: str) -> pd.DataFrame:
    if df.empty or column not in df:
        return df
    df[column] = pd.to_datetime(df[column], errors="coerce")
    return df.dropna(subset=[column]).reset_index(drop=True)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_has_rows(conn: sqlite3.Connection, table_name: str, ticker: str, date_col: str) -> bool:
    if not _table_exists(conn, table_name):
        return False
    row = conn.execute(
        f"SELECT 1 FROM {table_name} WHERE ticker = ? ORDER BY {date_col} DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    return row is not None


def _format_signed_lots(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value / 1000.0:+,.0f} 張"


def _format_delta_signed(value: float | int | None, unit: str) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"{value:+,.0f} {unit}"


def _format_value_oku(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value / 100000.0:,.2f} 億"


@st.cache_data(ttl=3600)
def _load_all_universe() -> tuple[dict, dict[str, str], dict[str, str], str]:
    return load_universe("all")


@st.cache_data(ttl=600)
def _ticker_exists_in_daily_price(ticker: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT 1 FROM daily_price WHERE ticker = ? LIMIT 1",
        (ticker,),
    ).fetchone()
    conn.close()
    return row is not None


def _ticker_exists(ticker: str, companies: dict[str, str]) -> bool:
    return ticker in companies or _ticker_exists_in_daily_price(ticker)


@st.cache_data(ttl=600)
def _load_ohlcv(ticker: str, tf: str) -> pd.DataFrame:
    if tf in INTRADAY_TFS:
        return _load_intraday_ohlcv(ticker, tf)
    rows = load_daily_ohlcv(ticker)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("trade_date").reset_index(drop=True)
    if tf == "1W":
        df = _resample_ohlcv(df, tf)
    return df


def _load_intraday_ohlcv(ticker: str, tf: str) -> pd.DataFrame:
    """讀 5m 原生 → 必要時 resample. 統一回傳欄名 trade_date (datetime, tz-naive)."""
    from fetch_intraday import ensure_intraday_table, load_intraday, PRIMITIVE_TF

    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_intraday_table(conn)
        df = load_intraday(conn, ticker, tf=PRIMITIVE_TF)
    finally:
        conn.close()
    if df.empty:
        return df
    # tz-naive 化以便 plotly 顯示時間軸 (rangebreaks 不支援 tz-aware)
    if df.index.tz is not None:
        df = df.tz_localize(None)
    if tf != PRIMITIVE_TF:
        rule, offset = INTRADAY_RESAMPLE_RULE[tf]
        kwargs: dict = dict(label="right", closed="right")
        if offset:
            kwargs["offset"] = offset
        df = (
            df.resample(rule, **kwargs)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
            .dropna(subset=["open", "high", "low", "close"])
        )
    df = df.reset_index().rename(columns={"ts": "trade_date"})
    return df


def _resample_ohlcv(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf != "1W":
        return df
    weekly = (
        df.set_index("trade_date")
        .resample("W-FRI", label="right", closed="right")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    return weekly


def _build_rangebreaks(tf: str) -> list[dict]:
    """plotly rangebreaks: 排除週末 + 日內非交易時段 (13:30 ~ 次日 09:00)."""
    breaks = [dict(bounds=["sat", "mon"])]
    if tf in INTRADAY_TFS:
        # 09:00–13:30 為交易時段; 其餘排除
        breaks.append(dict(bounds=[13.5, 9], pattern="hour"))
    return breaks


def _fetch_intraday_now(ticker: str) -> None:
    """UI 觸發抓取按鈕的 wrapper."""
    try:
        from fetch_intraday import fetch_and_store
        with st.spinner("yfinance 抓取 5m K 線（5 日）…"):
            summary = fetch_and_store(ticker, period="5d")
        st.success(
            f"抓 {summary['fetched']} 根，DB 共 {summary['total_in_db']} 根 "
            f"({summary['first_ts']} → {summary['last_ts']})"
        )
    except Exception as exc:
        st.error(f"抓取失敗：{exc}")


def _apply_display_range(df: pd.DataFrame, range_label: str) -> pd.DataFrame:
    if df.empty or range_label == "全部":
        return df
    days = DISPLAY_RANGE_DAYS[range_label]
    cutoff = df["trade_date"].max() - pd.Timedelta(days=days)
    return df[df["trade_date"] >= cutoff].copy()


def _enrich_price_indicators(df: pd.DataFrame) -> pd.DataFrame:
    chart_df = df.copy()
    for window in (5, 20, 60):
        chart_df[f"ma{window}"] = chart_df["close"].rolling(window).mean()
    std20 = chart_df["close"].rolling(20).std()
    chart_df["bb_upper"] = chart_df["ma20"] + std20 * 2
    chart_df["bb_lower"] = chart_df["ma20"] - std20 * 2
    return chart_df


def _build_price_chart_figure(display_df: pd.DataFrame, tf: str, ma_choices: list[str]) -> go.Figure:
    is_intraday = tf in INTRADAY_TFS
    x_fmt = "%m/%d %H:%M" if is_intraday else "%Y-%m-%d"

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.72, 0.28],
        vertical_spacing=0.03,
    )
    fig.add_trace(
        go.Candlestick(
            x=display_df["trade_date"],
            open=display_df["open"],
            high=display_df["high"],
            low=display_df["low"],
            close=display_df["close"],
            name="K 線",
            increasing_line_color=POS_COLOR,
            decreasing_line_color=NEG_COLOR,
        ),
        row=1,
        col=1,
    )

    for ma_key in ("MA5", "MA20", "MA60"):
        if ma_key not in ma_choices:
            continue
        window = int(ma_key[2:])
        fig.add_trace(
            go.Scatter(
                x=display_df["trade_date"],
                y=display_df[f"ma{window}"],
                mode="lines",
                name=ma_key,
                line=dict(color=MA_COLORS[ma_key], width=1.6),
                hovertemplate="%{x|" + x_fmt + "}<br>" + ma_key + " %{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    if "BBands" in ma_choices:
        fig.add_trace(
            go.Scatter(
                x=display_df["trade_date"],
                y=display_df["bb_upper"],
                mode="lines",
                name="BB 上軌",
                line=dict(color="#94a3b8", width=1, dash="dot"),
                hovertemplate="%{x|" + x_fmt + "}<br>BB 上軌 %{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=display_df["trade_date"],
                y=display_df["bb_lower"],
                mode="lines",
                name="BB 下軌",
                line=dict(color="#94a3b8", width=1, dash="dot"),
                hovertemplate="%{x|" + x_fmt + "}<br>BB 下軌 %{y:,.2f}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    volume_colors = [
        POS_COLOR if close >= open_ else NEG_COLOR
        for open_, close in zip(display_df["open"], display_df["close"])
    ]
    fig.add_trace(
        go.Bar(
            x=display_df["trade_date"],
            y=display_df["volume"],
            name="成交量",
            marker_color=volume_colors,
            opacity=0.72,
            hovertemplate="%{x|" + x_fmt + "}<br>成交量 %{y:,.0f}<extra></extra>",
        ),
        row=2,
        col=1,
    )

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#f1f5f9",
        plot_bgcolor="#f8fafc",
        hovermode="x unified",
        font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif", color="#1e293b"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            bgcolor=LEGEND_BG,
        ),
        margin=dict(t=56, b=36, l=48, r=18),
        height=720,
        xaxis_rangeslider_visible=False,
        bargap=0.1,
    )
    fig.update_yaxes(gridcolor=GRID_COLOR, row=1, col=1, title_text="股價")
    fig.update_yaxes(gridcolor=GRID_COLOR, row=2, col=1, title_text="成交量（張）", rangemode="tozero")
    fig.update_xaxes(gridcolor=GRID_COLOR)
    fig.update_xaxes(rangebreaks=_build_rangebreaks(tf))
    return fig


@st.cache_data(ttl=5, show_spinner=False)
def _cached_quote(ticker: str) -> dict | None:
    return fetch_quote(ticker)


def _render_quote_book(ticker: str) -> None:
    st.markdown("#### 即時五檔（MIS API · ttl=5s）")
    try:
        q = _cached_quote(ticker)
    except Exception as exc:
        st.warning(f"五檔抓取失敗：{exc}")
        return
    if q is None:
        st.caption("MIS 查無此代號（可能為非交易標的或暫停交易）。")
        return
    if "error" in q:
        st.warning(f"五檔抓取失敗：{q['error']}")
        return

    last = q.get("last")
    prev = q.get("prev_close")
    chg = q.get("change")
    pct = q.get("change_pct")

    refresh_col, info_col = st.columns([1, 5])
    if refresh_col.button("🔄 重新整理", key=f"quote_refresh_{ticker}"):
        _cached_quote.clear()
        st.rerun()
    market = (q.get("exchange") or "").upper() or "—"
    info_col.caption(
        f"市場：{market}　｜　交易日：{q.get('trade_date') or '—'}　"
        f"｜　最新撮合：{q.get('trade_time') or '—'}　｜　API 更新：{q.get('updated_at') or '—'}"
    )

    if last is None:
        st.info("⏸ 尚無成交（盤前 / 暫停 / 非交易時段）。")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("成交價", f"{last:.2f}", _format_quote_delta(chg, pct))
        m2.metric("昨收", f"{prev:.2f}" if prev else "—")
        rng_open = q.get("open")
        rng_high = q.get("high")
        rng_low = q.get("low")
        m3.metric(
            "今日區間",
            f"{rng_low:.2f} – {rng_high:.2f}" if rng_low and rng_high else "—",
            f"開 {rng_open:.2f}" if rng_open else None,
        )
        vol = q.get("volume")
        m4.metric("成交張數", f"{vol:,}" if vol is not None else "—")

    asks = list(q.get("asks") or [])
    bids = list(q.get("bids") or [])
    if not asks and not bids:
        st.caption("非交易時段或暫無五檔報價。")
        return

    book_df = _build_quote_book_df(bids, asks)
    if book_df.empty:
        st.caption("非交易時段或暫無五檔報價。")
        return
    st.dataframe(
        book_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "買量": st.column_config.NumberColumn("買量（張）", format="%d"),
            "買價": st.column_config.NumberColumn(format="%.2f"),
            "賣價": st.column_config.NumberColumn(format="%.2f"),
            "賣量": st.column_config.NumberColumn("賣量（張）", format="%d"),
        },
    )


def _format_quote_delta(change: float | None, pct: float | None) -> str | None:
    if change is None or pct is None:
        return None
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.2f} ({sign}{pct:.2f}%)"


def _build_quote_book_df(bids: list, asks: list) -> pd.DataFrame:
    rows = []
    for i in range(5):
        bid = bids[i] if i < len(bids) else None
        ask = asks[i] if i < len(asks) else None
        rows.append(
            {
                "檔位": f"第 {i + 1} 檔",
                "買量": getattr(bid, "volume", None),
                "買價": getattr(bid, "price", None),
                "賣價": getattr(ask, "price", None),
                "賣量": getattr(ask, "volume", None),
            }
        )
    df = pd.DataFrame(rows)
    if df[["買量", "買價", "賣價", "賣量"]].isna().all(axis=None):
        return pd.DataFrame()
    return df


NEWS_RANGE_OPTIONS = {"24 小時": 1, "7 天": 7, "30 天": 30, "全部": None}


@st.cache_data(ttl=300, show_spinner=False)
def _cached_news(ticker: str, since_iso: str | None, limit: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    try:
        ensure_news_cache(conn)
        return load_news(conn, ticker, limit=limit, since=since_iso)
    finally:
        conn.close()


def _render_news_feed(ticker: str, name: str) -> None:
    st.markdown("#### 📰 近期新聞（Google News RSS）")

    col_btn, col_range = st.columns([1, 4])
    if col_btn.button("🔄 更新新聞", key=f"news_refresh_{ticker}"):
        try:
            with st.spinner("抓取最新新聞…"):
                summary = fetch_and_store(ticker, name)
            _cached_news.clear()
            st.success(f"抓取 {summary['fetched']} 筆，新增 {summary['added']} 筆，DB 共 {summary['total_in_db']} 筆。")
        except Exception as exc:
            st.warning(f"新聞抓取失敗：{exc}")

    range_label = col_range.radio(
        "時間範圍",
        list(NEWS_RANGE_OPTIONS.keys()),
        horizontal=True,
        index=1,
        key=f"news_range_{ticker}",
    )
    days = NEWS_RANGE_OPTIONS[range_label]
    since_iso = None
    if days is not None:
        from datetime import datetime, timedelta, timezone
        since_iso = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")

    items = _cached_news(ticker, since_iso, 20)
    if not items:
        st.caption("此區間尚無新聞快取。點上方「🔄 更新新聞」抓取最新資料。")
        return

    for n in items:
        ts = _format_news_time(n.get("published_at"))
        src = n.get("source") or "—"
        title = n.get("title") or "(無標題)"
        url = n.get("url") or "#"
        st.markdown(
            f"`{ts}` · **{src}** ｜ [{title}]({url})",
            unsafe_allow_html=False,
        )


def _format_news_time(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso)
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return iso


def _render_extras(
    ticker: str,
    name: str,
    category: str,
    categories: dict[str, dict[str, str]],
    companies: dict[str, str],
    tf: str,
) -> None:
    with st.expander("延伸資訊（P6）", expanded=False):
        _render_basic_info_card(ticker, category)

        left, right = st.columns(2)
        with left:
            _render_monthly_revenue_panel(ticker)
        with right:
            _render_foreign_ownership_panel(ticker)

        _render_futures_panel(ticker)
        _render_peer_compare_panel(ticker, category, categories, companies)
        _render_technical_alerts(ticker)
        _render_snapshot_export(ticker, name, category, categories, companies, tf)


def _render_basic_info_card(ticker: str, category: str) -> None:
    st.markdown("#### E1 基本資料卡")
    profile = _load_price_profile(ticker)
    if not profile["has_price"]:
        st.caption("daily_price 尚無最新收盤資料。")
        return

    price_date = _format_date_value(profile["price_date"])
    foreign_date = _format_date_value(profile["foreign_date"])
    delta_text = None
    if profile["change_abs"] is not None and profile["change_pct"] is not None:
        delta_text = f"{profile['change_abs']:+.2f} ({profile['change_pct']:+.2f}%)"

    cols = st.columns(5)
    cols[0].metric("現價", _format_price(profile["close"]), delta_text)
    cols[1].metric("市值", _format_large_twd(profile["market_cap"]))
    cols[2].metric("外資持股", _format_pct(profile["foreign_pct"]))
    cols[3].metric("剩餘可投資", _format_pct(profile["remaining_pct"]))
    cols[4].metric("所屬類股", category)
    st.caption(f"收盤日：{price_date}　｜　外資持股資料日：{foreign_date}")


def _render_monthly_revenue_panel(ticker: str) -> None:
    st.markdown("#### E2 月營收迷你圖")
    df = _load_monthly_revenue_history(ticker, limit=12)
    if df.empty:
        st.caption("monthly_revenue 尚無此檔資料。")
        return

    latest = df.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric("最新月份", latest["period"])
    c2.metric("營收", f"{latest['revenue_b']:,.2f} 億" if pd.notna(latest["revenue_b"]) else "—")
    c3.metric("YoY", _format_pct(latest["yoy_pct"]), _format_pct_delta(latest["yoy_pct"], df.iloc[-2]["yoy_pct"] if len(df) >= 2 else None))

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["period"],
            y=df["revenue_b"],
            name="營收（億）",
            marker_color="#0f766e",
            hovertemplate="%{x}<br>營收 %{y:,.2f} 億<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["period"],
            y=df["yoy_pct"],
            name="YoY %",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="#f97316", width=2),
            hovertemplate="%{x}<br>YoY %{y:,.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#f1f5f9",
        plot_bgcolor="#f8fafc",
        margin=dict(t=28, b=24, l=14, r=14),
        height=300,
        font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif", color="#1e293b"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor=LEGEND_BG),
        yaxis=dict(title="營收（億）", gridcolor=GRID_COLOR),
        yaxis2=dict(title="YoY %", overlaying="y", side="right", showgrid=False),
    )
    fig.update_xaxes(gridcolor=GRID_COLOR)
    st.plotly_chart(fig, use_container_width=True)


def _render_foreign_ownership_panel(ticker: str) -> None:
    st.markdown("#### E3 外資持股比趨勢")
    df = _load_foreign_ownership_history(ticker, limit=60)
    if df.empty:
        st.caption("foreign_ownership 尚無此檔資料。")
        return

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else None
    c1, c2 = st.columns(2)
    c1.metric(
        "外資持股比",
        _format_pct(latest["foreign_pct"]),
        _format_pct_delta(latest["foreign_pct"], None if prev is None else prev["foreign_pct"]),
    )
    c2.metric(
        "剩餘可投資比率",
        _format_pct(latest["remaining_pct"]),
        _format_pct_delta(latest["remaining_pct"], None if prev is None else prev["remaining_pct"]),
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["trade_date"],
            y=df["foreign_pct"],
            mode="lines+markers",
            name="外資持股 %",
            line=dict(color="#2563eb", width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>外資持股 %{y:,.2f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["trade_date"],
            y=df["remaining_pct"],
            mode="lines+markers",
            name="剩餘可投資 %",
            line=dict(color="#0f766e", width=2),
            hovertemplate="%{x|%Y-%m-%d}<br>剩餘 %{y:,.2f}%<extra></extra>",
        )
    )
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#f1f5f9",
        plot_bgcolor="#f8fafc",
        margin=dict(t=28, b=24, l=14, r=14),
        height=300,
        font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif", color="#1e293b"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, bgcolor=LEGEND_BG),
    )
    fig.update_yaxes(title_text="%", gridcolor=GRID_COLOR)
    fig.update_xaxes(gridcolor=GRID_COLOR)
    st.plotly_chart(fig, use_container_width=True)


def _render_futures_panel(ticker: str) -> None:
    st.markdown("#### E4 期貨未平倉")
    if ticker not in FUTURES_CONTEXT_TICKERS:
        st.caption("此區塊只對期貨關聯的大型權值股顯示。")
        return

    latest_date, df = _load_futures_snapshot()
    if df.empty:
        st.caption("futures_oi 尚無資料。")
        return

    st.caption(f"最新資料日：{latest_date}")
    display_df = df.copy()
    display_df["contract"] = display_df["contract"].map(lambda v: FUTURES_CONTRACT_LABELS.get(v, v))
    display_df["role"] = display_df["role"].map(lambda v: FUTURES_ROLE_LABELS.get(v, v))
    display_df = display_df.rename(
        columns={
            "contract": "合約",
            "role": "法人",
            "net_oi": "淨未平倉",
            "net_value": "淨額（千元）",
        }
    )
    st.dataframe(
        display_df[["合約", "法人", "淨未平倉", "淨額（千元）"]],
        hide_index=True,
        use_container_width=True,
        column_config={
            "淨未平倉": st.column_config.NumberColumn(format="%d"),
            "淨額（千元）": st.column_config.NumberColumn(format="%.0f"),
        },
    )


def _render_peer_compare_panel(
    ticker: str,
    category: str,
    categories: dict[str, dict[str, str]],
    companies: dict[str, str],
) -> None:
    st.markdown("#### E5 同類股比較")
    if category not in categories:
        st.caption("此檔未收錄於 universe 類股分類，無法做同類股比較。")
        return

    days = st.radio(
        "比較區間",
        PEER_COMPARE_WINDOWS,
        horizontal=True,
        key=f"peer_compare_window_{ticker}",
        format_func=lambda value: f"近 {value} 日",
        index=1,
    )
    peer_tickers = tuple(categories[category].keys())
    df = _load_peer_compare(peer_tickers, days)
    if df.empty:
        st.caption("institutional_flow 尚無足夠資料。")
        return

    display_df = df.copy()
    display_df["股票"] = display_df["ticker"].map(lambda value: f"{value} {companies.get(value, value)}")
    display_df = display_df.rename(
        columns={
            "total_lots": f"{days} 日累積法人（張）",
            "foreign_lots": "外資（張）",
            "invest_lots": "投信（張）",
            "dealer_lots": "自營（張）",
            "price_change_pct": "區間漲跌%",
            "covered_days": "覆蓋天數",
        }
    )
    st.dataframe(
        display_df[["股票", f"{days} 日累積法人（張）", "外資（張）", "投信（張）", "自營（張）", "區間漲跌%", "覆蓋天數"]],
        hide_index=True,
        use_container_width=True,
        column_config={
            f"{days} 日累積法人（張）": st.column_config.NumberColumn(format="%.0f"),
            "外資（張）": st.column_config.NumberColumn(format="%.0f"),
            "投信（張）": st.column_config.NumberColumn(format="%.0f"),
            "自營（張）": st.column_config.NumberColumn(format="%.0f"),
            "區間漲跌%": st.column_config.NumberColumn(format="%.2f"),
            "覆蓋天數": st.column_config.NumberColumn(format="%d"),
        },
    )


def _render_technical_alerts(ticker: str) -> None:
    st.markdown("#### E6 技術面警示")
    alerts = _build_technical_alerts(ticker)
    if not alerts:
        st.info("目前沒有明確的 MA 突破 / 跌破、連續買賣超或量價背離訊號。")
        return

    for alert in alerts:
        body = f"**{alert['title']}**｜{alert['body']}"
        if alert["level"] == "warning":
            st.warning(body)
        elif alert["level"] == "success":
            st.success(body)
        else:
            st.info(body)


def _render_snapshot_export(
    ticker: str,
    name: str,
    category: str,
    categories: dict[str, dict[str, str]],
    companies: dict[str, str],
    tf: str,
) -> None:
    st.markdown("#### E7 匯出快照")
    st.caption("輸出 Markdown 至 `reports/stock_snapshot/`，包含基本卡、籌碼摘要、新聞與 K 線圖。")
    if st.button("📄 匯出 Markdown", key=f"snapshot_export_{ticker}"):
        try:
            path = _export_snapshot_markdown(ticker, name, category, categories, companies, tf)
        except Exception as exc:
            st.error(f"匯出失敗：{exc}")
            return
        st.success(f"已匯出：{path}")


@st.cache_data(ttl=300)
def _load_price_profile(ticker: str) -> dict[str, object]:
    conn = sqlite3.connect(DB_PATH)
    try:
        price_df = pd.read_sql_query(
            """
            SELECT trade_date, open, high, low, close, volume
            FROM daily_price
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT 30
            """,
            conn,
            params=(ticker,),
        )
        foreign_df = pd.read_sql_query(
            """
            SELECT trade_date, issued_shares, foreign_pct, remaining_pct
            FROM foreign_ownership
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT 1
            """,
            conn,
            params=(ticker,),
        )
    finally:
        conn.close()

    profile: dict[str, object] = {
        "has_price": not price_df.empty,
        "price_date": None,
        "close": None,
        "change_abs": None,
        "change_pct": None,
        "market_cap": None,
        "issued_shares": None,
        "foreign_date": None,
        "foreign_pct": None,
        "remaining_pct": None,
    }
    if price_df.empty:
        return profile

    for col in ("open", "high", "low", "close", "volume"):
        price_df[col] = pd.to_numeric(price_df[col], errors="coerce")
    price_df = price_df.dropna(subset=["close"]).reset_index(drop=True)
    if price_df.empty:
        profile["has_price"] = False
        return profile

    latest = price_df.iloc[0]
    prev = price_df.iloc[1] if len(price_df) >= 2 else None
    close = latest["close"]
    prev_close = None if prev is None else prev["close"]
    change_abs = None if prev_close is None or pd.isna(prev_close) else close - prev_close
    change_pct = None
    if change_abs is not None and prev_close not in (None, 0) and pd.notna(prev_close):
        change_pct = change_abs / prev_close * 100

    profile.update(
        {
            "price_date": latest["trade_date"],
            "close": close,
            "change_abs": change_abs,
            "change_pct": change_pct,
        }
    )

    if not foreign_df.empty:
        for col in ("issued_shares", "foreign_pct", "remaining_pct"):
            foreign_df[col] = pd.to_numeric(foreign_df[col], errors="coerce")
        foreign_latest = foreign_df.iloc[0]
        market_cap = None
        if pd.notna(foreign_latest["issued_shares"]) and pd.notna(close):
            market_cap = float(foreign_latest["issued_shares"]) * float(close)
        profile.update(
            {
                "market_cap": market_cap,
                "issued_shares": foreign_latest["issued_shares"],
                "foreign_date": foreign_latest["trade_date"],
                "foreign_pct": foreign_latest["foreign_pct"],
                "remaining_pct": foreign_latest["remaining_pct"],
            }
        )
    return profile


@st.cache_data(ttl=3600)
def _load_monthly_revenue_history(ticker: str, limit: int = 12) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT year, month, revenue_m, mom_pct, yoy_pct, cum_revenue, cum_yoy_pct
            FROM monthly_revenue
            WHERE ticker = ?
            ORDER BY year DESC, month DESC
            LIMIT ?
            """,
            conn,
            params=(ticker, limit),
        )
    finally:
        conn.close()
    if df.empty:
        return df

    for col in ("revenue_m", "mom_pct", "yoy_pct", "cum_revenue", "cum_yoy_pct"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values(["year", "month"]).reset_index(drop=True)
    df["period"] = df["year"].astype(int).astype(str) + "-" + df["month"].astype(int).map(lambda value: f"{value:02d}")
    df["period_date"] = pd.to_datetime(dict(year=df["year"], month=df["month"], day=1), errors="coerce")
    df["revenue_b"] = df["revenue_m"] / 100.0
    return df


@st.cache_data(ttl=600)
def _load_foreign_ownership_history(ticker: str, limit: int = 60) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT trade_date, issued_shares, foreign_shares, foreign_pct, remaining_pct, limit_pct
            FROM foreign_ownership
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            conn,
            params=(ticker, limit),
        )
    finally:
        conn.close()
    if df.empty:
        return df

    df = _normalize_date_df(df, "trade_date")
    for col in ("issued_shares", "foreign_shares", "foreign_pct", "remaining_pct", "limit_pct"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("trade_date").reset_index(drop=True)


@st.cache_data(ttl=600)
def _load_institutional_recent(ticker: str, limit: int = 20) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query(
            """
            SELECT trade_date, foreign_net, invest_net, dealer_net, total_net
            FROM institutional_flow
            WHERE ticker = ?
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            conn,
            params=(ticker, limit),
        )
    finally:
        conn.close()
    if df.empty:
        return df

    df = _normalize_date_df(df, "trade_date")
    for col in ("foreign_net", "invest_net", "dealer_net", "total_net"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("trade_date").reset_index(drop=True)


@st.cache_data(ttl=600)
def _load_institutional_trade_dates(limit: int) -> tuple[str, ...]:
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT DISTINCT trade_date
            FROM institutional_flow
            ORDER BY trade_date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return tuple(sorted(row[0] for row in rows if row[0]))


@st.cache_data(ttl=600)
def _load_peer_compare(category_tickers: tuple[str, ...], days: int) -> pd.DataFrame:
    if not category_tickers:
        return pd.DataFrame()

    dates = list(_load_institutional_trade_dates(days))
    if not dates:
        return pd.DataFrame()

    cached = load_from_db(dates)
    min_date = min(dates)

    conn = sqlite3.connect(DB_PATH)
    try:
        placeholders = ",".join("?" * len(category_tickers))
        price_df = pd.read_sql_query(
            f"""
            SELECT ticker, trade_date, close
            FROM daily_price
            WHERE ticker IN ({placeholders}) AND trade_date >= ?
            ORDER BY ticker, trade_date
            """,
            conn,
            params=[*category_tickers, min_date],
        )
    finally:
        conn.close()

    price_change_map: dict[str, float | None] = {}
    if not price_df.empty:
        price_df["close"] = pd.to_numeric(price_df["close"], errors="coerce")
        for peer_ticker, group in price_df.groupby("ticker"):
            group = group.dropna(subset=["close"])
            if group.empty:
                continue
            start_close = group.iloc[0]["close"]
            end_close = group.iloc[-1]["close"]
            if pd.notna(start_close) and start_close not in (None, 0) and pd.notna(end_close):
                price_change_map[peer_ticker] = float(end_close / start_close * 100 - 100)
            else:
                price_change_map[peer_ticker] = None

    rows = []
    for peer_ticker in category_tickers:
        foreign = invest = dealer = total = 0.0
        covered_days = 0
        for trade_date in dates:
            row = cached.get((peer_ticker, trade_date))
            if not row:
                continue
            covered_days += 1
            foreign += row.get("foreign") or 0.0
            invest += row.get("invest") or 0.0
            dealer += row.get("dealer") or 0.0
            total += row.get("total") or 0.0
        if covered_days == 0:
            continue
        rows.append(
            {
                "ticker": peer_ticker,
                "foreign_lots": foreign / 1000.0,
                "invest_lots": invest / 1000.0,
                "dealer_lots": dealer / 1000.0,
                "total_lots": total / 1000.0,
                "price_change_pct": price_change_map.get(peer_ticker),
                "covered_days": covered_days,
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["total_lots", "price_change_pct"],
        ascending=[False, False],
        na_position="last",
    ).reset_index(drop=True)


@st.cache_data(ttl=600)
def _load_futures_snapshot() -> tuple[str | None, pd.DataFrame]:
    conn = sqlite3.connect(DB_PATH)
    try:
        if not _table_exists(conn, "futures_oi"):
            return None, pd.DataFrame()
        row = conn.execute("SELECT MAX(trade_date) FROM futures_oi").fetchone()
        latest_date = row[0] if row and row[0] else None
        if not latest_date:
            return None, pd.DataFrame()
        df = pd.read_sql_query(
            """
            SELECT contract, role, net_oi, net_value
            FROM futures_oi
            WHERE trade_date = ? AND contract IN ('TXF', 'EXF')
            ORDER BY contract,
                     CASE role
                       WHEN 'foreign' THEN 1
                       WHEN 'invest' THEN 2
                       WHEN 'dealer' THEN 3
                       ELSE 4
                     END
            """,
            conn,
            params=(latest_date,),
        )
    finally:
        conn.close()
    if df.empty:
        return latest_date, df

    for col in ("net_oi", "net_value"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return latest_date, df


def _build_technical_alerts(ticker: str) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    df = _load_ohlcv(ticker, "1D")
    if len(df) >= 61:
        chart_df = _enrich_price_indicators(df).dropna(subset=["close"]).reset_index(drop=True)
        if len(chart_df) >= 2:
            latest = chart_df.iloc[-1]
            prev = chart_df.iloc[-2]
            for window in (20, 60):
                ma_key = f"ma{window}"
                if pd.isna(latest[ma_key]) or pd.isna(prev[ma_key]):
                    continue
                if prev["close"] <= prev[ma_key] and latest["close"] > latest[ma_key]:
                    alerts.append(
                        {
                            "level": "success",
                            "title": f"站上 MA{window}",
                            "body": f"最新收盤 {latest['close']:.2f} 由下往上突破 MA{window} {latest[ma_key]:.2f}。",
                        }
                    )
                elif prev["close"] >= prev[ma_key] and latest["close"] < latest[ma_key]:
                    alerts.append(
                        {
                            "level": "warning",
                            "title": f"跌破 MA{window}",
                            "body": f"最新收盤 {latest['close']:.2f} 由上往下跌破 MA{window} {latest[ma_key]:.2f}。",
                        }
                    )

            if len(chart_df) >= 25:
                last_5 = chart_df.tail(5)
                prev_20 = chart_df.iloc[-25:-5]
                if not prev_20.empty and pd.notna(last_5.iloc[0]["close"]) and last_5.iloc[0]["close"] not in (None, 0):
                    price_change_5d = latest["close"] / last_5.iloc[0]["close"] - 1
                    vol_5 = last_5["volume"].mean()
                    vol_20 = prev_20["volume"].mean()
                    if pd.notna(vol_5) and pd.notna(vol_20) and vol_20 > 0:
                        vol_ratio = vol_5 / vol_20
                        if price_change_5d >= 0.05 and vol_ratio <= 0.8:
                            alerts.append(
                                {
                                    "level": "warning",
                                    "title": "價漲量縮",
                                    "body": f"近 5 日股價上漲 {price_change_5d * 100:.2f}%，但均量僅為前 20 日的 {vol_ratio * 100:.0f}%。",
                                }
                            )
                        elif price_change_5d <= -0.05 and vol_ratio >= 1.3:
                            alerts.append(
                                {
                                    "level": "warning",
                                    "title": "價跌量增",
                                    "body": f"近 5 日股價下跌 {abs(price_change_5d) * 100:.2f}%，但均量放大到前 20 日的 {vol_ratio * 100:.0f}%。",
                                }
                            )

    flow_df = _load_institutional_recent(ticker, limit=20)
    if not flow_df.empty and flow_df["total_net"].notna().any():
        streak_sign, streak_days = _calculate_flow_streak(flow_df["total_net"])
        if streak_days >= 2:
            if streak_sign > 0:
                alerts.append(
                    {
                        "level": "info",
                        "title": "連續法人買超",
                        "body": f"三大法人合計已連續買超 {streak_days} 日。",
                    }
                )
            elif streak_sign < 0:
                alerts.append(
                    {
                        "level": "warning",
                        "title": "連續法人賣超",
                        "body": f"三大法人合計已連續賣超 {streak_days} 日。",
                    }
                )
    return alerts


def _calculate_flow_streak(series: pd.Series) -> tuple[int, int]:
    clean = series.dropna().tolist()
    if not clean:
        return 0, 0
    latest = clean[-1]
    if latest == 0:
        return 0, 0

    sign = 1 if latest > 0 else -1
    streak = 0
    for value in reversed(clean):
        if value == 0:
            break
        value_sign = 1 if value > 0 else -1
        if value_sign != sign:
            break
        streak += 1
    return sign, streak


def _export_snapshot_markdown(
    ticker: str,
    name: str,
    category: str,
    categories: dict[str, dict[str, str]],
    companies: dict[str, str],
    tf: str,
) -> Path:
    profile = _load_price_profile(ticker)
    chip = _fetch_chip_snapshot(ticker)
    revenue_df = _load_monthly_revenue_history(ticker, limit=12)
    foreign_df = _load_foreign_ownership_history(ticker, limit=60)
    alerts = _build_technical_alerts(ticker)
    news_items = _cached_news(ticker, None, 5)

    peer_df = pd.DataFrame()
    if category in categories:
        peer_df = _load_peer_compare(tuple(categories[category].keys()), 20)

    chart_df, chart_tf = _prepare_snapshot_chart_data(ticker, tf)
    chart_b64 = None
    if not chart_df.empty:
        fig = _build_price_chart_figure(chart_df, chart_tf, SNAPSHOT_DEFAULT_INDICATORS)
        chart_b64 = _figure_to_base64_png(fig, chart_df, chart_tf)

    content = _build_snapshot_markdown(
        ticker=ticker,
        name=name,
        category=category,
        companies=companies,
        profile=profile,
        chip=chip,
        revenue_df=revenue_df,
        foreign_df=foreign_df,
        peer_df=peer_df,
        alerts=alerts,
        news_items=news_items,
        chart_b64=chart_b64,
        chart_tf=chart_tf,
    )

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"snapshot_{ticker}_{datetime.now().strftime('%Y%m%d')}.md"
    path.write_text(content, encoding="utf-8")
    return path


def _prepare_snapshot_chart_data(ticker: str, tf: str) -> tuple[pd.DataFrame, str]:
    chart_tf = tf
    full_df = _load_ohlcv(ticker, chart_tf)
    if full_df.empty and chart_tf in INTRADAY_TFS:
        chart_tf = "1D"
        full_df = _load_ohlcv(ticker, chart_tf)
    if full_df.empty:
        return pd.DataFrame(), chart_tf

    chart_df = _enrich_price_indicators(full_df)
    chart_df = _apply_display_range(chart_df, DEFAULT_RANGE_BY_TF[chart_tf])
    chart_df = chart_df.dropna(subset=["open", "high", "low", "close"]).copy()
    return chart_df, chart_tf


def _figure_to_base64_png(fig: go.Figure, chart_df: pd.DataFrame, chart_tf: str) -> str | None:
    try:
        image_bytes = fig.to_image(format="png", width=1440, height=900, scale=1)
    except Exception:
        return _build_matplotlib_chart_base64(chart_df, chart_tf)
    return base64.b64encode(image_bytes).decode("ascii")


def _build_matplotlib_chart_base64(chart_df: pd.DataFrame, chart_tf: str) -> str | None:
    if chart_df.empty:
        return None

    from io import BytesIO

    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.patches import Rectangle
    except Exception:
        return None

    plot_df = chart_df.copy()
    plot_df["trade_date"] = pd.to_datetime(plot_df["trade_date"], errors="coerce")
    plot_df = plot_df.dropna(subset=["trade_date", "open", "high", "low", "close"])
    if plot_df.empty:
        return None

    dates = mdates.date2num([ts.to_pydatetime() for ts in plot_df["trade_date"]])
    width = _matplotlib_candle_width(dates)
    fig, (ax_price, ax_volume) = plt.subplots(
        2,
        1,
        figsize=(14, 9),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 1]},
        facecolor="#f1f5f9",
    )
    ax_price.set_facecolor("#f8fafc")
    ax_volume.set_facecolor("#f8fafc")

    for x, open_, high, low, close in zip(dates, plot_df["open"], plot_df["high"], plot_df["low"], plot_df["close"]):
        color = POS_COLOR if close >= open_ else NEG_COLOR
        ax_price.vlines(x, low, high, color=color, linewidth=1.1)
        body_bottom = min(open_, close)
        body_height = max(abs(close - open_), 0.01)
        ax_price.add_patch(
            Rectangle(
                (x - width / 2, body_bottom),
                width,
                body_height,
                facecolor=color,
                edgecolor=color,
                linewidth=1.0,
            )
        )

    for ma_key, color in (("ma5", MA_COLORS["MA5"]), ("ma20", MA_COLORS["MA20"]), ("ma60", MA_COLORS["MA60"])):
        if ma_key in plot_df:
            ax_price.plot(dates, plot_df[ma_key], color=color, linewidth=1.4, label=ma_key.upper())

    volume_colors = [
        POS_COLOR if close >= open_ else NEG_COLOR
        for open_, close in zip(plot_df["open"], plot_df["close"])
    ]
    ax_volume.bar(dates, plot_df["volume"].fillna(0), width=width, color=volume_colors, alpha=0.72)

    ax_price.grid(color=GRID_COLOR, alpha=0.8)
    ax_volume.grid(color=GRID_COLOR, alpha=0.8)
    ax_price.set_ylabel("Price")
    ax_volume.set_ylabel("Volume")
    ax_price.legend(loc="upper left")

    date_fmt = "%m/%d %H:%M" if chart_tf in INTRADAY_TFS else "%Y-%m-%d"
    ax_volume.xaxis.set_major_formatter(mdates.DateFormatter(date_fmt))
    fig.autofmt_xdate()
    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _matplotlib_candle_width(dates: list[float] | object) -> float:
    if len(dates) < 2:
        return 0.6
    diffs = pd.Series(dates).diff().dropna()
    if diffs.empty:
        return 0.6
    return max(float(diffs.median()) * 0.7, 0.02)


def _build_snapshot_markdown(
    *,
    ticker: str,
    name: str,
    category: str,
    companies: dict[str, str],
    profile: dict[str, object],
    chip: dict[str, pd.DataFrame | str | None],
    revenue_df: pd.DataFrame,
    foreign_df: pd.DataFrame,
    peer_df: pd.DataFrame,
    alerts: list[dict[str, str]],
    news_items: list[dict],
    chart_b64: str | None,
    chart_tf: str,
) -> str:
    lines = [
        f"# {ticker} {name} 個股快照",
        "",
        f"- 匯出時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 類股：{category}",
        f"- K 線週期：{chart_tf}",
        "",
        "## 基本資料",
        "",
        "| 指標 | 數值 |",
        "| --- | --- |",
        f"| 現價 | {_format_price(profile.get('close'))} |",
        f"| 漲跌 | {_format_snapshot_change(profile.get('change_abs'), profile.get('change_pct'))} |",
        f"| 市值 | {_format_large_twd(profile.get('market_cap'))} |",
        f"| 外資持股 | {_format_pct(profile.get('foreign_pct'))} |",
        f"| 剩餘可投資 | {_format_pct(profile.get('remaining_pct'))} |",
        "",
    ]

    if chart_b64:
        lines.extend(
            [
                "## K 線圖",
                "",
                f'<img src="data:image/png;base64,{chart_b64}" alt="{ticker} chart" />',
                "",
            ]
        )

    lines.extend(["## 籌碼摘要", ""])
    chip_lines_added = False
    inst_df = chip.get("institutional", pd.DataFrame())
    if isinstance(inst_df, pd.DataFrame) and not inst_df.empty:
        latest = inst_df.iloc[-1]
        lines.append(
            f"- 三大法人最新日 `{latest['trade_date'].strftime('%Y-%m-%d')}`："
            f"外資 {_format_signed_lots(latest['foreign_net'])}、"
            f"投信 {_format_signed_lots(latest['invest_net'])}、"
            f"自營 {_format_signed_lots(latest['dealer_net'])}、"
            f"合計 {_format_signed_lots(latest['total_net'])}"
        )
        chip_lines_added = True
    margin_df = chip.get("margin", pd.DataFrame())
    if isinstance(margin_df, pd.DataFrame) and not margin_df.empty:
        latest = margin_df.iloc[-1]
        lines.append(
            f"- 融資券 `{latest['trade_date'].strftime('%Y-%m-%d')}`："
            f"融資餘額 {latest['margin_balance']:,.0f} 張（{_format_delta_signed(latest['margin_change'], '張') or '—'}），"
            f"融券餘額 {latest['short_balance']:,.0f} 張（{_format_delta_signed(latest['short_change'], '張') or '—'}）"
        )
        chip_lines_added = True
    tdcc_df = chip.get("tdcc_latest", pd.DataFrame())
    if isinstance(tdcc_df, pd.DataFrame) and not tdcc_df.empty:
        latest = tdcc_df.iloc[0]
        lines.append(
            f"- 集保 `{latest['data_date']}`：400 張以上 {latest['pct_over_400']:.2f}% / "
            f"1000 張以上 {latest['pct_over_1000']:.2f}% / 散戶 <10 張 {latest['pct_retail_lt10']:.2f}%"
        )
        chip_lines_added = True
    if not chip_lines_added:
        lines.append("- 無可用籌碼摘要。")
    lines.append("")

    if not revenue_df.empty:
        latest = revenue_df.iloc[-1]
        lines.extend(
            [
                "## 月營收",
                "",
                f"- 最新 `{latest['period']}`：{latest['revenue_b']:,.2f} 億，MoM {_format_pct(latest['mom_pct'])}，YoY {_format_pct(latest['yoy_pct'])}",
                "",
            ]
        )

    if not foreign_df.empty:
        latest = foreign_df.iloc[-1]
        lines.extend(
            [
                "## 外資持股趨勢",
                "",
                f"- 最新 `{latest['trade_date'].strftime('%Y-%m-%d')}`：外資持股 {_format_pct(latest['foreign_pct'])}，剩餘可投資 {_format_pct(latest['remaining_pct'])}",
                "",
            ]
        )

    if not peer_df.empty:
        lines.extend(["## 同類股比較（近 20 日）", "", "| 股票 | 累積法人（張） | 區間漲跌% |", "| --- | ---: | ---: |"])
        for _, row in peer_df.head(5).iterrows():
            peer_ticker = row["ticker"]
            price_change_text = "—" if pd.isna(row["price_change_pct"]) else f"{row['price_change_pct']:.2f}"
            lines.append(
                f"| {peer_ticker} {companies.get(peer_ticker, peer_ticker)} | "
                f"{row['total_lots']:,.0f} | "
                f"{price_change_text} |"
            )
        lines.append("")

    lines.extend(["## 技術警示", ""])
    if alerts:
        for alert in alerts:
            lines.append(f"- {alert['title']}：{alert['body']}")
    else:
        lines.append("- 目前無明確訊號。")
    lines.append("")

    lines.extend(["## 近期新聞", ""])
    if news_items:
        for item in news_items:
            ts = _format_news_time(item.get("published_at"))
            title = item.get("title") or "(無標題)"
            source = item.get("source") or "—"
            url = item.get("url") or "#"
            lines.append(f"- `{ts}` {source}｜[{title}]({url})")
    else:
        lines.append("- 尚無新聞快取。")
    lines.append("")

    return "\n".join(lines)


def _format_price(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.2f}"


def _format_pct(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.2f}%"


def _format_pct_delta(latest: object, previous: object) -> str | None:
    if latest is None or previous is None or pd.isna(latest) or pd.isna(previous):
        return None
    return f"{float(latest) - float(previous):+.2f} pct"


def _format_large_twd(value: object) -> str:
    if value is None or pd.isna(value):
        return "—"
    value = float(value)
    abs_value = abs(value)
    if abs_value >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:,.2f} 兆"
    if abs_value >= 100_000_000:
        return f"{value / 100_000_000:,.2f} 億"
    return f"{value:,.0f}"


def _format_snapshot_change(change_abs: object, change_pct: object) -> str:
    if change_abs is None or change_pct is None or pd.isna(change_abs) or pd.isna(change_pct):
        return "—"
    return f"{float(change_abs):+.2f} ({float(change_pct):+.2f}%)"


def _format_date_value(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    try:
        return pd.to_datetime(value).strftime("%Y-%m-%d")
    except Exception:
        return str(value)
