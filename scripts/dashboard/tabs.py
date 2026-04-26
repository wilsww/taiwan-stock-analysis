from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.helpers import (
    POS_COLOR, NEG_COLOR, GRID_COLOR, NEU_ZERO_COLOR, LEGEND_BG, HIDDEN_Y2,
    LAYOUT_BASE, build_period_xaxis, add_missing_markers, split_by_missing,
    add_transparent_xaxis_helper, _color_num, _style_num_col, _bar_trace,
    _hhi_bg, _is_foreign, _unit_scale, _key_for_unit,
)
from dashboard.panels import render_chart_with_panel
from sector_flow import (
    load_from_db,
    aggregate_by_category,
    load_margin_from_db,
    load_broker_from_db,
    load_qfii_from_db,
    load_futures_from_db,
    load_tdcc_latest,
)


@dataclass(frozen=True)
class TabContext:
    params: Any
    data: Any


def render_alerts(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    a1, a2, a3, a4 = st.columns(4)

    latest_idx = -1
    latest_fgn = [(cat, data.period_data[cat]["foreign"][latest_idx]) for cat in data.cat_list]
    latest_fgn.sort(key=lambda x: x[1], reverse=True)
    top_fgn = latest_fgn[:3]
    latest_label = data.period_labels[latest_idx] if data.period_labels else "—"
    a1.markdown(f"**🏦 最新期外資買超 TOP3** _({latest_label})_")
    for cat, v in top_fgn:
        color = POS_COLOR if v > 0 else NEG_COLOR
        a1.markdown(
            f'<span style="color:{color};font-weight:600">{cat}：'
            f'{v:+,.2f} {data.unit_suffix}</span>',
            unsafe_allow_html=True,
        )

    streak_cats = []
    for cat in data.cat_list:
        raw = data.period_data[cat]["raw"]
        streak = 0
        for v in reversed(raw):
            if v > 0:
                streak += 1
            else:
                break
        if streak >= 3:
            streak_cats.append((cat, streak))
    a2.metric("🔥 連續 ≥3 期買超類股", f"{len(streak_cats)} 類")
    if streak_cats:
        a2.caption("、".join(f"{c}({s})" for c, s in streak_cats[:3]))

    if params.margin_auto:
        try:
            m_db = load_margin_from_db(data.trading_dates)
            if m_db:
                by_date_a: dict[str, float] = {}
                for (tk, dt), v in m_db.items():
                    if tk not in data.active_tickers:
                        continue
                    by_date_a[dt] = by_date_a.get(dt, 0.0) + (
                        (v.get("margin_balance", 0) or 0)
                        - (v.get("margin_prev", 0) or 0)
                    )

                i_db_all = load_from_db(sorted(by_date_a.keys())) if by_date_a else {}
                inst_net_by_date: dict[str, float] = {}
                for (tk, dt), v in i_db_all.items():
                    if tk not in data.active_tickers:
                        continue
                    inst_net_by_date[dt] = inst_net_by_date.get(dt, 0.0) + v.get("total", 0)

                div = 0
                for dt, m_chg in by_date_a.items():
                    i_net = inst_net_by_date.get(dt, 0.0)
                    if (m_chg > 0 and i_net < 0) or (m_chg < 0 and i_net > 0):
                        div += 1
                a3.metric("📊 融資-法人 背離天數", f"{div}")
            else:
                a3.metric("📊 融資-法人 背離", "—")
        except Exception:
            a3.metric("📊 融資-法人 背離", "—")
    else:
        a3.metric("📊 融資-法人 背離", "未啟用")
        a3.caption("左側啟用融資融券顯示")

    near_limit = []
    if data.trading_dates:
        q_db = load_qfii_from_db([data.trading_dates[-1]])
        for (tk, _dt), v in q_db.items():
            if tk in data.active_tickers and v.get("remaining_pct", 100) < 5:
                near_limit.append((tk, v.get("remaining_pct", 0)))
    a4.metric("⚠️ 外資接近上限（剩<5%）", f"{len(near_limit)} 檔")
    if near_limit:
        near_limit.sort(key=lambda x: x[1])
        a4.caption("、".join(f"{t}({p:.1f}%)" for t, p in near_limit[:3]))


def render_scrubber(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data

    with st.expander("⏮️ 時間軸回放（單期 snapshot）"):
        scrub_idx = st.slider(
            "選擇期間",
            min_value=0, max_value=len(data.period_labels) - 1,
            value=len(data.period_labels) - 1,
            format="%d",
        )
        scrub_label = data.period_labels[scrub_idx]
        st.caption(f"📅 **{scrub_label}**")

        scrub_vals = [(cat, data.period_data[cat]["raw"][scrub_idx]) for cat in data.cat_list]
        scrub_vals.sort(key=lambda x: x[1], reverse=True)
        sc_cats = [c for c, _ in scrub_vals]
        sc_data = [v for _, v in scrub_vals]
        sc_colors = [POS_COLOR if v > 0 else NEG_COLOR for v in sc_data]
        fig_scrub = go.Figure(go.Bar(
            x=sc_data, y=sc_cats, orientation="h",
            marker_color=sc_colors,
            text=[f"{v:+{data.unit_fmt}}" for v in sc_data],
            textposition="outside",
            hovertemplate="%{y}<br>%{x:+,.2f}<extra></extra>",
        ))
        fig_scrub.update_layout(
            **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
            height=max(300, len(data.cat_list) * 30 + 80),
            xaxis=dict(
                title=f"當期 {params.institution_label} 買賣超（{data.unit_suffix}）",
                tickformat=",.2f" if params.unit == "value_oku" else ",",
                gridcolor=GRID_COLOR,
                zeroline=True, zerolinecolor=NEU_ZERO_COLOR,
            ),
            yaxis=dict(autorange="reversed", gridcolor=GRID_COLOR),
            showlegend=False,
        )
        st.plotly_chart(fig_scrub, width="stretch")


def render_tab1(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    fig1 = go.Figure()
    segments_per_cat = {
        cat: split_by_missing(data.period_labels, data.period_data[cat]["pos"], data.missing_set)
        for cat in data.cat_list
    }
    segment_count = max((len(segments) for segments in segments_per_cat.values()), default=0)

    for seg_idx in range(segment_count):
        for cat in data.cat_list:
            segments = segments_per_cat[cat]
            if seg_idx >= len(segments):
                continue
            sx, sy = segments[seg_idx]
            color = data.cat_colors[cat]
            fig1.add_trace(go.Scatter(
                x=sx,
                y=sy,
                name=cat,
                legendgroup=cat,
                showlegend=(seg_idx == 0),
                stackgroup=f"g{seg_idx}",
                groupnorm="percent",
                fill="tonexty",
                line=dict(width=0.5, color=color),
                fillcolor=color,
                opacity=0.85,
                hovertemplate="%{x}<extra></extra>",
            ))

    add_transparent_xaxis_helper(fig1, data.period_labels)
    fig1.update_layout(
        **LAYOUT_BASE,
        height=500,
        yaxis=dict(ticksuffix="%", range=[0, 100], gridcolor=GRID_COLOR),
        yaxis2=HIDDEN_Y2,
        xaxis=build_period_xaxis(data.period_labels, params.split),
    )
    add_missing_markers(fig1, data.missing_labels, data.period_labels, params.split)

    parts = ["面積高度 = 各類股買賣超絕對值佔比"]
    if data.missing_labels:
        parts.append(f"灰色底色 = 開盤無資料（{len(data.missing_labels)} 天）")
    st.caption("　｜　".join(parts))

    render_chart_with_panel(
        fig1, data.panel_tab1, "tab1", data.cat_colors,
        unit=params.unit, unit_suffix=data.unit_suffix,
        cat_order=data.cat_list, height=500, n_cats=len(data.cat_list),
        coverage_json=data.coverage_json,
    )


def render_tab2(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    st.caption(
        "各類股每期買賣超累加，反映法人倉位變化趨勢。"
        "向上 = 持續買進加碼，向下 = 持續賣出減碼。"
    )

    fig2 = go.Figure()
    for cat in data.cat_list:
        color = data.cat_colors[cat]
        rgba_fill = data.cat_rgba_015[cat]
        segments = split_by_missing(data.period_labels, data.period_data[cat]["cumsum"], data.missing_set)
        for i, (sx, sy) in enumerate(segments):
            fig2.add_trace(go.Scatter(
                x=sx,
                y=sy,
                name=cat,
                legendgroup=cat,
                showlegend=(i == 0),
                mode="lines",
                line=dict(width=1.5, color=color),
                fill="tozeroy",
                fillcolor=rgba_fill,
                hovertemplate="%{x}<extra></extra>",
            ))

    add_transparent_xaxis_helper(fig2, data.period_labels)
    fig2.add_hline(y=0, line_width=1, line_color=NEU_ZERO_COLOR, line_dash="dot")
    fig2.update_layout(
        **LAYOUT_BASE,
        height=500,
        yaxis=dict(
            title=f"累積買賣超（{data.unit_suffix}）",
            gridcolor=GRID_COLOR,
            tickformat=",.2f" if params.unit == "value_oku" else ",",
        ),
        yaxis2=HIDDEN_Y2,
        xaxis=build_period_xaxis(data.period_labels, params.split),
    )
    add_missing_markers(fig2, data.missing_labels, data.period_labels, params.split)

    render_chart_with_panel(
        fig2, data.panel_tab2, "tab2", data.cat_colors,
        unit=params.unit, unit_suffix=data.unit_suffix,
        cat_order=data.cat_list, height=500, n_cats=len(data.cat_list),
        coverage_json=data.coverage_json,
    )


def render_tab3(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    st.caption(
        "各類股每期買賣超股數，正值朝上（買超）、負值朝下（賣超）。"
        "顏色與其他圖表一致。"
    )

    fig3 = go.Figure()
    for cat in data.cat_list:
        color = data.cat_colors[cat]
        raw_vals = data.period_data[cat]["raw"]
        pos = [
            None if lbl in data.missing_set else (v if v > 0 else 0)
            for lbl, v in zip(data.period_labels, raw_vals)
        ]
        neg = [
            None if lbl in data.missing_set else (v if v < 0 else 0)
            for lbl, v in zip(data.period_labels, raw_vals)
        ]
        shared = dict(
            x=data.period_labels, name=cat,
            marker_color=color,
            hovertemplate="%{x}<extra></extra>",
        )
        fig3.add_trace(go.Bar(**shared, y=pos, showlegend=True))
        fig3.add_trace(go.Bar(**shared, y=neg, showlegend=False, hoverinfo="skip"))

    period_net_valid = [
        v for lbl, v in zip(data.period_labels, data.period_net) if lbl not in data.missing_set
    ]
    for i, (sx, sy) in enumerate(split_by_missing(data.period_labels, data.period_net, data.missing_set)):
        fig3.add_trace(go.Scatter(
            x=sx,
            y=sy,
            name="整體合計",
            legendgroup="period_net",
            showlegend=(i == 0),
            mode="lines+markers",
            line=dict(width=2, color="#1e293b", dash="dot"),
            marker=dict(size=4),
            hovertemplate=" <extra></extra>",
        ))

    if len(period_net_valid) >= 3:
        mean = np.mean(period_net_valid)
        std = np.std(period_net_valid)
        for band_val, band_name, band_color in [
            (mean + std, "+1σ", "rgba(239,68,68,0.5)"),
            (mean, "均值", "rgba(100,116,139,0.6)"),
            (mean - std, "−1σ", "rgba(34,197,94,0.5)"),
        ]:
            fig3.add_hline(
                y=band_val,
                line_width=1, line_dash="dash", line_color=band_color,
                annotation_text=band_name,
                annotation_position="right",
                annotation_font_size=10,
            )

    layout3 = {**LAYOUT_BASE, "barmode": "relative", "height": 560, "margin": dict(t=100, b=40, l=60, r=40)}
    layout3["legend"] = dict(
        orientation="h",
        yanchor="bottom", y=1.02,
        xanchor="left", x=0,
        bgcolor=LEGEND_BG,
        font=dict(size=11),
        entrywidth=110,
        entrywidthmode="pixels",
    )
    fig3.update_layout(
        **layout3,
        yaxis=dict(
            title=f"買賣超（{data.unit_suffix}）",
            gridcolor=GRID_COLOR,
            tickformat=",.2f" if params.unit == "value_oku" else ",",
            zeroline=True, zerolinecolor=NEU_ZERO_COLOR, zerolinewidth=1.5,
        ),
        xaxis=build_period_xaxis(data.period_labels, params.split),
    )
    add_missing_markers(fig3, data.missing_labels, data.period_labels, params.split)

    render_chart_with_panel(
        fig3, data.panel_tab3, "tab3", data.cat_colors,
        unit=params.unit, unit_suffix=data.unit_suffix,
        cat_order=data.cat_list, height=560, n_cats=len(data.cat_list),
        coverage_json=data.coverage_json,
    )


def render_tab4(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    st.caption("外資／投信／自營各期買賣超合計對比，觀察同步 / 背離。滑鼠移至圖表查看數據與億元估算。")
    foreign_net = [sum(data.period_data[c]["foreign"][i] for c in data.cat_list) for i in range(len(data.period_labels))]
    invest_net = [sum(data.period_data[c]["invest"][i] for c in data.cat_list) for i in range(len(data.period_labels))]
    dealer_net = [sum(data.period_data[c]["dealer"][i] for c in data.cat_list) for i in range(len(data.period_labels))]

    fig4 = go.Figure()
    _bar_trace(fig4, foreign_net, "外資合計", "#2563eb", "foreign", data.period_labels)
    _bar_trace(fig4, invest_net, "投信合計", "#8b5cf6", "invest", data.period_labels)
    _bar_trace(fig4, dealer_net, "自營合計", "#f97316", "dealer", data.period_labels)
    fig4.add_hline(y=0, line_width=1, line_color=NEU_ZERO_COLOR, line_dash="dot")

    layout4 = {
        **LAYOUT_BASE,
        "barmode": "overlay",
        "height": 520,
        "yaxis": dict(
            title=f"買賣超（{data.unit_suffix}）",
            tickformat=",.2f" if params.unit == "value_oku" else ",",
            gridcolor=GRID_COLOR,
        ),
        "legend": dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            bgcolor=LEGEND_BG,
            font=dict(size=12),
            tracegroupgap=0,
            itemwidth=80,
            entrywidth=120,
            entrywidthmode="pixels",
        ),
        "margin": dict(t=80, b=40, l=60, r=80),
    }
    fig4.update_layout(**layout4)
    fig4.update_xaxes(**build_period_xaxis(data.period_labels, params.split))
    add_missing_markers(fig4, data.missing_labels, data.period_labels, params.split)
    render_chart_with_panel(
        fig4, data.panel_tab4, "tab4", data.cat_colors,
        unit=params.unit, unit_suffix=data.unit_suffix,
        cat_order=data.cat_list, height=520, n_cats=0,
        coverage_json=data.coverage_json,
    )

    if len(data.period_labels) >= 2:
        sync = sum(1 for f, t in zip(foreign_net, invest_net) if (f > 0 and t > 0) or (f < 0 and t < 0))
        div = sum(1 for f, t in zip(foreign_net, invest_net) if (f > 0 and t < 0) or (f < 0 and t > 0))
        total_periods = len([f for f, t in zip(foreign_net, invest_net) if f != 0 or t != 0])
        if total_periods > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("同向操作期數", f"{sync}")
            c2.metric("背離操作期數", f"{div}")
            c3.metric("同向率", f"{sync/total_periods*100:.0f}%" if total_periods else "—")


def render_tab5(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    start_str = params.start_date.strftime("%Y-%m-%d")
    end_str = params.end_date.strftime("%Y-%m-%d")

    if len(data.period_labels) < 2:
        st.info("需要至少 2 個期間才能顯示輪動摘要。請擴大日期區間或換用較細的時間分組。")
        return

    st.subheader("輪動摘要")
    first_vals = {cat: data.period_data[cat]["raw"][0] for cat in data.cat_list}
    last_vals = {cat: data.period_data[cat]["raw"][-1] for cat in data.cat_list}

    diffs = {cat: last_vals[cat] - first_vals[cat] for cat in data.cat_list}
    gainers = sorted([(c, d) for c, d in diffs.items() if d > 0], key=lambda x: x[1], reverse=True)
    losers = sorted([(c, d) for c, d in diffs.items() if d < 0], key=lambda x: x[1])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**▲ 資金流入（相較首期）**")
        for cat, diff in gainers[:5]:
            st.markdown(f"- {cat}：{_color_num(diff, params.unit, data.unit_suffix)}", unsafe_allow_html=True)
        if not gainers:
            st.markdown("- 無明顯流入")
    with col2:
        st.markdown("**▼ 資金流出（相較首期）**")
        for cat, diff in losers[:5]:
            st.markdown(f"- {cat}：{_color_num(diff, params.unit, data.unit_suffix)}", unsafe_allow_html=True)
        if not losers:
            st.markdown("- 無明顯流出")

    if gainers and losers:
        st.info(f"**資金移轉方向：** {losers[0][0]} → {gainers[0][0]}")

    st.subheader("資金動能評分")
    st.caption("統計各類股最近連續買超（🔥）或賣超（🧊）期數，反映動能強度。")

    max_possible_streak = len(data.period_labels)
    momentum_rows = []
    for cat in data.cat_list:
        raw = data.period_data[cat]["raw"]
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
            bar_pct = int(streak / max(max_possible_streak, 1) * 100)
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
                "最新期量體": (f"{last_v:+,.2f} {data.unit_suffix}" if params.unit == "value_oku"
                               else f"{last_v:+,.0f} {data.unit_suffix}"),
            })

    momentum_rows.sort(key=lambda x: x["連續期數"], reverse=True)
    if momentum_rows:
        mom_df = pd.DataFrame(momentum_rows)
        st.write(
            mom_df.to_html(escape=False, index=False, classes="momentum-table", border=0),
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

    st.subheader("輪動變化率排名")
    st.caption(f"最近一期（{data.period_labels[-1]}）vs 上期（{data.period_labels[-2]}）買賣超變化。")

    chg_rows = []
    for cat in data.cat_list:
        raw = data.period_data[cat]["raw"]
        prev, curr = raw[-2], raw[-1]
        abs_chg = curr - prev
        if prev != 0:
            pct_chg = abs_chg / abs(prev) * 100
            pct_str = f"{pct_chg:+.1f}%"
        else:
            pct_str = "—" if curr == 0 else ("新增" if curr > 0 else "新增賣超")
        if abs_chg != 0:
            chg_rows.append({
                "類股": cat,
                "上期": prev,
                "本期": curr,
                "變化量": abs_chg,
                "變化率": pct_str,
            })

    chg_rows.sort(key=lambda x: x["變化量"], reverse=True)
    if chg_rows:
        chg_df = pd.DataFrame(chg_rows)
        num_cols = ["上期", "本期", "變化量"]
        num_fmt_str = "{:+,.2f}" if params.unit == "value_oku" else "{:+,.0f}"
        fmt = {c: (lambda v, _f=num_fmt_str: _f.format(v)) for c in num_cols}
        st.dataframe(
            chg_df.style.format(fmt).map(_style_num_col, subset=num_cols),
            width="stretch", hide_index=True,
        )
    else:
        st.caption("兩期間無變化")

    h_tkrs = [tk for cat in data.cat_list for tk in data.universe_cats.get(cat, {}).keys()]
    h_rows = load_broker_from_db(h_tkrs, start_str, end_str) if h_tkrs else []
    if h_rows:
        st.subheader("籌碼集中度 HHI")
        st.caption(
            "Herfindahl-Hirschman Index：HHI = Σ(券商買賣超佔比%)²。"
            "**>2500 高度集中（單一主力）**、1500-2500 適度集中、**<1500 分散**（散戶盤）。"
        )
        h_df = pd.DataFrame(h_rows)
        hhi_by_ticker = []
        for tk in h_tkrs:
            sub = h_df[h_df["ticker"] == tk]
            if sub.empty:
                continue
            abs_tot = sub["net_lots"].abs().sum() or 1
            hhi = ((sub.groupby("broker_name")["net_lots"].sum().abs() / abs_tot) ** 2).sum() * 10000
            days = sub["trade_date"].nunique()
            cat = next((c for c in data.cat_list if tk in data.universe_cats.get(c, {})), "?")
            hhi_by_ticker.append({
                "類股": cat,
                "代碼": tk,
                "公司": data.universe_cats.get(cat, {}).get(tk, tk),
                "HHI": hhi,
                "資料天數": days,
            })
        if hhi_by_ticker:
            hhi_df = pd.DataFrame(hhi_by_ticker).sort_values("HHI", ascending=False)
            st.dataframe(
                hhi_df.style.format({"HHI": "{:,.0f}"}).map(_hhi_bg, subset=["HHI"]),
                width="stretch", hide_index=True,
            )
        else:
            st.caption("無有效分點資料可計算 HHI")

    with st.expander("類股資金相關性矩陣"):
        st.caption("各類股每期買賣超的 Pearson 相關係數。+1 = 同步操作，-1 = 反向操作。")

        raw_df = pd.DataFrame(
            {cat: data.period_data[cat]["raw"] for cat in data.cat_list},
            index=data.period_labels,
        )
        valid = raw_df.loc[:, raw_df.std() > 0]
        if valid.shape[1] >= 2:
            corr = valid.corr()
            fig_corr = go.Figure(go.Heatmap(
                z=corr.values,
                x=list(corr.columns),
                y=list(corr.index),
                colorscale="RdBu",
                zmid=0, zmin=-1, zmax=1,
                text=np.round(corr.values, 2),
                texttemplate="%{text}",
                textfont=dict(size=10),
                hovertemplate="%{y} × %{x}<br>相關係數：%{z:.2f}<extra></extra>",
            ))
            fig_corr.update_layout(
                **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend", "margin")},
                height=max(400, len(valid.columns) * 35),
                xaxis=dict(tickangle=-45),
                margin=dict(t=40, b=120, l=120, r=20),
            )
            st.plotly_chart(fig_corr, width="stretch")
        else:
            st.caption("需要至少 2 個有效類股才能計算相關性")


def render_tab6(ctx: TabContext) -> None:
    data = ctx.data
    st.caption(
        "融資餘額 = 散戶槓桿部位；融券餘額 = 散戶做空部位。"
        "**融資↑ + 法人賣** = 散戶追高，籌碼轉差；"
        "**融資↓ + 法人買** = 散戶殺低，籌碼轉佳；"
        "**融券↑** = 空方壓力加重。（單位：張）"
    )

    m_db = load_margin_from_db(data.trading_dates)
    if not m_db:
        st.warning("融資融券 DB 無資料。請在左側「散戶情緒（融資融券）」expander 按「補抓融資融券」。")
        return

    by_date = {}
    for (tk, dt), v in m_db.items():
        if tk not in data.active_tickers:
            continue
        slot = by_date.setdefault(dt, {
            "margin_balance": 0.0, "margin_prev": 0.0,
            "margin_buy": 0.0, "margin_sell": 0.0,
            "short_balance": 0.0, "short_prev": 0.0,
            "short_sell": 0.0, "short_cover": 0.0,
        })
        for k in slot.keys():
            slot[k] += (v.get(k) or 0.0)

    sorted_dates = sorted(by_date.keys())
    if not sorted_dates:
        st.warning("當前選取類股於此區間無融資融券資料。")
        return

    mg_bal = [by_date[d]["margin_balance"] for d in sorted_dates]
    mg_chg = [by_date[d]["margin_balance"] - by_date[d]["margin_prev"] for d in sorted_dates]
    sh_bal = [by_date[d]["short_balance"] for d in sorted_dates]
    sh_chg = [by_date[d]["short_balance"] - by_date[d]["short_prev"] for d in sorted_dates]

    inst_dates = set(sorted_dates)
    inst_daily = {d: 0.0 for d in sorted_dates}
    db_data = load_from_db(sorted_dates)
    for (tk, dt), v in db_data.items():
        if tk in data.active_tickers and dt in inst_dates:
            inst_daily[dt] += v.get("total", 0.0) / 1000.0
    inst_net = [inst_daily[d] for d in sorted_dates]

    fig6 = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        row_heights=[0.55, 0.45],
        subplot_titles=("融資餘額 vs 法人買賣超", "融券餘額與空方壓力"),
    )
    fig6.add_trace(go.Scatter(
        x=sorted_dates, y=mg_bal, name="融資餘額",
        line=dict(color="#f59e0b", width=2),
        hovertemplate="%{x}<br>融資餘額：%{y:,.0f} 張<extra></extra>",
    ), row=1, col=1)
    fig6.add_trace(go.Bar(
        x=sorted_dates, y=inst_net, name="三大法人買賣超",
        marker_color=[POS_COLOR if v > 0 else NEG_COLOR for v in inst_net],
        opacity=0.55, yaxis="y2",
        hovertemplate="%{x}<br>法人：%{y:+,.0f} 張<extra></extra>",
    ), row=1, col=1)
    fig6.add_trace(go.Scatter(
        x=sorted_dates, y=sh_bal, name="融券餘額",
        line=dict(color="#8b5cf6", width=2),
        hovertemplate="%{x}<br>融券餘額：%{y:,.0f} 張<extra></extra>",
    ), row=2, col=1)
    fig6.add_trace(go.Bar(
        x=sorted_dates, y=sh_chg, name="融券變化",
        marker_color=[NEG_COLOR if v > 0 else POS_COLOR for v in sh_chg],
        opacity=0.55,
        hovertemplate="%{x}<br>融券變化：%{y:+,.0f} 張<extra></extra>",
    ), row=2, col=1)

    fig6.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
        height=640,
        yaxis=dict(title="融資餘額（張）", gridcolor=GRID_COLOR, tickformat=","),
        yaxis2=dict(title="法人買賣超（張）", overlaying="y", side="right", showgrid=False, tickformat=",+"),
        yaxis3=dict(title="融券餘額（張）", gridcolor=GRID_COLOR, tickformat=","),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    )
    st.plotly_chart(fig6, width="stretch")

    div_days = sum(1 for m, i in zip(mg_chg, inst_net) if (m > 0 and i < 0) or (m < 0 and i > 0))
    sync_days = sum(1 for m, i in zip(mg_chg, inst_net) if (m > 0 and i > 0) or (m < 0 and i < 0))
    c1, c2, c3 = st.columns(3)
    c1.metric("融資-法人 背離天數", f"{div_days}")
    c2.metric("融資-法人 同向天數", f"{sync_days}")
    c3.metric("最新融券餘額", f"{sh_bal[-1]:,.0f} 張", delta=f"{sh_chg[-1]:+,.0f}")


def render_tab7(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data
    start_str = params.start_date.strftime("%Y-%m-%d")
    end_str = params.end_date.strftime("%Y-%m-%d")

    st.caption(
        "類股成員股前 15 大券商買賣超聚合。**紅色券商名稱** = 外資券商。"
        "資料來源：HiStock 分點（當日，僅前 15 買方 + 前 15 賣方）。"
    )

    if not data.active_tickers:
        st.warning("當前類股無標的。")
        return

    b_rows = load_broker_from_db(list(data.active_tickers), start_str, end_str)
    if not b_rows:
        st.warning(
            "DB 無分點資料。左側「🏦 券商分點」按「📥 抓取今日分點」。"
            "HiStock 僅提供當日資料，需每日累積。"
        )
        return

    b_df = pd.DataFrame(b_rows)
    agg = b_df.groupby("broker_name", as_index=False).agg(
        net_lots=("net_lots", "sum"),
        buy_lots=("buy_lots", "sum"),
        sell_lots=("sell_lots", "sum"),
        days=("trade_date", "nunique"),
        tickers=("ticker", "nunique"),
    )
    agg["is_foreign"] = agg["broker_name"].apply(_is_foreign)
    agg = agg.sort_values("net_lots", ascending=False)

    col1, col2 = st.columns([0.6, 0.4])
    with col1:
        st.subheader(f"前 15 大買超券商（類股 {len(data.active_tickers)} 檔 × {b_df['trade_date'].nunique()} 天）")
        top = agg.head(15)
        fig_b = go.Figure(go.Bar(
            x=top["net_lots"],
            y=top["broker_name"],
            orientation="h",
            marker_color=[("#ef4444" if f else "#3b82f6") for f in top["is_foreign"]],
            hovertemplate="%{y}<br>買超 %{x:,.0f} 張<extra></extra>",
        ))
        fig_b.update_layout(
            **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
            height=520,
            yaxis=dict(autorange="reversed", gridcolor=GRID_COLOR),
            xaxis=dict(title="買超（張）", tickformat=",", gridcolor=GRID_COLOR, zeroline=True, zerolinecolor=NEU_ZERO_COLOR),
            showlegend=False,
        )
        st.plotly_chart(fig_b, width="stretch")

        st.subheader("前 15 大賣超券商")
        bot = agg.tail(15).iloc[::-1]
        fig_s = go.Figure(go.Bar(
            x=bot["net_lots"],
            y=bot["broker_name"],
            orientation="h",
            marker_color=[("#ef4444" if f else "#22c55e") for f in bot["is_foreign"]],
            hovertemplate="%{y}<br>賣超 %{x:,.0f} 張<extra></extra>",
        ))
        fig_s.update_layout(
            **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
            height=520,
            yaxis=dict(autorange="reversed", gridcolor=GRID_COLOR),
            xaxis=dict(title="賣超（張）", tickformat=",", gridcolor=GRID_COLOR, zeroline=True, zerolinecolor=NEU_ZERO_COLOR),
            showlegend=False,
        )
        st.plotly_chart(fig_s, width="stretch")

    with col2:
        st.subheader("券商 → 成員股分佈")
        all_brokers = agg["broker_name"].tolist()
        sel_broker = st.selectbox("選擇券商", options=all_brokers[:30], index=0)
        bk = b_df[b_df["broker_name"] == sel_broker].groupby("ticker", as_index=False).agg(
            net_lots=("net_lots", "sum"),
        )
        tk2name = {tk: nm for c in data.universe_cats.values() for tk, nm in c.items()}
        bk["name"] = bk["ticker"].map(lambda t: tk2name.get(t, t))
        bk["cat"] = bk["ticker"].map(lambda t: data.ticker_to_cat.get(t, "?"))
        bk["abs"] = bk["net_lots"].abs()
        bk = bk.sort_values("abs", ascending=False)
        if not bk.empty and bk["abs"].sum() > 0:
            fig_tm = go.Figure(go.Treemap(
                labels=bk["name"] + "<br>" + bk["net_lots"].map(lambda v: f"{v:+,.0f} 張"),
                parents=[""] * len(bk),
                values=bk["abs"],
                marker=dict(colors=[(POS_COLOR if v > 0 else NEG_COLOR) for v in bk["net_lots"]]),
                hovertemplate="%{label}<extra></extra>",
                textinfo="label",
            ))
            fig_tm.update_layout(height=540, margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig_tm, width="stretch")
        else:
            st.caption("該券商無個股資料")

    st.subheader("外資 vs 本土券商")
    f_net = agg[agg["is_foreign"]]["net_lots"].sum()
    d_net = agg[~agg["is_foreign"]]["net_lots"].sum()
    f_count = agg["is_foreign"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("外資券商 淨買賣超（張）", f"{f_net:+,.0f}")
    c2.metric("本土券商 淨買賣超（張）", f"{d_net:+,.0f}")
    c3.metric("外資券商進榜數", f"{f_count} / {len(agg)}")


def render_tab8(ctx: TabContext) -> None:
    data = ctx.data
    st.caption(
        "三大法人期貨淨多空口數（多空淨額）。**外資期貨淨空 + 現貨賣超** = 做空預期，"
        "**外資期貨淨多 + 現貨買超** = 看多加碼。"
        "契約：TXF 臺股期、EXF 電子期。"
    )
    f_rows = load_futures_from_db(data.trading_dates, ["TXF", "EXF"])
    if not f_rows:
        st.warning("期貨未平倉 DB 無資料。重新載入或擴大日期區間。")
        return

    f_df = pd.DataFrame(f_rows).sort_values("trade_date")
    contract_choice = st.radio("合約", ["TXF 臺股期", "EXF 電子期"], horizontal=True)
    cid = "TXF" if contract_choice.startswith("TXF") else "EXF"
    sub = f_df[f_df["contract"] == cid]
    if sub.empty:
        st.warning(f"{cid} 無資料")
        return

    pivot = sub.pivot_table(
        index="trade_date", columns="role",
        values="net_oi", aggfunc="sum",
    ).fillna(0)
    fig_fut = go.Figure()
    role_color = {"foreign": "#2563eb", "invest": "#8b5cf6", "dealer": "#f97316"}
    role_label = {"foreign": "外資", "invest": "投信", "dealer": "自營"}
    for role in ["foreign", "invest", "dealer"]:
        if role not in pivot.columns:
            continue
        fig_fut.add_trace(go.Bar(
            x=pivot.index, y=pivot[role],
            name=role_label[role],
            marker_color=role_color[role],
            opacity=0.8,
            hovertemplate=f"%{{x}}<br>{role_label[role]} 淨 %{{y:+,.0f}} 口<extra></extra>",
        ))
    fig_fut.add_hline(y=0, line_color=NEU_ZERO_COLOR, line_width=1, line_dash="dot")
    fig_fut.update_layout(
        **{k: v for k, v in LAYOUT_BASE.items() if k not in ("legend",)},
        barmode="group", height=480,
        yaxis=dict(title=f"{cid} 淨多空口數", tickformat=",", gridcolor=GRID_COLOR, zeroline=True, zerolinecolor=NEU_ZERO_COLOR),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="left", x=0),
    )
    st.plotly_chart(fig_fut, width="stretch")

    latest_day = pivot.index[-1]
    latest = pivot.iloc[-1]
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "外資淨多空（口）",
        f"{latest.get('foreign', 0):+,.0f}",
        delta=f"{(latest.get('foreign', 0) - pivot.iloc[-2].get('foreign', 0)):+,.0f}" if len(pivot) >= 2 else None,
    )
    c2.metric(
        "投信淨多空（口）",
        f"{latest.get('invest', 0):+,.0f}",
        delta=f"{(latest.get('invest', 0) - pivot.iloc[-2].get('invest', 0)):+,.0f}" if len(pivot) >= 2 else None,
    )
    c3.metric(
        "自營淨多空（口）",
        f"{latest.get('dealer', 0):+,.0f}",
        delta=f"{(latest.get('dealer', 0) - pivot.iloc[-2].get('dealer', 0)):+,.0f}" if len(pivot) >= 2 else None,
    )
    st.caption(f"資料日期：{latest_day}")


def render_detail(ctx: TabContext) -> None:
    params = ctx.params
    data = ctx.data

    with st.expander("個股明細（全期合計）"):
        detail_db = load_from_db(data.trading_dates)
        detail_agg = aggregate_by_category(detail_db, data.trading_dates, data.universe_cats, data.ticker_to_cat)

        drill_cat = st.selectbox(
            "篩選類股（全選顯示所有）",
            options=["（全部）"] + data.cat_list,
            index=0,
            key="drill_cat",
        )

        detail_scale = _unit_scale(params.unit)
        detail_fk = _key_for_unit("foreign", params.unit)
        detail_ik = _key_for_unit("invest", params.unit)
        detail_dk = _key_for_unit("dealer", params.unit)

        qfii_latest = {}
        if data.trading_dates:
            q = load_qfii_from_db([data.trading_dates[-1]])
            for (tk, _dt), v in q.items():
                qfii_latest[tk] = v
        tdcc_latest = load_tdcc_latest(list(data.active_tickers))

        rows = []
        for cat in data.cat_list:
            if drill_cat != "（全部）" and cat != drill_cat:
                continue
            agg_vals = detail_agg[cat]
            for ticker, sdat in sorted(
                agg_vals["stocks"].items(), key=lambda x: x[1]["shares"], reverse=True
            ):
                name = data.universe_cats[cat].get(ticker, ticker)
                if params.unit == "shares":
                    stock_disp = sdat["shares"]
                elif params.unit == "value_oku":
                    stock_disp = sdat["value"] / 1e5
                else:
                    stock_disp = sdat["value"]
                q = qfii_latest.get(ticker, {})
                fpct = q.get("foreign_pct", 0)
                rpct = q.get("remaining_pct", 0)
                lpct = q.get("limit_pct", 0)
                warn = "🔴" if rpct and rpct < 5 else ("🟡" if rpct and rpct < 15 else "")
                td = tdcc_latest.get(ticker, {})
                big = td.get(15, {}).get("pct", 0)
                retail = sum((td.get(t, {}).get("pct", 0)) for t in range(1, 10))
                rows.append({
                    "類股": cat,
                    "代碼": ticker,
                    "公司": name,
                    f"外資（類股／{data.unit_suffix}）": agg_vals.get(detail_fk, 0.0) * detail_scale,
                    f"投信（類股／{data.unit_suffix}）": agg_vals.get(detail_ik, 0.0) * detail_scale,
                    f"自營（類股／{data.unit_suffix}）": agg_vals.get(detail_dk, 0.0) * detail_scale,
                    f"個股合計（{data.unit_suffix}）": stock_disp,
                    "外資持股%": f"{fpct:.2f}" if fpct else "—",
                    "剩餘%": f"{warn} {rpct:.2f}" if rpct else "—",
                    "上限%": f"{lpct:.0f}" if lpct else "—",
                    "大戶≥1000張%": f"{big:.2f}" if big else "—",
                    "散戶<5萬股%": f"{retail:.2f}" if retail else "—",
                })

        if rows:
            detail_df = pd.DataFrame(rows)
            num_cols_d = [
                f"外資（類股／{data.unit_suffix}）",
                f"投信（類股／{data.unit_suffix}）",
                f"自營（類股／{data.unit_suffix}）",
                f"個股合計（{data.unit_suffix}）",
            ]
            d_fmt_str = "{:+,.2f}" if params.unit == "value_oku" else "{:+,.0f}"
            fmt_d = {c: (lambda v, _f=d_fmt_str: _f.format(v)) for c in num_cols_d}
            st.dataframe(
                detail_df.style.format(fmt_d).map(_style_num_col, subset=num_cols_d),
                width="stretch", hide_index=True,
            )
            st.caption("外資／投信／自營欄位為類股級別合計；個股合計為該股票全期三大法人買賣超加總。")
        else:
            st.write("（無資料，請先更新）")
