#!/usr/bin/env python3
"""
sector_flow_dashboard.py — 主力資金類股輪動 Streamlit 儀表板

啟動：streamlit run scripts/sector_flow_dashboard.py
"""

import sys
import json
from pathlib import Path
from dataclasses import dataclass

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

from datetime import date, timedelta, datetime

import numpy as np
import streamlit as st

# Delay local path injection until after third-party imports so sibling files
# cannot accidentally shadow installed packages such as numpy/pandas.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from dashboard.data import (
    cached_load_universe,
    _cached_latest_date,
    load_data,
    load_trading_dates,
)
from dashboard.helpers import (
    COLORS, DEFAULT_COLOR, INSTITUTION_MAP, UNIT_MAP, TIER_MAP, SPLIT_MAP,
)
from dashboard.panels import build_panel_data
from dashboard.tabs import (
    TabContext,
    render_alerts,
    render_scrubber,
    render_tab1,
    render_tab2,
    render_tab3,
    render_tab4,
    render_tab5,
    render_tab6,
    render_tab7,
    render_tab8,
    render_detail,
)
from sector_flow import (
    init_db,
    ensure_data,
    ensure_calendar,
    ensure_margin_data,
    fetch_broker_today,
    ensure_qfii_data,
    ensure_futures_data,
    ensure_tdcc_data,
    UNIVERSE_PATH,
)


# ── 頁面設定 ─────────────────────────────────────────────────
st.set_page_config(
    page_title="主力資金類股輪動",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background-color: #f1f5f9; color: #1e293b; }
    .stSidebar { background-color: #e2e8f0; }
    .stSidebar * { color: #1e293b; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not UNIVERSE_PATH.exists():
    st.error(f"找不到 `research/stock_universe.json`\n\n路徑：{UNIVERSE_PATH}")
    st.stop()

@dataclass(frozen=True)
class SidebarParams:
    start_date: date
    end_date: date
    institution_label: str
    institution: str
    unit_label: str
    unit: str
    tier_label_sel: str
    tier: str
    split_label: str
    split: str
    selected_cats: list[str]
    margin_auto: bool
    broker_auto: bool
    fut_auto: bool


def render_sidebar() -> SidebarParams:
    with st.sidebar:
        st.title("控制面板")

        st.subheader("📅 日期區間")
        _today = date.today()
        _quick_cols = st.columns(4)
        _quick_map = {"30天": 30, "90天": 90, "半年": 180, "今年": None}
        for _i, (_ql, _qv) in enumerate(_quick_map.items()):
            if _quick_cols[_i].button(_ql, width="stretch", key=f"quick_{_ql}"):
                if _qv:
                    st.session_state["_qs"] = (_today - timedelta(days=_qv)).isoformat()
                else:
                    st.session_state["_qs"] = date(_today.year, 1, 1).isoformat()
                st.session_state["_qe"] = _today.isoformat()
        _default_start = date.fromisoformat(st.session_state["_qs"]) if "_qs" in st.session_state else (_today - timedelta(days=90))
        _default_end   = date.fromisoformat(st.session_state["_qe"]) if "_qe" in st.session_state else _today
        start_date = st.date_input("開始日期", value=_default_start)
        end_date   = st.date_input("結束日期", value=_default_end)

        if start_date >= end_date:
            st.error("開始日期必須早於結束日期")
            st.stop()

        st.subheader("🏦 法人類型")
        institution_label = st.radio("選擇法人", options=list(INSTITUTION_MAP.keys()), index=0)
        institution = INSTITUTION_MAP[institution_label]

        st.subheader("💰 顯示單位")
        unit_label = st.radio("單位", options=list(UNIT_MAP.keys()), index=0)
        unit = UNIT_MAP[unit_label]

        st.subheader("📦 標的範圍")
        tier_label_sel = st.radio("選擇 Tier", options=list(TIER_MAP.keys()), index=0)
        tier = TIER_MAP[tier_label_sel]

        st.subheader("📊 時間分組")
        split_label = st.radio("分組方式", options=list(SPLIT_MAP.keys()), index=2)
        split = SPLIT_MAP[split_label]

        st.subheader("🔍 類股篩選")
        _preview_cats = list(cached_load_universe(tier)[0].keys())
        # Preset 載入
        _preset_path = ROOT_DIR / "research" / "dashboard_presets.json"
        _presets = {}
        if _preset_path.exists():
            try:
                _presets = json.loads(_preset_path.read_text(encoding="utf-8"))
            except Exception:
                _presets = {}
        _preset_choice = st.selectbox(
            "快速預設",
            options=["（自訂）"] + list(_presets.keys()),
            index=0,
        )
        if _preset_choice != "（自訂）":
            _preset_cats = [c for c in _presets[_preset_choice] if c in _preview_cats]
            _default_sel = _preset_cats
        else:
            _default_sel = []
        _selected_cats = st.multiselect(
            "選擇顯示類股（空白 = 全選）",
            options=_preview_cats,
            default=_default_sel,
            placeholder="全選...",
        )

        with st.expander("📈 期貨未平倉"):
            _fut_auto = st.checkbox("顯示 Tab 8：期現連動", value=False,
                                    help="勾選後自動補抓 TAIFEX 三大法人期貨未平倉（TXF 臺指期 + EXF 電子期）")

        with st.expander("🏦 券商分點"):
            _broker_auto = st.checkbox("顯示 Tab 7：券商動向", value=False,
                                        help="顯示類股級別前 15 大券商排行。需先抓分點資料。")
            if _broker_auto and st.button("📥 抓取今日分點（HiStock）", width="stretch"):
                _, _b_tkrs, _, _ = cached_load_universe(tier)
                with st.spinner(f"抓取 {len(_b_tkrs)} 檔分點（預估 {len(_b_tkrs)*2.5/60:.1f} 分鐘）..."):
                    try:
                        n = fetch_broker_today(_b_tkrs, date.today().isoformat(), sleep_sec=2.5)
                        st.success(f"完成，寫入 {n} 筆")
                    except Exception as e:
                        st.error(f"失敗：{e}")
                st.cache_data.clear()
                st.rerun()

        with st.expander("📉 散戶情緒（融資融券）"):
            _margin_auto = st.checkbox("顯示 Tab 6：散戶情緒", value=False,
                                        help="勾選後自動補抓融資融券資料（TWSE MI_MARGN + TPEx margin_bal）")
            if _margin_auto and st.button("🔄 補抓融資融券", width="stretch"):
                st.cache_data.clear()
                _, _m_tkrs, _, _ = cached_load_universe(tier)
                with st.spinner("補抓融資融券..."):
                    try:
                        _m_dates = ensure_calendar(start_date, end_date)
                        ensure_margin_data(_m_dates, _m_tkrs, no_fetch=False)
                        st.success("完成")
                    except Exception as e:
                        st.error(f"失敗：{e}")
                st.rerun()

        with st.expander("🔄 更新資料 / 資料新鮮度"):
            if st.button("從 TWSE 補抓缺漏日期", width="stretch"):
                st.cache_data.clear()
                with st.spinner("補抓中..."):
                    _, all_tickers, _, _ = cached_load_universe(tier)  # noqa: cache hit
                    _ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    try:
                        all_dates = ensure_calendar(start_date, end_date)
                        ensure_data(all_dates, no_fetch=False, all_tickers=all_tickers)
                        st.session_state["last_update"] = {
                            "ok": True, "tier": tier_label_sel,
                            "start": start_date.strftime("%Y-%m-%d"),
                            "end": end_date.strftime("%Y-%m-%d"), "ts": _ts,
                        }
                    except Exception as e:
                        st.session_state["last_update"] = {
                            "ok": False, "tier": tier_label_sel,
                            "start": start_date.strftime("%Y-%m-%d"),
                            "end": end_date.strftime("%Y-%m-%d"), "ts": _ts, "err": str(e),
                        }
                st.rerun()

            if "last_update" in st.session_state:
                _u = st.session_state["last_update"]
                if _u["ok"]:
                    st.success(
                        f"✅ 成功　｜　{_u['tier']}\n\n"
                        f"📅 {_u['start']} ～ {_u['end']}\n\n"
                        f"🕐 {_u['ts']}"
                    )
                else:
                    st.error(
                        f"❌ 失敗　｜　{_u['tier']}\n\n"
                        f"📅 {_u['start']} ～ {_u['end']}\n\n"
                        f"🕐 {_u['ts']}\n\n錯誤：{_u['err']}"
                    )

            _latest = _cached_latest_date()
            if _latest:
                _latest_dt = datetime.strptime(_latest, "%Y-%m-%d").date()
                _lag = (_today - _latest_dt).days
                _lag_str = f"（{_lag} 天前）" if _lag > 0 else "（今日）"
                _color = "🟢" if _lag <= 1 else ("🟡" if _lag <= 3 else "🔴")
                st.caption(f"{_color} 最新資料：**{_latest}** {_lag_str}")
            else:
                st.caption("⚪ 資料庫無資料")

        return SidebarParams(
            start_date=start_date,
            end_date=end_date,
            institution_label=institution_label,
            institution=institution,
            unit_label=unit_label,
            unit=unit,
            tier_label_sel=tier_label_sel,
            tier=tier,
            split_label=split_label,
            split=split,
            selected_cats=_selected_cats,
            margin_auto=_margin_auto,
            broker_auto=_broker_auto,
            fut_auto=_fut_auto,
        )


@dataclass(frozen=True)
class AppData:
    period_labels: list[str]
    cat_list: list[str]
    period_data: dict[str, dict]
    missing_labels: list[str]
    universe_cats: dict
    all_tickers: list[str]
    ticker_to_cat: dict
    missing_set: set[str]
    active_tickers: set[str]
    trading_dates: list[str]
    unit_suffix: str
    unit_fmt: str
    cat_colors: dict[str, str]
    cat_rgba_015: dict[str, str]
    coverage_json: str
    period_net: list[float]
    panel_tab1: str
    panel_tab2: str
    panel_tab3: str
    panel_tab4: str


def load_app_data(params: SidebarParams) -> AppData:
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state["db_initialized"] = True

    start_str = params.start_date.strftime("%Y-%m-%d")
    end_str = params.end_date.strftime("%Y-%m-%d")
    auto_key = f"auto_fetch_{start_str}_{end_str}_{params.tier}"
    if auto_key not in st.session_state:
        st.session_state[auto_key] = True
        _, auto_tickers, _, _ = cached_load_universe(params.tier)
        try:
            auto_dates = ensure_calendar(params.start_date, params.end_date)
            _, fetched_count = ensure_data(auto_dates, no_fetch=False, all_tickers=auto_tickers)
            if params.margin_auto:
                ensure_margin_data(auto_dates, auto_tickers, no_fetch=False)
            if auto_dates:
                ensure_qfii_data([auto_dates[-1]], auto_tickers, no_fetch=False)
            if params.fut_auto:
                ensure_futures_data(auto_dates, ["TXF", "EXF"], no_fetch=False)
            try:
                ensure_tdcc_data(auto_tickers, no_fetch=False)
            except Exception:
                pass
            if fetched_count > 0:
                st.cache_data.clear()
        except Exception:
            pass

    with st.spinner("載入資料..."):
        period_labels, cat_list, period_data, missing_labels = load_data(
            start_str, end_str, params.split, params.tier, params.institution, params.unit
        )

    universe_cats, all_tickers, ticker_to_cat, _ = cached_load_universe(params.tier)

    unit_suffix = {"shares": "股", "value_thousand": "千元", "value_oku": "億"}.get(params.unit, "股")
    unit_fmt = ",.2f" if params.unit == "value_oku" else ",.0f"

    if params.selected_cats:
        cat_list = [c for c in cat_list if c in params.selected_cats]
        period_data = {c: period_data[c] for c in cat_list}

    missing_set: set[str] = set(missing_labels)
    active_tickers: set[str] = {
        tk for cat in cat_list for tk in universe_cats.get(cat, {}).keys()
    }
    trading_dates = load_trading_dates(params.start_date, params.end_date)

    if cat_list:
        raw_matrix = np.array([period_data[cat]["raw"] for cat in cat_list])
        period_net = raw_matrix.sum(axis=0).tolist()
        coverage_by_period = (raw_matrix != 0).mean(axis=0).tolist()
    else:
        period_net = [0.0] * len(period_labels)
        coverage_by_period = [0.0] * len(period_labels)

    coverage_json = json.dumps(
        {period_labels[i]: coverage_by_period[i] for i in range(len(period_labels))},
        ensure_ascii=False,
    )

    cat_colors = {cat: COLORS.get(cat, DEFAULT_COLOR) for cat in cat_list}
    cat_rgba_015: dict[str, str] = {
        cat: "rgba({},{},{},0.15)".format(
            int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
        )
        for cat, c in cat_colors.items()
    }

    panel_tab1 = build_panel_data("tab1", period_labels, cat_list, period_data)
    panel_tab2 = build_panel_data("tab2", period_labels, cat_list, period_data)
    panel_tab3 = build_panel_data("tab3", period_labels, cat_list, period_data)
    panel_tab4 = build_panel_data("tab4", period_labels, cat_list, period_data)

    return AppData(
        period_labels=period_labels,
        cat_list=cat_list,
        period_data=period_data,
        missing_labels=missing_labels,
        universe_cats=universe_cats,
        all_tickers=all_tickers,
        ticker_to_cat=ticker_to_cat,
        missing_set=missing_set,
        active_tickers=active_tickers,
        trading_dates=trading_dates,
        unit_suffix=unit_suffix,
        unit_fmt=unit_fmt,
        cat_colors=cat_colors,
        cat_rgba_015=cat_rgba_015,
        coverage_json=coverage_json,
        period_net=period_net,
        panel_tab1=panel_tab1,
        panel_tab2=panel_tab2,
        panel_tab3=panel_tab3,
        panel_tab4=panel_tab4,
    )


def main() -> None:
    params = render_sidebar()
    data = load_app_data(params)
    ctx = TabContext(params=params, data=data)

    st.title("主力資金類股輪動")
    st.caption(
        f"{params.tier_label_sel}（{len(data.all_tickers)} 檔）　｜　"
        f"{params.institution_label}　｜　{params.split_label}分組　｜　{params.unit_label}　｜　"
        f"{params.start_date:%Y-%m-%d} ～ {params.end_date:%Y-%m-%d}"
    )

    if not data.period_labels:
        st.warning("選定區間無交易資料，請稍候自動補抓中...")
        st.stop()

    render_alerts(ctx)
    st.divider()
    render_scrubber(ctx)

    tab_labels = [
        "📊 資金強度佔比",
        "📈 累積買賣超（倉位變化）",
        "📉 每期買賣超量體",
        "🔀 三大法人對比",
        "📋 輪動摘要",
    ]
    if params.margin_auto:
        tab_labels.append("💳 散戶情緒（融資融券）")
    if params.broker_auto:
        tab_labels.append("🏦 券商動向")
    if params.fut_auto:
        tab_labels.append("📈 期現連動")
    tabs = st.tabs(tab_labels)
    tab1, tab2, tab3, tab4, tab5 = tabs[:5]
    tab_idx = 5
    tab6 = tabs[tab_idx] if params.margin_auto else None
    if params.margin_auto:
        tab_idx += 1
    tab7 = tabs[tab_idx] if params.broker_auto else None
    if params.broker_auto:
        tab_idx += 1
    tab8 = tabs[tab_idx] if params.fut_auto else None

    with tab1:
        render_tab1(ctx)

    with tab2:
        render_tab2(ctx)

    with tab3:
        render_tab3(ctx)

    with tab4:
        render_tab4(ctx)

    with tab5:
        render_tab5(ctx)

    if tab6 is not None:
        with tab6:
            render_tab6(ctx)

    if tab7 is not None:
        with tab7:
            render_tab7(ctx)

    if tab8 is not None:
        with tab8:
            render_tab8(ctx)

    render_detail(ctx)


main()
