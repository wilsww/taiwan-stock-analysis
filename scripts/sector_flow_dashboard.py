#!/usr/bin/env python3
"""
sector_flow_dashboard.py — 主力資金類股輪動 Streamlit 儀表板

啟動：streamlit run scripts/sector_flow_dashboard.py
"""

import sys
import json
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent

import sqlite3
from datetime import date, timedelta, datetime

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

# Delay local path injection until after third-party imports so sibling files
# cannot accidentally shadow installed packages such as numpy/pandas.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from sector_flow import (
    load_universe,
    init_db,
    trading_dates_in_range,
    split_into_periods,
    load_from_db,
    ensure_data,
    ensure_calendar,
    aggregate_by_category,
    load_margin_from_db,
    ensure_margin_data,
    load_broker_from_db,
    fetch_broker_today,
    load_qfii_from_db,
    ensure_qfii_data,
    load_futures_from_db,
    ensure_futures_data,
    load_tdcc_latest,
    ensure_tdcc_data,
    UNIVERSE_PATH,
    DB_PATH,
)

# ── 顏色常數 ─────────────────────────────────────────────────
POS_COLOR = "#ef4444"
NEG_COLOR = "#22c55e"
NEU_COLOR = "#94a3b8"

# ── 顏色方案（去除重複 key）───────────────────────────────────
COLORS: dict[str, str] = {
    "HBM/DRAM 記憶體": "#3b82f6",
    "DRAM 記憶體":     "#3b82f6",
    "先進封裝 CoWoS":  "#8b5cf6",
    "ABF 載板":        "#06b6d4",
    "IC 載板 PCB":     "#06b6d4",
    "CPO 光源核心":    "#f59e0b",
    "CPO 光通訊核心":  "#f59e0b",
    "CPO 光通周邊":    "#f97316",
    "CPO 光通訊周邊":  "#f97316",
    "AI 散熱/電源":    "#ef4444",
    "伺服器 ODM":      "#10b981",
    "網通基礎設施":    "#84cc16",
    "矽晶圓/材料":     "#94a3b8",
    "晶圓代工":        "#60a5fa",
    "IC 設計 AI":      "#a78bfa",
    "PCB 傳統":        "#34d399",
    "航運":            "#fb923c",
    "金融":            "#f87171",
}
DEFAULT_COLOR = "#64748b"

INSTITUTION_MAP = {
    "合計": "total",
    "外資": "foreign",
    "投信": "invest",
    "自營": "dealer",
}

UNIT_MAP = {
    "金額（億元）": "value_oku",
    "股數":         "shares",
    "金額（千元）": "value_thousand",
}

TIER_MAP = {
    "AI 供應鏈精選": "ai_supply_chain",
    "台股廣義主題":  "broad_themes",
    "全部":          "all",
}

SPLIT_MAP = {
    "月份": "month",
    "週":   "week",
    "天":   "day",
    "全期": "none",
}

LAYOUT_BASE = dict(
    template="plotly_white",
    paper_bgcolor="#f1f5f9",
    plot_bgcolor="#f8fafc",
    hovermode="x",
    font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif", color="#1e293b"),
    legend=dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        bgcolor="rgba(241,245,249,0.85)",
        entrywidth=120,
        entrywidthmode="pixels",
    ),
    margin=dict(t=80, b=40, l=60, r=20),
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


# ── 快取 load_universe ────────────────────────────────────────
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


# ── 資料載入 ─────────────────────────────────────────────────
def _unit_scale(unit: str) -> float:
    """將 DB 原始值縮放為顯示單位。
    DB: shares（原始股數）, *_value（千元）。
    unit='shares'      → 回傳 1（直接顯示股數）
    unit='value_thousand'→ 1（顯示千元）
    unit='value_oku'   → 1/1e5（千元 → 億元）
    """
    if unit == "value_oku":
        return 1 / 1e5
    return 1.0


def _key_for_unit(base: str, unit: str) -> str:
    """依 unit 決定要從 agg 取哪個欄位。
    base='foreign'|'invest'|'dealer'|'total'
    shares → base（股數）
    value_* → base + '_value'（千元）
    """
    if unit == "shares":
        return base
    return f"{base}_value"


@st.cache_data(ttl=3600)
def load_data(
    start_str: str,
    end_str: str,
    split: str,
    tier: str,
    institution: str,
    unit: str = "value_oku",
) -> tuple[list, list, dict, list]:
    categories, all_tickers, ticker_to_cat, _ = cached_load_universe(tier)
    start_dt = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_dt   = datetime.strptime(end_str,   "%Y-%m-%d").date()

    all_dates = trading_dates_in_range(start_dt, end_dt)
    if not all_dates:
        return [], list(categories.keys()), {}, []

    date_groups     = split_into_periods(all_dates, split)
    db_data         = load_from_db(all_dates)
    dates_with_data = set(d for _, d in db_data.keys())

    period_labels  = [label for label, _ in date_groups]
    cat_list       = list(categories.keys())
    missing_labels: list[str] = []

    period_data: dict[str, dict] = {
        cat: {"raw": [], "pos": [], "cumsum": [],
              "foreign": [], "invest": [], "dealer": []} for cat in cat_list
    }

    running: dict[str, float] = {cat: 0.0 for cat in cat_list}
    scale   = _unit_scale(unit)
    main_k  = _key_for_unit(institution, unit)
    fk      = _key_for_unit("foreign",   unit)
    ik      = _key_for_unit("invest",    unit)
    dk      = _key_for_unit("dealer",    unit)

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


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.title("控制面板")

    st.subheader("📅 日期區間")
    _today = date.today()
    _quick_cols = st.columns(4)
    _quick_map = {"30天": 30, "90天": 90, "半年": 180, "今年": None}
    for _i, (_ql, _qv) in enumerate(_quick_map.items()):
        if _quick_cols[_i].button(_ql, use_container_width=True, key=f"quick_{_ql}"):
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
        if _broker_auto and st.button("📥 抓取今日分點（HiStock）", use_container_width=True):
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
        if _margin_auto and st.button("🔄 補抓融資融券", use_container_width=True):
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
        if st.button("從 TWSE 補抓缺漏日期", use_container_width=True):
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
            _today = date.today()
            _latest_dt = datetime.strptime(_latest, "%Y-%m-%d").date()
            _lag = (_today - _latest_dt).days
            _lag_str = f"（{_lag} 天前）" if _lag > 0 else "（今日）"
            _color = "🟢" if _lag <= 1 else ("🟡" if _lag <= 3 else "🔴")
            st.caption(f"{_color} 最新資料：**{_latest}** {_lag_str}")
        else:
            st.caption("⚪ 資料庫無資料")


# ── 讀取資料 ─────────────────────────────────────────────────
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True
start_str = start_date.strftime("%Y-%m-%d")
end_str   = end_date.strftime("%Y-%m-%d")

_auto_key = f"auto_fetch_{start_str}_{end_str}_{tier}"
if _auto_key not in st.session_state:
    st.session_state[_auto_key] = True
    _, _auto_tickers, _, _ = cached_load_universe(tier)  # cache hit
    try:
        _auto_dates = ensure_calendar(start_date, end_date)
        _, _fetched_count = ensure_data(_auto_dates, no_fetch=False, all_tickers=_auto_tickers)
        if _margin_auto:
            ensure_margin_data(_auto_dates, _auto_tickers, no_fetch=False)
        # QFII 只抓最後一天（比例變化慢）
        if _auto_dates:
            ensure_qfii_data([_auto_dates[-1]], _auto_tickers, no_fetch=False)
        if _fut_auto:
            ensure_futures_data(_auto_dates, ["TXF", "EXF"], no_fetch=False)
        # TDCC 大戶（週資料，自行判斷是否需抓）
        try:
            ensure_tdcc_data(_auto_tickers, no_fetch=False)
        except Exception:
            pass
        if _fetched_count > 0:
            st.cache_data.clear()
    except Exception:
        pass

with st.spinner("載入資料..."):
    period_labels, cat_list, period_data, missing_labels = load_data(
        start_str, end_str, split, tier, institution, unit
    )

_, all_tickers, _, _ = cached_load_universe(tier)  # cache hit; tier_label_sel used in caption
st.title("主力資金類股輪動")
st.caption(
    f"{tier_label_sel}（{len(all_tickers)} 檔）　｜　"
    f"{institution_label}　｜　{split_label}分組　｜　{unit_label}　｜　"
    f"{start_str} ～ {end_str}"
)

# 單位顯示字尾（供 hover panel JS / 軸標籤使用）
UNIT_SUFFIX = {"shares": "股", "value_thousand": "千元", "value_oku": "億"}
_unit_suffix = UNIT_SUFFIX.get(unit, "股")
# 數值格式：億元用 1 位小數，其他整數
_unit_fmt = ".2f" if unit == "value_oku" else ",.0f"

if not period_labels:
    st.warning("選定區間無交易資料，請稍候自動補抓中...")
    st.stop()

if _selected_cats:
    cat_list    = [c for c in cat_list if c in _selected_cats]
    period_data = {c: period_data[c] for c in cat_list}

# ── 警示摘要區 ──────────────────────────────────────────────
def _render_alerts():
    _a1, _a2, _a3, _a4 = st.columns(4)

    # 1. 最新期外資買超前 3 類股
    _latest_idx = -1
    _latest_fgn = [(cat, period_data[cat]["foreign"][_latest_idx]) for cat in cat_list]
    _latest_fgn.sort(key=lambda x: x[1], reverse=True)
    _top_fgn = _latest_fgn[:3]
    _latest_label = period_labels[_latest_idx] if period_labels else "—"
    _a1.markdown(f"**🏦 最新期外資買超 TOP3** _({_latest_label})_")
    for cat, v in _top_fgn:
        _color = POS_COLOR if v > 0 else NEG_COLOR
        _a1.markdown(
            f'<span style="color:{_color};font-weight:600">{cat}：'
            f'{v:+,.2f} {_unit_suffix}</span>',
            unsafe_allow_html=True,
        )

    # 2. 連續買超類股數（以當前 institution 值）
    _streak_cats = []
    for cat in cat_list:
        raw = period_data[cat]["raw"]
        streak = 0
        for v in reversed(raw):
            if v > 0:
                streak += 1
            else:
                break
        if streak >= 3:
            _streak_cats.append((cat, streak))
    _a2.metric("🔥 連續 ≥3 期買超類股", f"{len(_streak_cats)} 類")
    if _streak_cats:
        _a2.caption("、".join(f"{c}({s})" for c, s in _streak_cats[:3]))

    # 3. 融資/法人背離天數（若已抓 margin）
    if _margin_auto:
        try:
            _m_db = load_margin_from_db(
                trading_dates_in_range(
                    datetime.strptime(start_str, "%Y-%m-%d").date(),
                    datetime.strptime(end_str,   "%Y-%m-%d").date(),
                )
            )
            if _m_db:
                _universe_cats_a, _, _, _ = cached_load_universe(tier)
                _active_tkrs_a = {tk for cat in cat_list
                                  for tk in _universe_cats_a.get(cat, {}).keys()}
                _by_date_a = {}
                for (tk, dt), v in _m_db.items():
                    if tk not in _active_tkrs_a:
                        continue
                    slot = _by_date_a.setdefault(dt, [0, 0])
                    slot[0] += (v.get("margin_balance", 0) or 0) - (v.get("margin_prev", 0) or 0)
                _div = 0
                for dt in sorted(_by_date_a.keys()):
                    m_chg = _by_date_a[dt][0]
                    # 當日法人合計（股）
                    i_db = load_from_db([dt])
                    i_net = sum(v.get("total", 0) for (tk, _d), v in i_db.items() if tk in _active_tkrs_a)
                    if (m_chg > 0 and i_net < 0) or (m_chg < 0 and i_net > 0):
                        _div += 1
                _a3.metric("📊 融資-法人 背離天數", f"{_div}")
            else:
                _a3.metric("📊 融資-法人 背離", "—")
        except Exception:
            _a3.metric("📊 融資-法人 背離", "—")
    else:
        _a3.metric("📊 融資-法人 背離", "未啟用")
        _a3.caption("左側啟用融資融券顯示")

    # 4. 外資持股接近上限（剩 <5%）標的數
    _universe_cats_q, _, _, _ = cached_load_universe(tier)
    _active_tkrs_q = {tk for cat in cat_list for tk in _universe_cats_q.get(cat, {}).keys()}
    _qdates = trading_dates_in_range(
        datetime.strptime(start_str, "%Y-%m-%d").date(),
        datetime.strptime(end_str,   "%Y-%m-%d").date(),
    )
    _near_limit = []
    if _qdates:
        _q_db = load_qfii_from_db([_qdates[-1]])
        for (tk, _dt), v in _q_db.items():
            if tk in _active_tkrs_q and v.get("remaining_pct", 100) < 5:
                _near_limit.append((tk, v.get("remaining_pct", 0)))
    _a4.metric("⚠️ 外資接近上限（剩<5%）", f"{len(_near_limit)} 檔")
    if _near_limit:
        _near_limit.sort(key=lambda x: x[1])
        _a4.caption("、".join(f"{t}({p:.1f}%)" for t, p in _near_limit[:3]))

_render_alerts()
st.divider()

# ── 時間軸回放（scrubber）──────────────────────────────────
with st.expander("⏮️ 時間軸回放（單期 snapshot）"):
    _scrub_idx = st.slider(
        "選擇期間",
        min_value=0, max_value=len(period_labels) - 1,
        value=len(period_labels) - 1,
        format="%d",
    )
    _scrub_label = period_labels[_scrub_idx]
    st.caption(f"📅 **{_scrub_label}**")

    # 該期類股橫向長條
    _scrub_vals = [(cat, period_data[cat]["raw"][_scrub_idx]) for cat in cat_list]
    _scrub_vals.sort(key=lambda x: x[1], reverse=True)
    _sc_cats = [c for c, _ in _scrub_vals]
    _sc_data = [v for _, v in _scrub_vals]
    _sc_colors = [POS_COLOR if v > 0 else NEG_COLOR for v in _sc_data]
    fig_scrub = go.Figure(go.Bar(
        x=_sc_data, y=_sc_cats, orientation="h",
        marker_color=_sc_colors,
        text=[f"{v:+,.2f}" if unit == "value_oku" else f"{v:+,.0f}" for v in _sc_data],
        textposition="outside",
        hovertemplate="%{y}<br>%{x:+,.2f}<extra></extra>",
    ))
    fig_scrub.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
        height=max(300, len(cat_list) * 30 + 80),
        xaxis=dict(title=f"當期 {institution_label} 買賣超（{_unit_suffix}）",
                   tickformat=",.2f" if unit == "value_oku" else ",",
                   gridcolor="#cbd5e1",
                   zeroline=True, zerolinecolor="#94a3b8"),
        yaxis=dict(autorange="reversed", gridcolor="#cbd5e1"),
        showlegend=False,
    )
    st.plotly_chart(fig_scrub, use_container_width=True)

if cat_list:
    _raw_matrix = np.array([period_data[cat]["raw"] for cat in cat_list])  # (n_cats, n_periods)
    period_net = _raw_matrix.sum(axis=0).tolist()
    coverage_by_period = (_raw_matrix != 0).mean(axis=0).tolist()
else:
    period_net = [0.0] * len(period_labels)
    coverage_by_period = [0.0] * len(period_labels)

# 預先序列化一次，避免 render_chart_with_panel 重複建構
_coverage_json = json.dumps(
    {period_labels[i]: coverage_by_period[i] for i in range(len(period_labels))},
    ensure_ascii=False,
)


# ── 共用：加無資料標記 ───────────────────────────────────────
def add_missing_markers(fig, missing_labels, period_labels, split):
    for lbl in missing_labels:
        if split == "day":
            fig.add_shape(
                type="line",
                x0=lbl, x1=lbl, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(width=1, dash="dot", color="rgba(148,163,184,0.6)"),
            )
            fig.add_annotation(
                x=lbl, y=1, yref="paper",
                text="無資料", showarrow=False,
                font=dict(size=8, color="rgba(148,163,184,0.8)"),
                yanchor="bottom",
            )
        else:
            idx = period_labels.index(lbl) if lbl in period_labels else None
            if idx is not None:
                fig.add_vrect(
                    x0=idx - 0.4, x1=idx + 0.4,
                    fillcolor="rgba(148,163,184,0.15)", line_width=0,
                )


# ── 共用輔助：數字格式化 ─────────────────────────────────────
def _color_num(v: float) -> str:
    if unit == "value_oku":
        txt_pos = f"{v:+,.2f} {_unit_suffix}"
        txt_zero = f"0 {_unit_suffix}"
    else:
        txt_pos = f"{v:+,.0f} {_unit_suffix}"
        txt_zero = f"0 {_unit_suffix}"
    if v > 0:
        return f'<span style="color:{POS_COLOR};font-weight:600">{txt_pos}</span>'
    elif v < 0:
        return f'<span style="color:{NEG_COLOR};font-weight:600">{txt_pos}</span>'
    return f'<span style="color:{NEU_COLOR}">{txt_zero}</span>'

def _style_num_col(val) -> str:
    try:
        v = float(val)
        if v > 0:   return f"color: {POS_COLOR}; font-weight: 600"
        elif v < 0: return f"color: {NEG_COLOR}; font-weight: 600"
        return f"color: {NEU_COLOR}"
    except Exception:
        return ""


# ── 共用：產生帶 hover panel 的 HTML component ───────────────
def render_chart_with_panel(
    fig,
    panel_data_json: str,
    tab_mode: str,
    cat_colors: dict,
    height: int = 500,
    n_cats: int = 0,
    coverage_json: str = "{}",
) -> None:
    fig_json = fig.to_json()

    # 動態 iframe 高度：panel 高度依類股數計算
    if tab_mode == "tab4":
        panel_h = 80
    else:
        row_h = 52
        panel_h = max(80, min(n_cats * row_h + 40, 320))
    total_h = height + panel_h + 20

    _is_oku = "true" if unit == "value_oku" else "false"
    panel_js = f"""
    var POS_COLOR = '{POS_COLOR}';
    var NEG_COLOR = '{NEG_COLOR}';
    var NEU_COLOR = '{NEU_COLOR}';
    var UNIT_SUFFIX = '{_unit_suffix}';
    var IS_OKU = {_is_oku};
    function formatVal(v) {{
        if (IS_OKU) {{
            return (v >= 0 ? '+' : '') + v.toLocaleString('zh-TW', {{minimumFractionDigits:2, maximumFractionDigits:2}});
        }}
        return (v >= 0 ? '+' : '') + Math.round(v).toLocaleString('zh-TW');
    }}
    function fmtNum(v) {{
        if (v === 0) return '<span style="color:' + NEU_COLOR + '">0 ' + UNIT_SUFFIX + '</span>';
        var color = v > 0 ? POS_COLOR : NEG_COLOR;
        return '<span style="color:' + color + '">' + formatVal(v) + ' ' + UNIT_SUFFIX + '</span>';
    }}
    function fmtSub(v, label) {{
        if (v === 0) return '<span style="color:' + NEU_COLOR + '">' + label + '：0</span>';
        var color = v > 0 ? POS_COLOR : NEG_COLOR;
        return label + '：<span style="color:' + color + '">' + formatVal(v) + '</span>';
    }}
    """

    if tab_mode == "tab1":
        build_panel_js = """
        function buildPanel(label, panelData, catColors, coverage) {
            var cats = Object.keys(panelData[label] || {});
            if (!cats.length) return '<div style="color:#94a3b8">無資料</div>';
            cats.sort(function(a,b){ return (panelData[label][b].pos||0) - (panelData[label][a].pos||0); });
            var totalAbs = cats.reduce(function(s,c){ return s + (panelData[label][c].pos||0); }, 0);
            var html = '';
            cats.forEach(function(cat) {
                var d = panelData[label][cat];
                var raw = d.raw || 0;
                var pct = totalAbs > 0 ? (d.pos / totalAbs * 100).toFixed(1) : '0.0';
                var color = catColors[cat] || '#64748b';
                html += '<div style="margin-bottom:6px;padding:4px 8px;border-left:3px solid '+color+';background:rgba(255,255,255,0.6);border-radius:3px">';
                html += '<div style="font-weight:600;font-size:13px">'+cat+'</div>';
                html += '<div style="font-size:12px;margin-top:2px">買賣超：' + fmtNum(raw) + '　強度佔比：<b>'+pct+'%</b></div>';
                html += '<div style="font-size:11px;color:#475569;margin-top:2px">';
                html += fmtSub(d.foreign||0,'外資') + '　' + fmtSub(d.invest||0,'投信') + '　' + fmtSub(d.dealer||0,'自營');
                html += '</div></div>';
            });
            return html;
        }
        """
    elif tab_mode == "tab2":
        build_panel_js = """
        function buildPanel(label, panelData, catColors, coverage) {
            var cats = Object.keys(panelData[label] || {});
            if (!cats.length) return '<div style="color:#94a3b8">無資料</div>';
            cats.sort(function(a,b){ return Math.abs(panelData[label][b].cumsum||0) - Math.abs(panelData[label][a].cumsum||0); });
            var html = '';
            cats.forEach(function(cat) {
                var d = panelData[label][cat];
                var color = catColors[cat] || '#64748b';
                html += '<div style="margin-bottom:6px;padding:4px 8px;border-left:3px solid '+color+';background:rgba(255,255,255,0.6);border-radius:3px">';
                html += '<div style="font-weight:600;font-size:13px">'+cat+'</div>';
                html += '<div style="font-size:12px;margin-top:2px">累積買賣超：' + fmtNum(d.cumsum||0) + '　本期：' + fmtNum(d.raw||0) + '</div>';
                html += '<div style="font-size:11px;color:#475569;margin-top:2px">';
                html += fmtSub(d.foreign||0,'外資') + '　' + fmtSub(d.invest||0,'投信') + '　' + fmtSub(d.dealer||0,'自營');
                html += '</div></div>';
            });
            return html;
        }
        """
    elif tab_mode == "tab3":
        build_panel_js = """
        function buildPanel(label, panelData, catColors, coverage) {
            var cats = Object.keys(panelData[label] || {});
            if (!cats.length) return '<div style="color:#94a3b8">無資料</div>';
            cats.sort(function(a,b){ return Math.abs(panelData[label][b].raw||0) - Math.abs(panelData[label][a].raw||0); });
            var total = cats.reduce(function(s,c){ return s + (panelData[label][c].raw||0); }, 0);
            var totalColor = total > 0 ? POS_COLOR : (total < 0 ? NEG_COLOR : NEU_COLOR);
            var html = '<div style="margin-bottom:8px;padding:4px 8px;background:#e2e8f0;border-radius:3px;font-size:12px">';
            html += '整體合計：<span style="color:'+totalColor+';font-weight:700">'+formatVal(total)+' '+UNIT_SUFFIX+'</span></div>';
            cats.forEach(function(cat) {
                var d = panelData[label][cat];
                var raw = d.raw || 0;
                var color = catColors[cat] || '#64748b';
                html += '<div style="margin-bottom:6px;padding:4px 8px;border-left:3px solid '+color+';background:rgba(255,255,255,0.6);border-radius:3px">';
                html += '<div style="font-weight:600;font-size:13px">'+cat+'</div>';
                html += '<div style="font-size:12px;margin-top:2px">買賣超：' + fmtNum(raw) + '</div>';
                html += '<div style="font-size:11px;color:#475569;margin-top:2px">';
                html += fmtSub(d.foreign||0,'外資') + '　' + fmtSub(d.invest||0,'投信') + '　' + fmtSub(d.dealer||0,'自營');
                html += '</div></div>';
            });
            return html;
        }
        """
    else:  # tab4
        build_panel_js = """
        function buildPanel(label, panelData, catColors, coverage) {
            var d = panelData[label];
            if (!d) return '<div style="color:#94a3b8">無資料</div>';
            var foreign = d.foreign || 0;
            var invest  = d.invest  || 0;
            var dealer  = d.dealer  || 0;
            var total   = foreign + invest + dealer;
            function fmtRow(v, lbl, color) {
                var c = v > 0 ? POS_COLOR : (v < 0 ? NEG_COLOR : NEU_COLOR);
                return '<div style="padding:3px 8px;border-left:3px solid '+color+';background:rgba(255,255,255,0.6);border-radius:3px;flex:1;min-width:90px">'
                     + '<div style="font-weight:600;font-size:11px;color:#475569">'+lbl+'</div>'
                     + '<div style="font-size:12px;font-weight:700;color:'+c+'">'+formatVal(v)+' '+UNIT_SUFFIX+'</div>'
                     + '</div>';
            }
            var totalColor = total > 0 ? POS_COLOR : (total < 0 ? NEG_COLOR : NEU_COLOR);
            var html = '<div style="display:inline-flex;align-items:center;gap:6px;margin-bottom:5px;padding:2px 8px;background:#e2e8f0;border-radius:3px;font-size:11px;flex-wrap:wrap">';
            html += '<span>三大法人合計：</span><span style="color:'+totalColor+';font-weight:700">'+formatVal(total)+' '+UNIT_SUFFIX+'</span></div>';
            html += '<div style="display:flex;gap:5px;flex-wrap:nowrap">';
            html += fmtRow(foreign, '外資', '#2563eb');
            html += fmtRow(invest,  '投信', '#8b5cf6');
            html += fmtRow(dealer,  '自營', '#f97316');
            html += '</div>';
            return html;
        }
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  body {{ margin:0; padding:0; background:#f1f5f9; font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif; }}
  #panel {{
    min-height: 40px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #1e293b;
    overflow: hidden;
  }}
  #panel-header {{
    font-size: 12px;
    color: #64748b;
    margin-bottom: 6px;
    font-weight: 600;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
  }}
  #panel-body {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  #panel-body > div {{
    flex: 1 1 200px;
    min-width: 180px;
    max-width: 280px;
  }}
  #panel-body.tab4-body > div {{
    flex: 1 1 0;
    min-width: 90px;
  }}
  #chart {{ width:100%; }}
  .hoverlayer .hovertext {{ display: none !important; }}
  .hoverlayer .spikeline {{ display: none !important; }}
</style>
</head>
<body>
<div id="panel">
  <div id="panel-header">&#8592; 滑鼠移至圖表查看各類股數據</div>
  <div id="panel-body"></div>
</div>
<div id="chart"></div>
<script>
var figData = {fig_json};
var panelData = {panel_data_json};
var catColors = {json.dumps(cat_colors)};
var coverageData = {coverage_json};

figData.data.forEach(function(trace) {{
    trace.hovertemplate = '%{{x}}<extra></extra>';
    delete trace.hoverinfo;
}});
figData.layout.hovermode = 'x';
var tabMode = '{tab_mode}';
// legend 由 Python 側各 tab 自行設定，JS 不覆寫

Plotly.newPlot('chart', figData.data, figData.layout, {{responsive: true, displayModeBar: false}});

{panel_js}
{build_panel_js}

var chartEl = document.getElementById('chart');
var panelHeader = document.getElementById('panel-header');
var panelBody = document.getElementById('panel-body');

if (tabMode === 'tab4') {{ panelBody.classList.add('tab4-body'); }}

function updatePanel(labelStr) {{
    var headerHtml = '<span>📅 ' + labelStr + '</span>';
    if (tabMode !== 'tab4' && coverageData[labelStr] !== undefined) {{
        var covPct = (coverageData[labelStr] * 100).toFixed(0) + '%';
        headerHtml += '<span style="float:right;font-weight:400;color:#64748b">資料覆蓋率：<b style="color:#1e293b">' + covPct + '</b></span>';
    }}
    panelHeader.innerHTML = headerHtml;
    panelBody.innerHTML = buildPanel(labelStr, panelData, catColors, coverageData);
}}

// 初始化：預設顯示最新（最右）期間資料，避免空白等待 hover
var _labels = Object.keys(panelData);
if (_labels.length) {{
    updatePanel(_labels[_labels.length - 1]);
}}

// 垂直追蹤線：以 shapes 畫一條 x 位置的 full-height 線
var VLINE_NAME = '__hover_vline__';
function setVLine(xVal) {{
    var layout = chartEl.layout || {{}};
    var shapes = (layout.shapes || []).filter(function(s) {{ return s.name !== VLINE_NAME; }});
    if (xVal !== null && xVal !== undefined) {{
        shapes.push({{
            name: VLINE_NAME,
            type: 'line',
            xref: 'x', yref: 'paper',
            x0: xVal, x1: xVal,
            y0: 0, y1: 1,
            line: {{ color: 'rgba(71,85,105,0.75)', width: 2.5, dash: 'dot' }},
            layer: 'above',
        }});
    }}
    Plotly.relayout(chartEl, {{shapes: shapes}});
}}

chartEl.on('plotly_hover', function(eventData) {{
    if (!eventData || !eventData.points || !eventData.points.length) return;
    var label = eventData.points[0].x;
    if (label === undefined || label === null) return;
    updatePanel(String(label));
    setVLine(label);
}});
chartEl.on('plotly_unhover', function() {{
    setVLine(null);
}});
</script>
</body>
</html>
"""
    components.html(html, height=total_h, scrolling=False)


# ── 建立 panel_data（各 Tab 共用）────────────────────────────
def build_panel_data(tab_mode: str) -> str:
    result = {}
    for i, label in enumerate(period_labels):
        if tab_mode == "tab4":
            result[label] = {
                "foreign": sum(period_data[c]["foreign"][i] for c in cat_list),
                "invest":  sum(period_data[c]["invest"][i]  for c in cat_list),
                "dealer":  sum(period_data[c]["dealer"][i]  for c in cat_list),
            }
        else:
            result[label] = {}
            for cat in cat_list:
                d = period_data[cat]
                if tab_mode == "tab2":
                    result[label][cat] = {
                        "raw":     d["raw"][i],
                        "cumsum":  d["cumsum"][i],
                        "foreign": d["foreign"][i],
                        "invest":  d["invest"][i],
                        "dealer":  d["dealer"][i],
                    }
                else:
                    result[label][cat] = {
                        "raw":     d["raw"][i],
                        "pos":     d["pos"][i],
                        "foreign": d["foreign"][i],
                        "invest":  d["invest"][i],
                        "dealer":  d["dealer"][i],
                    }
    return json.dumps(result, ensure_ascii=False)


cat_colors = {cat: COLORS.get(cat, DEFAULT_COLOR) for cat in cat_list}

# 一次建立所有 tab 的 panel_data JSON，避免每個 tab 重複計算
_panel_tab1 = build_panel_data("tab1")
_panel_tab2 = build_panel_data("tab2")
_panel_tab3 = build_panel_data("tab3")
_panel_tab4 = build_panel_data("tab4")


# ════════════════════════════════════════════════════════════
# TAB 切換
# ════════════════════════════════════════════════════════════
_tab_labels = [
    "📊 資金強度佔比",
    "📈 累積買賣超（倉位變化）",
    "📉 每期買賣超量體",
    "🔀 三大法人對比",
    "📋 輪動摘要",
]
if _margin_auto:
    _tab_labels.append("💳 散戶情緒（融資融券）")
if _broker_auto:
    _tab_labels.append("🏦 券商動向")
if _fut_auto:
    _tab_labels.append("📈 期現連動")
_tabs = st.tabs(_tab_labels)
tab1, tab2, tab3, tab4, tab5 = _tabs[:5]
_tab_idx = 5
tab6 = _tabs[_tab_idx] if _margin_auto else None
if _margin_auto: _tab_idx += 1
tab7 = _tabs[_tab_idx] if _broker_auto else None
if _broker_auto: _tab_idx += 1
tab8 = _tabs[_tab_idx] if _fut_auto else None


# ── Tab 1：資金強度佔比（100% 堆疊面積，abs）────────────────
with tab1:
    fig1 = go.Figure()
    _missing_set = set(missing_labels)

    for cat in cat_list:
        color    = cat_colors[cat]
        pos_vals = [
            None if lbl in _missing_set else v
            for lbl, v in zip(period_labels, period_data[cat]["pos"])
        ]
        fig1.add_trace(go.Scatter(
            x=period_labels, y=pos_vals,
            name=cat,
            stackgroup="one", groupnorm="percent",
            fill="tonexty",
            line=dict(width=0.5, color=color),
            fillcolor=color,
            opacity=0.85,
            connectgaps=False,
            hovertemplate="%{x}<extra></extra>",
        ))

    fig1.update_layout(
        **LAYOUT_BASE,
        height=500,
        yaxis=dict(ticksuffix="%", range=[0, 100], gridcolor="#cbd5e1"),
        xaxis=dict(gridcolor="#cbd5e1"),
    )
    add_missing_markers(fig1, missing_labels, period_labels, split)

    parts = ["面積高度 = 各類股買賣超絕對值佔比"]
    if missing_labels:
        parts.append(f"灰色虛線 = 開盤無資料（{len(missing_labels)} 天）")
    st.caption("　｜　".join(parts))

    render_chart_with_panel(fig1, _panel_tab1, "tab1", cat_colors, height=500, n_cats=len(cat_list), coverage_json=_coverage_json)


# ── Tab 2：累積買賣超（倉位趨勢河流圖）─────────────────────
with tab2:
    st.caption(
        "各類股每期買賣超累加，反映法人倉位變化趨勢。"
        "向上 = 持續買進加碼，向下 = 持續賣出減碼。"
    )

    fig2 = go.Figure()
    _missing_set2 = set(missing_labels)

    for cat in cat_list:
        color       = cat_colors[cat]
        cumsum_vals = [
            None if lbl in _missing_set2 else v
            for lbl, v in zip(period_labels, period_data[cat]["cumsum"])
        ]
        fig2.add_trace(go.Scatter(
            x=period_labels,
            y=cumsum_vals,
            name=cat,
            mode="lines",
            connectgaps=False,
            line=dict(width=1.5, color=color),
            fill="tozeroy",
            fillcolor="rgba({},{},{},0.15)".format(
                int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            ),
            hovertemplate="%{x}<extra></extra>",
        ))

    fig2.add_hline(y=0, line_width=1, line_color="#94a3b8", line_dash="dot")

    fig2.update_layout(
        **LAYOUT_BASE,
        height=500,
        yaxis=dict(
            title=f"累積買賣超（{_unit_suffix}）",
            gridcolor="#cbd5e1",
            tickformat=",.2f" if unit == "value_oku" else ",",
        ),
        xaxis=dict(gridcolor="#cbd5e1"),
    )
    add_missing_markers(fig2, missing_labels, period_labels, split)

    render_chart_with_panel(fig2, _panel_tab2, "tab2", cat_colors, height=500, n_cats=len(cat_list), coverage_json=_coverage_json)


# ── Tab 3：每期買賣超量體（正負 stacked bar）────────────────
with tab3:
    st.caption(
        "各類股每期買賣超股數，正值朝上（買超）、負值朝下（賣超）。"
        "顏色與其他圖表一致。"
    )

    fig3 = go.Figure()

    for cat in cat_list:
        color    = cat_colors[cat]
        raw_vals = period_data[cat]["raw"]
        pos = [v if v > 0 else 0 for v in raw_vals]
        neg = [v if v < 0 else 0 for v in raw_vals]

        shared = dict(
            x=period_labels, name=cat,
            marker_color=color,
            hovertemplate="%{x}<extra></extra>",
        )
        fig3.add_trace(go.Bar(**shared, y=pos, showlegend=True))
        fig3.add_trace(go.Bar(**shared, y=neg, showlegend=False, hoverinfo="skip"))

    # 整體合計線
    fig3.add_trace(go.Scatter(
        x=period_labels,
        y=period_net,
        name="整體合計",
        mode="lines+markers",
        line=dict(width=2, color="#1e293b", dash="dot"),
        marker=dict(size=4),
        hovertemplate=" <extra></extra>",
    ))

    # ±1σ 警示線（整體合計）
    if len(period_net) >= 3:
        _mean = np.mean(period_net)
        _std  = np.std(period_net)
        for _band_val, _band_name, _band_color in [
            (_mean + _std, "+1σ", "rgba(239,68,68,0.5)"),
            (_mean,        "均值", "rgba(100,116,139,0.6)"),
            (_mean - _std, "−1σ", "rgba(34,197,94,0.5)"),
        ]:
            fig3.add_hline(
                y=_band_val,
                line_width=1, line_dash="dash", line_color=_band_color,
                annotation_text=_band_name,
                annotation_position="right",
                annotation_font_size=10,
            )

    _layout3 = {**LAYOUT_BASE, "barmode": "relative", "height": 560,
                "margin": dict(t=100, b=40, l=60, r=40)}
    _layout3["legend"] = dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        bgcolor="rgba(241,245,249,0.85)",
        font=dict(size=11),
        entrywidth=110,
        entrywidthmode="pixels",
    )
    fig3.update_layout(
        **_layout3,
        yaxis=dict(
            title=f"買賣超（{_unit_suffix}）",
            gridcolor="#cbd5e1",
            tickformat=",.2f" if unit == "value_oku" else ",",
            zeroline=True, zerolinecolor="#94a3b8", zerolinewidth=1.5,
        ),
        xaxis=dict(gridcolor="#cbd5e1"),
    )
    add_missing_markers(fig3, missing_labels, period_labels, split)

    render_chart_with_panel(fig3, _panel_tab3, "tab3", cat_colors, height=560, n_cats=len(cat_list), coverage_json=_coverage_json)


# ── Tab 4：三大法人對比（grouped bar）───────────────────────
with tab4:
    st.caption("外資／投信／自營各期買賣超合計對比，觀察同步 / 背離。滑鼠移至圖表查看數據與億元估算。")

    _foreign_net = [sum(period_data[c]["foreign"][i] for c in cat_list) for i in range(len(period_labels))]
    _invest_net  = [sum(period_data[c]["invest"][i]  for c in cat_list) for i in range(len(period_labels))]
    _dealer_net  = [sum(period_data[c]["dealer"][i]  for c in cat_list) for i in range(len(period_labels))]

    fig4 = go.Figure()

    def _bar_trace(fig, vals, name, color, legendgroup):
        pos = [v if v > 0 else 0 for v in vals]
        neg = [v if v < 0 else 0 for v in vals]
        fig.add_trace(go.Bar(
            x=period_labels, y=pos, name=name,
            marker_color=color, opacity=0.85,
            legendgroup=legendgroup,
            hovertemplate="%{x}<extra></extra>",
        ))
        fig.add_trace(go.Bar(
            x=period_labels, y=neg, name=name,
            marker_color=color, opacity=0.4,
            legendgroup=legendgroup, showlegend=False,
            hovertemplate="%{x}<extra></extra>",
        ))

    _bar_trace(fig4, _foreign_net, "外資合計", "#2563eb", "foreign")
    _bar_trace(fig4, _invest_net,  "投信合計", "#8b5cf6", "invest")
    _bar_trace(fig4, _dealer_net,  "自營合計", "#f97316", "dealer")

    fig4.add_hline(y=0, line_width=1, line_color="#94a3b8", line_dash="dot")

    _layout4 = {
        **LAYOUT_BASE,
        "barmode": "overlay",
        "height": 520,
        "yaxis": dict(title=f"買賣超（{_unit_suffix}）",
                      tickformat=",.2f" if unit == "value_oku" else ",",
                      gridcolor="#cbd5e1"),
        "legend": dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            bgcolor="rgba(241,245,249,0.85)",
            font=dict(size=12),
            tracegroupgap=0,
            itemwidth=80,
            entrywidth=120,
            entrywidthmode="pixels",
        ),
        "margin": dict(t=80, b=40, l=60, r=80),
    }
    fig4.update_layout(**_layout4)
    fig4.update_xaxes(gridcolor="#cbd5e1")

    add_missing_markers(fig4, missing_labels, period_labels, split)
    render_chart_with_panel(fig4, _panel_tab4, "tab4", cat_colors, height=520, n_cats=0, coverage_json=_coverage_json)

    # 同步 / 背離統計
    if len(period_labels) >= 2:
        _sync = sum(1 for f, t in zip(_foreign_net, _invest_net) if (f > 0 and t > 0) or (f < 0 and t < 0))
        _div  = sum(1 for f, t in zip(_foreign_net, _invest_net) if (f > 0 and t < 0) or (f < 0 and t > 0))
        _total_periods = len([f for f, t in zip(_foreign_net, _invest_net) if f != 0 or t != 0])
        if _total_periods > 0:
            _c1, _c2, _c3 = st.columns(3)
            _c1.metric("同向操作期數", f"{_sync}")
            _c2.metric("背離操作期數", f"{_div}")
            _c3.metric("同向率", f"{_sync/_total_periods*100:.0f}%" if _total_periods else "—")


# ── Tab 5：輪動摘要 ──────────────────────────────────────────
with tab5:
    if len(period_labels) < 2:
        st.info("需要至少 2 個期間才能顯示輪動摘要。請擴大日期區間或換用較細的時間分組。")
    else:
        # ── 輪動摘要 ──────────────────────────────────────────
        st.subheader("輪動摘要")
        first_vals = {cat: period_data[cat]["raw"][0]  for cat in cat_list}
        last_vals  = {cat: period_data[cat]["raw"][-1] for cat in cat_list}

        diffs = {cat: last_vals[cat] - first_vals[cat] for cat in cat_list}
        gainers = sorted([(c, d) for c, d in diffs.items() if d > 0], key=lambda x: x[1], reverse=True)
        losers  = sorted([(c, d) for c, d in diffs.items() if d < 0], key=lambda x: x[1])

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**▲ 資金流入（相較首期）**")
            for cat, diff in gainers[:5]:
                st.markdown(f"- {cat}：{_color_num(diff)}", unsafe_allow_html=True)
            if not gainers:
                st.markdown("- 無明顯流入")
        with col2:
            st.markdown("**▼ 資金流出（相較首期）**")
            for cat, diff in losers[:5]:
                st.markdown(f"- {cat}：{_color_num(diff)}", unsafe_allow_html=True)
            if not losers:
                st.markdown("- 無明顯流出")

        if gainers and losers:
            st.info(f"**資金移轉方向：** {losers[0][0]} → {gainers[0][0]}")

        # ── 資金動能評分 ──────────────────────────────────────
        st.subheader("資金動能評分")
        st.caption("統計各類股最近連續買超（🔥）或賣超（🧊）期數，反映動能強度。")

        _max_possible_streak = len(period_labels)

        momentum_rows = []
        for cat in cat_list:
            raw = period_data[cat]["raw"]
            if not raw:
                continue
            streak = 0
            direction = None
            for v in reversed(raw):
                if v == 0:
                    break
                cur_dir = "buy" if v > 0 else "sell"
                if direction is None:
                    direction = cur_dir
                if cur_dir != direction:
                    break
                streak += 1
            if streak >= 2:
                last_v = raw[-1]
                bar_pct = int(streak / max(_max_possible_streak, 1) * 100)
                bar_color = POS_COLOR if direction == "buy" else NEG_COLOR
                bar_html = (
                    f'<div style="background:#e2e8f0;border-radius:3px;height:8px;width:100%">'
                    f'<div style="background:{bar_color};width:{bar_pct}%;height:8px;border-radius:3px"></div>'
                    f'</div>'
                )
                momentum_rows.append({
                    "類股": cat,
                    "方向": "🔥 買超" if direction == "buy" else "🧊 賣超",
                    "連續期數": streak,
                    "動能強度": bar_html,
                    "最新期量體": (f"{last_v:+,.2f} {_unit_suffix}" if unit == "value_oku"
                                   else f"{last_v:+,.0f} {_unit_suffix}"),
                })

        momentum_rows.sort(key=lambda x: x["連續期數"], reverse=True)
        if momentum_rows:
            _mom_df = pd.DataFrame(momentum_rows)
            st.write(
                _mom_df.to_html(escape=False, index=False,
                    classes="momentum-table",
                    border=0),
                unsafe_allow_html=True,
            )
            st.markdown(
                "<style>.momentum-table{width:100%;border-collapse:collapse;font-size:13px}"
                ".momentum-table th{background:#e2e8f0;padding:6px 10px;text-align:left}"
                ".momentum-table td{padding:5px 10px;border-bottom:1px solid #e2e8f0}"
                "</style>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("無連續 2 期以上的動能訊號")

        # ── 輪動變化率排名 ────────────────────────────────────
        st.subheader("輪動變化率排名")
        st.caption(f"最近一期（{period_labels[-1]}）vs 上期（{period_labels[-2]}）買賣超變化。")

        chg_rows = []
        for cat in cat_list:
            raw = period_data[cat]["raw"]
            prev, curr = raw[-2], raw[-1]
            abs_chg = curr - prev
            if prev != 0:
                pct_chg = abs_chg / abs(prev) * 100
                pct_str = f"{pct_chg:+.1f}%"
            else:
                pct_str = "—" if curr == 0 else ("新增" if curr > 0 else "新增賣超")
            if abs_chg != 0:
                chg_rows.append({
                    "類股":   cat,
                    "上期":   prev,
                    "本期":   curr,
                    "變化量": abs_chg,
                    "變化率": pct_str,
                })

        chg_rows.sort(key=lambda x: x["變化量"], reverse=True)
        if chg_rows:
            _chg_df = pd.DataFrame(chg_rows)
            _num_cols = ["上期", "本期", "變化量"]
            _num_fmt_str = "{:+,.2f}" if unit == "value_oku" else "{:+,.0f}"
            _fmt = {c: (lambda v, _f=_num_fmt_str: _f.format(v)) for c in _num_cols}
            st.dataframe(
                _chg_df.style.format(_fmt).applymap(_style_num_col, subset=_num_cols),
                use_container_width=True, hide_index=True,
            )
        else:
            st.caption("兩期間無變化")

        # ── 相關性矩陣 ────────────────────────────────────────
        # ── 籌碼集中度 HHI（若有分點資料）──────────────────
        _universe_cats_h, _, _, _ = cached_load_universe(tier)
        _h_tkrs = [tk for cat in cat_list for tk in _universe_cats_h.get(cat, {}).keys()]
        _h_rows = load_broker_from_db(_h_tkrs, start_str, end_str) if _h_tkrs else []
        if _h_rows:
            st.subheader("籌碼集中度 HHI")
            st.caption(
                "Herfindahl-Hirschman Index：HHI = Σ(券商買賣超佔比%)²。"
                "**>2500 高度集中（單一主力）**、1500-2500 適度集中、**<1500 分散**（散戶盤）。"
            )
            _h_df = pd.DataFrame(_h_rows)
            # 按 ticker 聚合：每檔全期 HHI
            _hhi_by_ticker = []
            for tk in _h_tkrs:
                _sub = _h_df[_h_df["ticker"] == tk]
                if _sub.empty:
                    continue
                # 以券商為單位累計 net_lots（買賣均納入集中度分析）
                _abs_tot = _sub["net_lots"].abs().sum() or 1
                _hhi = ((_sub.groupby("broker_name")["net_lots"].sum().abs() / _abs_tot) ** 2).sum() * 10000
                _days = _sub["trade_date"].nunique()
                _cat  = next((c for c in cat_list
                              if tk in _universe_cats_h.get(c, {})), "?")
                _hhi_by_ticker.append({"類股": _cat, "代碼": tk,
                                       "公司": _universe_cats_h.get(_cat, {}).get(tk, tk),
                                       "HHI": _hhi, "資料天數": _days})
            if _hhi_by_ticker:
                _hhi_df = pd.DataFrame(_hhi_by_ticker).sort_values("HHI", ascending=False)
                def _hhi_bg(v):
                    try: v = float(v)
                    except: return ""
                    if v > 2500: return f"background-color: #fecaca"
                    if v > 1500: return f"background-color: #fef08a"
                    return f"background-color: #bbf7d0"
                st.dataframe(
                    _hhi_df.style.format({"HHI": "{:,.0f}"})
                        .applymap(_hhi_bg, subset=["HHI"]),
                    use_container_width=True, hide_index=True,
                )
            else:
                st.caption("無有效分點資料可計算 HHI")

        with st.expander("類股資金相關性矩陣"):
            st.caption("各類股每期買賣超的 Pearson 相關係數。+1 = 同步操作，-1 = 反向操作。")

            _raw_df = pd.DataFrame(
                {cat: period_data[cat]["raw"] for cat in cat_list},
                index=period_labels,
            )
            _valid = _raw_df.loc[:, _raw_df.std() > 0]
            if _valid.shape[1] >= 2:
                _corr = _valid.corr()
                fig_corr = go.Figure(go.Heatmap(
                    z=_corr.values,
                    x=list(_corr.columns),
                    y=list(_corr.index),
                    colorscale="RdBu",
                    zmid=0, zmin=-1, zmax=1,
                    text=np.round(_corr.values, 2),
                    texttemplate="%{text}",
                    textfont=dict(size=10),
                    hovertemplate="%{y} × %{x}<br>相關係數：%{z:.2f}<extra></extra>",
                ))
                fig_corr.update_layout(
                    **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend", "margin")},
                    height=max(400, len(_valid.columns) * 35),
                    xaxis=dict(tickangle=-45),
                    margin=dict(t=40, b=120, l=120, r=20),
                )
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.caption("需要至少 2 個有效類股才能計算相關性")


# ── Tab 6：散戶情緒（融資融券） ─────────────────────────────
if tab6 is not None:
    with tab6:
        st.caption(
            "融資餘額 = 散戶槓桿部位；融券餘額 = 散戶做空部位。"
            "**融資↑ + 法人賣** = 散戶追高，籌碼轉差；"
            "**融資↓ + 法人買** = 散戶殺低，籌碼轉佳；"
            "**融券↑** = 空方壓力加重。（單位：張）"
        )

        _m_dates_full = trading_dates_in_range(
            datetime.strptime(start_str, "%Y-%m-%d").date(),
            datetime.strptime(end_str,   "%Y-%m-%d").date(),
        )
        _m_db = load_margin_from_db(_m_dates_full)

        if not _m_db:
            st.warning("融資融券 DB 無資料。請在左側「散戶情緒（融資融券）」expander 按「補抓融資融券」。")
        else:
            # 按日期聚合：整個當前 cat_list 成員股合計
            _active_tkrs = set()
            _universe_cats, _, _u_t2c, _ = cached_load_universe(tier)
            for cat in cat_list:
                for tk in _universe_cats.get(cat, {}).keys():
                    _active_tkrs.add(tk)

            # 依日期分組累加
            _by_date = {}
            for (tk, dt), v in _m_db.items():
                if tk not in _active_tkrs:
                    continue
                slot = _by_date.setdefault(dt, {
                    "margin_balance": 0.0, "margin_prev": 0.0,
                    "margin_buy": 0.0, "margin_sell": 0.0,
                    "short_balance": 0.0, "short_prev": 0.0,
                    "short_sell": 0.0, "short_cover": 0.0,
                })
                for k in slot.keys():
                    slot[k] += (v.get(k) or 0.0)

            _sorted_dates = sorted(_by_date.keys())
            if not _sorted_dates:
                st.warning("當前選取類股於此區間無融資融券資料。")
            else:
                _mg_bal = [_by_date[d]["margin_balance"] for d in _sorted_dates]
                _mg_chg = [_by_date[d]["margin_balance"] - _by_date[d]["margin_prev"] for d in _sorted_dates]
                _sh_bal = [_by_date[d]["short_balance"]  for d in _sorted_dates]
                _sh_chg = [_by_date[d]["short_balance"]  - _by_date[d]["short_prev"]  for d in _sorted_dates]

                # 法人合計（當前單位為股；轉張比較）
                _inst_dates = set(_sorted_dates)
                _inst_daily = {d: 0.0 for d in _sorted_dates}
                _db_data = load_from_db(_sorted_dates)
                for (tk, dt), v in _db_data.items():
                    if tk in _active_tkrs and dt in _inst_dates:
                        _inst_daily[dt] += v.get("total", 0.0) / 1000.0   # 股 → 張
                _inst_net = [_inst_daily[d] for d in _sorted_dates]

                fig6 = make_subplots(
                    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
                    row_heights=[0.55, 0.45],
                    subplot_titles=("融資餘額 vs 法人買賣超", "融券餘額與空方壓力"),
                )
                # 融資餘額（線）
                fig6.add_trace(go.Scatter(
                    x=_sorted_dates, y=_mg_bal, name="融資餘額",
                    line=dict(color="#f59e0b", width=2),
                    hovertemplate="%{x}<br>融資餘額：%{y:,.0f} 張<extra></extra>",
                ), row=1, col=1)
                # 法人買賣超（柱，副軸）
                fig6.add_trace(go.Bar(
                    x=_sorted_dates, y=_inst_net, name="三大法人買賣超",
                    marker_color=[POS_COLOR if v > 0 else NEG_COLOR for v in _inst_net],
                    opacity=0.55, yaxis="y2",
                    hovertemplate="%{x}<br>法人：%{y:+,.0f} 張<extra></extra>",
                ), row=1, col=1)
                # 融券餘額（線）
                fig6.add_trace(go.Scatter(
                    x=_sorted_dates, y=_sh_bal, name="融券餘額",
                    line=dict(color="#8b5cf6", width=2),
                    hovertemplate="%{x}<br>融券餘額：%{y:,.0f} 張<extra></extra>",
                ), row=2, col=1)
                fig6.add_trace(go.Bar(
                    x=_sorted_dates, y=_sh_chg, name="融券變化",
                    marker_color=[NEG_COLOR if v > 0 else POS_COLOR for v in _sh_chg],
                    opacity=0.55,
                    hovertemplate="%{x}<br>融券變化：%{y:+,.0f} 張<extra></extra>",
                ), row=2, col=1)

                fig6.update_layout(
                    **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
                    height=640,
                    yaxis=dict(title="融資餘額（張）", gridcolor="#cbd5e1", tickformat=","),
                    yaxis2=dict(title="法人買賣超（張）", overlaying="y", side="right",
                                showgrid=False, tickformat=",+"),
                    yaxis3=dict(title="融券餘額（張）", gridcolor="#cbd5e1", tickformat=","),
                    legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
                )
                st.plotly_chart(fig6, use_container_width=True)

                # 同期背離統計
                _div_days = sum(1 for m, i in zip(_mg_chg, _inst_net)
                                if (m > 0 and i < 0) or (m < 0 and i > 0))
                _sync_days = sum(1 for m, i in zip(_mg_chg, _inst_net)
                                 if (m > 0 and i > 0) or (m < 0 and i < 0))
                _c1, _c2, _c3 = st.columns(3)
                _c1.metric("融資-法人 背離天數", f"{_div_days}")
                _c2.metric("融資-法人 同向天數", f"{_sync_days}")
                _c3.metric("最新融券餘額", f"{_sh_bal[-1]:,.0f} 張",
                           delta=f"{_sh_chg[-1]:+,.0f}")


# ── Tab 7：券商動向 ────────────────────────────────────────
if tab7 is not None:
    with tab7:
        st.caption(
            "類股成員股前 15 大券商買賣超聚合。**紅色券商名稱** = 外資券商。"
            "資料來源：HiStock 分點（當日，僅前 15 買方 + 前 15 賣方）。"
        )

        # 外資券商辨識（關鍵字）
        _foreign_keywords = ["高盛", "摩根", "美林", "花旗", "瑞銀", "瑞信",
                             "野村", "新加坡商", "港商", "法商", "美商",
                             "匯豐", "麥格理", "德意志", "日商", "星展"]
        def _is_foreign(name: str) -> bool:
            return any(k in name for k in _foreign_keywords)

        _universe_cats, _, _u_t2c, _ = cached_load_universe(tier)
        _bt_tkrs = set()
        for cat in cat_list:
            for tk in _universe_cats.get(cat, {}).keys():
                _bt_tkrs.add(tk)

        if not _bt_tkrs:
            st.warning("當前類股無標的。")
        else:
            _b_rows = load_broker_from_db(list(_bt_tkrs), start_str, end_str)
            if not _b_rows:
                st.warning(
                    "DB 無分點資料。左側「🏦 券商分點」按「📥 抓取今日分點」。"
                    "HiStock 僅提供當日資料，需每日累積。"
                )
            else:
                _b_df = pd.DataFrame(_b_rows)
                # 聚合：broker_name 跨所有成員股與日期加總
                _agg = _b_df.groupby("broker_name", as_index=False).agg(
                    net_lots=("net_lots", "sum"),
                    buy_lots=("buy_lots", "sum"),
                    sell_lots=("sell_lots", "sum"),
                    days=("trade_date", "nunique"),
                    tickers=("ticker", "nunique"),
                )
                _agg["is_foreign"] = _agg["broker_name"].apply(_is_foreign)
                _agg = _agg.sort_values("net_lots", ascending=False)

                _col1, _col2 = st.columns([0.6, 0.4])
                with _col1:
                    st.subheader(f"前 15 大買超券商（類股 {len(_bt_tkrs)} 檔 × {_b_df['trade_date'].nunique()} 天）")
                    _top = _agg.head(15)
                    fig_b = go.Figure(go.Bar(
                        x=_top["net_lots"],
                        y=_top["broker_name"],
                        orientation="h",
                        marker_color=[("#ef4444" if f else "#3b82f6") for f in _top["is_foreign"]],
                        hovertemplate="%{y}<br>買超 %{x:,.0f} 張<extra></extra>",
                    ))
                    fig_b.update_layout(
                        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
                        height=520,
                        yaxis=dict(autorange="reversed", gridcolor="#cbd5e1"),
                        xaxis=dict(title="買超（張）", tickformat=",", gridcolor="#cbd5e1",
                                   zeroline=True, zerolinecolor="#94a3b8"),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_b, use_container_width=True)

                    st.subheader(f"前 15 大賣超券商")
                    _bot = _agg.tail(15).iloc[::-1]
                    fig_s = go.Figure(go.Bar(
                        x=_bot["net_lots"],
                        y=_bot["broker_name"],
                        orientation="h",
                        marker_color=[("#ef4444" if f else "#22c55e") for f in _bot["is_foreign"]],
                        hovertemplate="%{y}<br>賣超 %{x:,.0f} 張<extra></extra>",
                    ))
                    fig_s.update_layout(
                        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
                        height=520,
                        yaxis=dict(autorange="reversed", gridcolor="#cbd5e1"),
                        xaxis=dict(title="賣超（張）", tickformat=",", gridcolor="#cbd5e1",
                                   zeroline=True, zerolinecolor="#94a3b8"),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_s, use_container_width=True)

                with _col2:
                    st.subheader("券商 → 成員股分佈")
                    _all_brokers = _agg["broker_name"].tolist()
                    _sel_broker = st.selectbox("選擇券商", options=_all_brokers[:30], index=0)
                    _bk = _b_df[_b_df["broker_name"] == _sel_broker].groupby("ticker", as_index=False).agg(
                        net_lots=("net_lots", "sum"),
                    )
                    _tk2name = {tk: nm for c in _universe_cats.values() for tk, nm in c.items()}
                    _bk["name"] = _bk["ticker"].map(lambda t: _tk2name.get(t, t))
                    _bk["cat"]  = _bk["ticker"].map(lambda t: _u_t2c.get(t, "?"))
                    _bk["abs"]  = _bk["net_lots"].abs()
                    _bk = _bk.sort_values("abs", ascending=False)
                    if not _bk.empty and _bk["abs"].sum() > 0:
                        fig_tm = go.Figure(go.Treemap(
                            labels=_bk["name"] + "<br>" + _bk["net_lots"].map(lambda v: f"{v:+,.0f} 張"),
                            parents=[""] * len(_bk),
                            values=_bk["abs"],
                            marker=dict(
                                colors=[(POS_COLOR if v > 0 else NEG_COLOR) for v in _bk["net_lots"]],
                            ),
                            hovertemplate="%{label}<extra></extra>",
                            textinfo="label",
                        ))
                        fig_tm.update_layout(height=540, margin=dict(t=20, b=20, l=10, r=10))
                        st.plotly_chart(fig_tm, use_container_width=True)
                    else:
                        st.caption("該券商無個股資料")

                # 外資 vs 本土彙總
                st.subheader("外資 vs 本土券商")
                _f_net = _agg[_agg["is_foreign"]]["net_lots"].sum()
                _d_net = _agg[~_agg["is_foreign"]]["net_lots"].sum()
                _f_count = _agg["is_foreign"].sum()
                _cc1, _cc2, _cc3 = st.columns(3)
                _cc1.metric("外資券商 淨買賣超（張）", f"{_f_net:+,.0f}")
                _cc2.metric("本土券商 淨買賣超（張）", f"{_d_net:+,.0f}")
                _cc3.metric("外資券商進榜數", f"{_f_count} / {len(_agg)}")


# ── Tab 8：期現連動 ────────────────────────────────────────
if tab8 is not None:
    with tab8:
        st.caption(
            "三大法人期貨淨多空口數（多空淨額）。**外資期貨淨空 + 現貨賣超** = 做空預期，"
            "**外資期貨淨多 + 現貨買超** = 看多加碼。"
            "契約：TXF 臺股期、EXF 電子期。"
        )
        _f_dates = trading_dates_in_range(
            datetime.strptime(start_str, "%Y-%m-%d").date(),
            datetime.strptime(end_str,   "%Y-%m-%d").date(),
        )
        _f_rows = load_futures_from_db(_f_dates, ["TXF", "EXF"])
        if not _f_rows:
            st.warning("期貨未平倉 DB 無資料。重新載入或擴大日期區間。")
        else:
            _f_df = pd.DataFrame(_f_rows).sort_values("trade_date")

            _contract_choice = st.radio("合約", ["TXF 臺股期", "EXF 電子期"], horizontal=True)
            _cid = "TXF" if _contract_choice.startswith("TXF") else "EXF"
            _sub = _f_df[_f_df["contract"] == _cid]
            if _sub.empty:
                st.warning(f"{_cid} 無資料")
            else:
                _pivot = _sub.pivot_table(
                    index="trade_date", columns="role",
                    values="net_oi", aggfunc="sum",
                ).fillna(0)
                fig_fut = go.Figure()
                _role_color = {"foreign": "#2563eb", "invest": "#8b5cf6", "dealer": "#f97316"}
                _role_label = {"foreign": "外資", "invest": "投信", "dealer": "自營"}
                for role in ["foreign", "invest", "dealer"]:
                    if role not in _pivot.columns:
                        continue
                    fig_fut.add_trace(go.Bar(
                        x=_pivot.index, y=_pivot[role],
                        name=_role_label[role],
                        marker_color=_role_color[role],
                        opacity=0.8,
                        hovertemplate=f"%{{x}}<br>{_role_label[role]} 淨 %{{y:+,.0f}} 口<extra></extra>",
                    ))
                fig_fut.add_hline(y=0, line_color="#94a3b8", line_width=1, line_dash="dot")
                fig_fut.update_layout(
                    **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
                    barmode="group", height=480,
                    yaxis=dict(title=f"{_cid} 淨多空口數", tickformat=",", gridcolor="#cbd5e1",
                               zeroline=True, zerolinecolor="#94a3b8"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
                )
                st.plotly_chart(fig_fut, use_container_width=True)

                # 當前外資淨多空
                _latest_day = _pivot.index[-1]
                _latest = _pivot.iloc[-1]
                _cc1, _cc2, _cc3 = st.columns(3)
                _cc1.metric("外資淨多空（口）",
                            f"{_latest.get('foreign', 0):+,.0f}",
                            delta=f"{(_latest.get('foreign',0) - _pivot.iloc[-2].get('foreign',0)):+,.0f}" if len(_pivot) >= 2 else None)
                _cc2.metric("投信淨多空（口）",
                            f"{_latest.get('invest', 0):+,.0f}",
                            delta=f"{(_latest.get('invest',0) - _pivot.iloc[-2].get('invest',0)):+,.0f}" if len(_pivot) >= 2 else None)
                _cc3.metric("自營淨多空（口）",
                            f"{_latest.get('dealer', 0):+,.0f}",
                            delta=f"{(_latest.get('dealer',0) - _pivot.iloc[-2].get('dealer',0)):+,.0f}" if len(_pivot) >= 2 else None)
                st.caption(f"資料日期：{_latest_day}")


# ── 個股明細 ─────────────────────────────────────────────────
with st.expander("個股明細（全期合計）"):
    _detail_cats, _, _detail_ticker_to_cat, _ = cached_load_universe(tier)
    _detail_dates = trading_dates_in_range(
        datetime.strptime(start_str, "%Y-%m-%d").date(),
        datetime.strptime(end_str,   "%Y-%m-%d").date(),
    )
    _detail_db   = load_from_db(_detail_dates)
    _detail_agg  = aggregate_by_category(_detail_db, _detail_dates, _detail_cats, _detail_ticker_to_cat)

    _drill_cat = st.selectbox(
        "篩選類股（全選顯示所有）",
        options=["（全部）"] + cat_list,
        index=0,
        key="drill_cat",
    )

    _detail_scale = _unit_scale(unit)
    _detail_fk = _key_for_unit("foreign", unit)
    _detail_ik = _key_for_unit("invest",  unit)
    _detail_dk = _key_for_unit("dealer",  unit)
    # 取最新 QFII 快照（單日）
    _qfii_latest = {}
    if _detail_dates:
        _q = load_qfii_from_db([_detail_dates[-1]])
        for (tk, _dt), v in _q.items():
            _qfii_latest[tk] = v
    # TDCC 大戶（分級 15 = 1000 張以上）最新週
    _all_tkrs_for_tdcc = list({tk for cat in cat_list for tk in _detail_cats.get(cat, {}).keys()})
    _tdcc_latest = load_tdcc_latest(_all_tkrs_for_tdcc)
    rows = []
    for cat in cat_list:
        if _drill_cat != "（全部）" and cat != _drill_cat:
            continue
        agg_vals = _detail_agg[cat]
        # 個股明細：stocks dict 只含「股數」合計；金額模式下按類股平均價估算不準，維持顯示股數
        # 類股法人欄位依單位切換
        # stocks: {ticker: {"shares": ..., "value": ... (千元)}}
        for ticker, sdat in sorted(
            agg_vals["stocks"].items(), key=lambda x: x[1]["shares"], reverse=True
        ):
            name = _detail_cats[cat].get(ticker, ticker)
            if unit == "shares":
                stock_disp = sdat["shares"]
            elif unit == "value_oku":
                stock_disp = sdat["value"] / 1e5
            else:  # value_thousand
                stock_disp = sdat["value"]
            _q = _qfii_latest.get(ticker, {})
            _fpct = _q.get("foreign_pct", 0)
            _rpct = _q.get("remaining_pct", 0)
            _lpct = _q.get("limit_pct", 0)
            _warn = "🔴" if _rpct and _rpct < 5 else ("🟡" if _rpct and _rpct < 15 else "")
            _td = _tdcc_latest.get(ticker, {})
            _big = _td.get(15, {}).get("pct", 0)     # 大戶 ≥1000 張比例
            _retail = sum((_td.get(t, {}).get("pct", 0)) for t in range(1, 10))  # 散戶 <5萬股
            rows.append({
                "類股":       cat,
                "代碼":       ticker,
                "公司":       name,
                f"外資（類股／{_unit_suffix}）": agg_vals.get(_detail_fk, 0.0) * _detail_scale,
                f"投信（類股／{_unit_suffix}）": agg_vals.get(_detail_ik, 0.0) * _detail_scale,
                f"自營（類股／{_unit_suffix}）": agg_vals.get(_detail_dk, 0.0) * _detail_scale,
                f"個股合計（{_unit_suffix}）":   stock_disp,
                "外資持股%":  f"{_fpct:.2f}" if _fpct else "—",
                "剩餘%":      f"{_warn} {_rpct:.2f}" if _rpct else "—",
                "上限%":      f"{_lpct:.0f}" if _lpct else "—",
                "大戶≥1000張%": f"{_big:.2f}" if _big else "—",
                "散戶<5萬股%":  f"{_retail:.2f}" if _retail else "—",
            })

    if rows:
        _detail_df = pd.DataFrame(rows)
        _num_cols_d = [f"外資（類股／{_unit_suffix}）",
                       f"投信（類股／{_unit_suffix}）",
                       f"自營（類股／{_unit_suffix}）",
                       f"個股合計（{_unit_suffix}）"]
        _d_fmt_str = "{:+,.2f}" if unit == "value_oku" else "{:+,.0f}"
        _fmt_d = {c: (lambda v, _f=_d_fmt_str: _f.format(v)) for c in _num_cols_d}
        st.dataframe(
            _detail_df.style.format(_fmt_d).applymap(_style_num_col, subset=_num_cols_d),
            use_container_width=True, hide_index=True,
        )
        st.caption("外資／投信／自營欄位為類股級別合計；個股合計為該股票全期三大法人買賣超加總。")
    else:
        st.write("（無資料，請先更新）")
