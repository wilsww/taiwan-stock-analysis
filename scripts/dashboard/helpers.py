from datetime import datetime, timedelta
from typing import Optional

import plotly.graph_objects as go

# ── 顏色常數 ─────────────────────────────────────────────────
POS_COLOR = "#ef4444"
NEG_COLOR = "#22c55e"
NEU_COLOR = "#94a3b8"

# ── 共用顏色常數（grid / zero / missing / legend bg）────────
GRID_COLOR     = "#cbd5e1"
NEU_ZERO_COLOR = "#94a3b8"
MISSING_FILL   = "rgba(148,163,184,0.22)"
MISSING_BORDER = "rgba(100,116,139,0.24)"
MISSING_TEXT   = "rgba(100,116,139,0.85)"
LEGEND_BG      = "rgba(241,245,249,0.85)"

# ── 共用 layout 片段 ───────────────────────────────────────
HIDDEN_Y2 = dict(overlaying="y", range=[0, 1], visible=False, fixedrange=True)

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

# Tab1/2 直接套用 LAYOUT_BASE（含預設 legend）。
# Tab3/4/6/8 需客製 legend（不同 font size / x 錨點 / tracegroupgap），
# 於各 tab 內 override 整個 "legend" key；Tab5/7 走 st.plotly_chart 傳 showlegend=False。
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
        bgcolor=LEGEND_BG,
        entrywidth=120,
        entrywidthmode="pixels",
    ),
    margin=dict(t=80, b=40, l=60, r=20),
)


def build_missing_spans(
    labels: list[str],
    missing_set: set[str],
) -> list[tuple[int, int, bool, bool]]:
    """回傳連續缺漏區間與左右是否緊鄰有效資料。"""
    spans: list[tuple[int, int, bool, bool]] = []
    span_start: Optional[int] = None
    span_end: Optional[int] = None

    for idx, lbl in enumerate(labels):
        if lbl not in missing_set:
            if span_start is not None and span_end is not None:
                has_left_data = span_start > 0 and labels[span_start - 1] not in missing_set
                has_right_data = span_end + 1 < len(labels) and labels[span_end + 1] not in missing_set
                spans.append((span_start, span_end, has_left_data, has_right_data))
                span_start = span_end = None
            continue

        if span_start is None:
            span_start = span_end = idx
        else:
            span_end = idx

    if span_start is not None and span_end is not None:
        has_left_data = span_start > 0 and labels[span_start - 1] not in missing_set
        has_right_data = span_end + 1 < len(labels) and labels[span_end + 1] not in missing_set
        spans.append((span_start, span_end, has_left_data, has_right_data))

    return spans


def _day_label_dt(label: str) -> datetime:
    return datetime.strptime(label, "%Y-%m-%d")


def build_period_xaxis(period_labels: list[str], split: str) -> dict:
    if split == "day" and period_labels:
        start_dt = _day_label_dt(period_labels[0]) - timedelta(hours=12)
        end_dt = _day_label_dt(period_labels[-1]) + timedelta(hours=12)
        return dict(
            type="date",
            range=[start_dt, end_dt],
            rangebreaks=[dict(bounds=["sat", "mon"])],
            gridcolor=GRID_COLOR,
        )

    return dict(
        type="category",
        categoryorder="array",
        categoryarray=period_labels,
        gridcolor=GRID_COLOR,
    )


def add_missing_markers(fig, missing_labels, period_labels, split):
    _fill_color = MISSING_FILL
    _border_color = MISSING_BORDER

    for lbl in missing_labels:
        if split != "day":
            if lbl in period_labels:
                fig.add_vrect(
                    x0=lbl,
                    x1=lbl,
                    x0shift=-0.5,
                    x1shift=0.5,
                    fillcolor=_fill_color,
                    line_width=0,
                    layer="below",
                )
            continue

    if split == "day" and missing_labels:
        missing_set = set(missing_labels)

        for start_idx, end_idx, has_left_data, has_right_data in build_missing_spans(period_labels, missing_set):
            start_dt = _day_label_dt(period_labels[start_idx]) - timedelta(hours=12)
            end_dt = _day_label_dt(period_labels[end_idx]) + timedelta(hours=12)
            fig.add_vrect(
                x0=start_dt,
                x1=end_dt,
                fillcolor=_fill_color,
                line_width=0,
                layer="below",
            )

            # 只有在缺漏區塊真的接到有效資料時，才補一條淡邊界線，避免邊界視覺偏移。
            if has_left_data:
                fig.add_vline(
                    x=start_dt,
                    line_width=1,
                    line_color=_border_color,
                    layer="below",
                )
            if has_right_data:
                fig.add_vline(
                    x=end_dt,
                    line_width=1,
                    line_color=_border_color,
                    layer="below",
                )

            fig.add_annotation(
                x=start_dt + (end_dt - start_dt) / 2,
                y=1,
                yref="paper",
                text="無資料",
                showarrow=False,
                font=dict(size=8, color=MISSING_TEXT),
                yanchor="bottom",
            )


def split_by_missing(
    labels: list[str],
    values: list[float],
    missing_set: set[str],
) -> list[tuple[list[str], list[float]]]:
    """依缺漏日切成多段連續有效資料，缺漏 label 不會出現在回傳段內。"""
    segments: list[tuple[list[str], list[float]]] = []
    cur_x: list[str] = []
    cur_y: list[float] = []

    for lbl, val in zip(labels, values):
        if lbl in missing_set:
            if cur_x:
                segments.append((cur_x, cur_y))
                cur_x, cur_y = [], []
            continue
        cur_x.append(lbl)
        cur_y.append(val)

    if cur_x:
        segments.append((cur_x, cur_y))

    return segments


def add_transparent_xaxis_helper(
    fig: go.Figure,
    labels: list[str],
    *,
    yaxis: str = "y2",
    y_value: float = 0.5,
) -> None:
    """加一條透明 helper trace，保留所有 x 類別位置但不參與 hover。"""
    if not labels:
        return

    fig.add_trace(go.Scatter(
        x=labels,
        y=[y_value] * len(labels),
        mode="markers",
        marker=dict(size=10, color="rgba(0,0,0,0)"),
        hoverinfo="skip",
        showlegend=False,
        meta=dict(helper_trace=True),
        yaxis=yaxis,
    ))


def _color_num(v: float, unit: str, suffix: str) -> str:
    fmt = "+,.2f" if unit == "value_oku" else "+,.0f"
    txt_pos = f"{v:{fmt}} {suffix}"
    txt_zero = f"0 {suffix}"
    if v > 0:
        return f'<span style="color:{POS_COLOR};font-weight:600">{txt_pos}</span>'
    elif v < 0:
        return f'<span style="color:{NEG_COLOR};font-weight:600">{txt_pos}</span>'
    return f'<span style="color:{NEU_COLOR}">{txt_zero}</span>'


def _bar_trace(
    fig: go.Figure,
    vals: list[float],
    name: str,
    color: str,
    legendgroup: str,
    period_labels: list[str],
) -> None:
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


def _hhi_bg(v) -> str:
    try:
        v = float(v)
    except Exception:
        return ""
    if v > 2500:
        return "background-color: #fecaca"
    if v > 1500:
        return "background-color: #fef08a"
    return "background-color: #bbf7d0"


_FOREIGN_BROKER_KEYWORDS = ("高盛", "摩根", "美林", "花旗", "瑞銀", "瑞信",
                            "野村", "新加坡商", "港商", "法商", "美商",
                            "匯豐", "麥格理", "德意志", "日商", "星展")


def _is_foreign(name: str) -> bool:
    return any(k in name for k in _FOREIGN_BROKER_KEYWORDS)


def _style_num_col(val) -> str:
    try:
        v = float(val)
        if v > 0:
            return f"color: {POS_COLOR}; font-weight: 600"
        elif v < 0:
            return f"color: {NEG_COLOR}; font-weight: 600"
        return f"color: {NEU_COLOR}"
    except Exception:
        return ""
