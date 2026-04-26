import sqlite3
from datetime import date, datetime, timedelta

import streamlit as st

from dashboard.helpers import _key_for_unit, _unit_scale
from sector_flow import (
    load_universe,
    trading_dates_in_range,
    split_into_periods,
    load_from_db,
    aggregate_by_category,
    DB_PATH,
)


@st.cache_data(ttl=3600)
def cached_load_universe(tier: str):
    return load_universe(tier)


@st.cache_data(ttl=60)
def _cached_latest_date() -> str:
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT MAX(trade_date) FROM institutional_flow").fetchone()
        conn.close()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


@st.cache_data(ttl=3600)
def load_data(
    start_str: str,
    end_str: str,
    split: str,
    tier: str,
    institution: str,
    unit: str = "value_oku",
) -> tuple[list, list, dict, list]:
    categories, _all_tickers, ticker_to_cat, _ = cached_load_universe(tier)
    start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_str, "%Y-%m-%d").date()

    if split == "day":
        all_dates = []
        cur = start_dt
        while cur <= end_dt:
            if cur.weekday() < 5:
                all_dates.append(cur.strftime("%Y-%m-%d"))
            cur += timedelta(days=1)
    else:
        all_dates = trading_dates_in_range(start_dt, end_dt)
    if not all_dates:
        return [], list(categories.keys()), {}, []

    date_groups = split_into_periods(all_dates, split)
    db_data = load_from_db(all_dates)
    dates_with_data = set(d for _, d in db_data.keys())

    period_labels = [label for label, _ in date_groups]
    cat_list = list(categories.keys())
    missing_labels: list[str] = []

    period_data: dict[str, dict] = {
        cat: {"raw": [], "pos": [], "cumsum": [], "foreign": [], "invest": [], "dealer": []}
        for cat in cat_list
    }

    running: dict[str, float] = {cat: 0.0 for cat in cat_list}
    scale = _unit_scale(unit)
    main_k = _key_for_unit(institution, unit)
    fk = _key_for_unit("foreign", unit)
    ik = _key_for_unit("invest", unit)
    dk = _key_for_unit("dealer", unit)

    for label, dates in date_groups:
        agg = aggregate_by_category(db_data, dates, categories, ticker_to_cat)
        if not any(d in dates_with_data for d in dates):
            missing_labels.append(label)
        for cat in cat_list:
            val = agg[cat].get(main_k, 0.0) * scale
            running[cat] += val
            period_data[cat]["raw"].append(val)
            period_data[cat]["pos"].append(abs(val))
            period_data[cat]["cumsum"].append(running[cat])
            period_data[cat]["foreign"].append(agg[cat].get(fk, 0.0) * scale)
            period_data[cat]["invest"].append(agg[cat].get(ik, 0.0) * scale)
            period_data[cat]["dealer"].append(agg[cat].get(dk, 0.0) * scale)

    return period_labels, cat_list, period_data, missing_labels


def load_trading_dates(start_date: date, end_date: date) -> list[str]:
    return trading_dates_in_range(start_date, end_date)
