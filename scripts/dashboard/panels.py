import json
from typing import Optional

import streamlit.components.v1 as components

from dashboard.helpers import NEG_COLOR, NEU_COLOR, POS_COLOR

# ── 共用：hover-panel HTML component 的固定 CSS / JS ──────────
_PANEL_CSS = """
  body { margin:0; padding:0; background:#f1f5f9; font-family: 'PingFang TC', 'Microsoft JhengHei', sans-serif; }
  #panel {
    min-height: 40px;
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 6px;
    font-size: 12px;
    color: #1e293b;
    overflow: hidden;
  }
  #panel-header {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 6px;
    font-weight: 600;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 4px;
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 12px;
    flex-wrap: wrap;
  }
  #panel-body {
    display: grid;
    grid-template-columns: repeat(3, minmax(330px, 1fr));
    gap: 10px;
  }
  #panel-body > div {
    min-width: 0;
    max-width: none;
  }
  #panel-body.tab4-body {
    display: flex;
    gap: 6px;
  }
  #panel-body.tab4-body > div {
    flex: 1 1 0;
    min-width: 90px;
  }
  #chart { width:100%; }
  .hoverlayer .hovertext { display: none !important; }
  .hoverlayer .spikeline { display: none !important; }
"""

# 依賴 panel_js 提供的 POS_COLOR/NEG_COLOR/NEU_COLOR/UNIT_SUFFIX/formatVal。
_PANEL_JS_HELPERS = """
function orderedCatsForLabel(label) {
    if (!panelData[label]) return [];
    var ordered = catOrder.filter(function(cat) {
        return panelData[label][cat] !== undefined;
    });
    return ordered.length ? ordered : Object.keys(panelData[label]);
}

function tab3TotalMeta(label) {
    var cats = orderedCatsForLabel(label);
    if (!cats.length) return '';
    var total = cats.reduce(function(sum, cat) {
        return sum + (panelData[label][cat].raw || 0);
    }, 0);
    var color = total > 0 ? POS_COLOR : (total < 0 ? NEG_COLOR : NEU_COLOR);
    return '整體合計：<b style="color:' + color + '">' + formatVal(total) + ' ' + UNIT_SUFFIX + '</b>';
}
"""

_PANEL_VLINE_JS = """
var VLINE_NAME = '__hover_vline__';
function setVLine(xVal) {
    var layout = chartEl.layout || {};
    var shapes = (layout.shapes || []).filter(function(s) { return s.name !== VLINE_NAME; });
    if (xVal !== null && xVal !== undefined) {
        shapes.push({
            name: VLINE_NAME,
            type: 'line',
            xref: 'x', yref: 'paper',
            x0: xVal, x1: xVal,
            y0: 0, y1: 1,
            line: { color: 'rgba(71,85,105,0.75)', width: 2.5, dash: 'dot' },
            layer: 'above',
        });
    }
    Plotly.relayout(chartEl, {shapes: shapes});
}

chartEl.on('plotly_hover', function(eventData) {
    if (!eventData || !eventData.points || !eventData.points.length) return;
    var label = eventData.points[0].x;
    if (label === undefined || label === null) return;
    updatePanel(String(label));
    setVLine(label);
});
chartEl.on('plotly_unhover', function() {
    setVLine(null);
});
"""

_PANEL_EXTRA_KEY = {"tab1": "pos", "tab3": "pos", "tab2": "cumsum"}


def render_chart_with_panel(
    fig,
    panel_data_json: str,
    tab_mode: str,
    cat_colors: dict,
    *,
    unit: str,
    unit_suffix: str,
    cat_order: Optional[list[str]] = None,
    height: int = 500,
    n_cats: int = 0,
    coverage_json: str = "{}",
) -> None:
    fig_json = fig.to_json()
    cat_order_json = json.dumps(cat_order or [], ensure_ascii=False)

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
    var UNIT_SUFFIX = '{unit_suffix}';
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

    _cat_card_js = """
        function renderCatCard(cat, color, mainLine, subLine) {
            var html = '<div style="margin-bottom:6px;padding:4px 8px;border-left:3px solid '+color+';background:rgba(255,255,255,0.6);border-radius:3px">';
            html += '<div style="font-weight:600;font-size:13px">'+cat+'</div>';
            html += '<div style="font-size:12px;margin-top:2px">'+mainLine+'</div>';
            html += '<div style="font-size:11px;color:#475569;margin-top:2px">'+subLine+'</div>';
            html += '</div>';
            return html;
        }
        function institutionSub(d) {
            return fmtSub(d.foreign||0,'外資') + '　' + fmtSub(d.invest||0,'投信') + '　' + fmtSub(d.dealer||0,'自營');
        }
    """

    if tab_mode == "tab1":
        build_panel_js = _cat_card_js + """
        function buildPanel(label, panelData, catColors, coverage) {
            var cats = orderedCatsForLabel(label);
            if (!cats.length) return '<div style="color:#94a3b8">無資料</div>';
            var totalAbs = cats.reduce(function(s,c){ return s + (panelData[label][c].pos||0); }, 0);
            var html = '';
            cats.forEach(function(cat) {
                var d = panelData[label][cat];
                var raw = d.raw || 0;
                var pct = totalAbs > 0 ? (d.pos / totalAbs * 100).toFixed(1) : '0.0';
                var main = '買賣超：' + fmtNum(raw) + '　強度佔比：<b>'+pct+'%</b>';
                html += renderCatCard(cat, catColors[cat] || '#64748b', main, institutionSub(d));
            });
            return html;
        }
        """
    elif tab_mode == "tab2":
        build_panel_js = _cat_card_js + """
        function buildPanel(label, panelData, catColors, coverage) {
            var cats = orderedCatsForLabel(label);
            if (!cats.length) return '<div style="color:#94a3b8">無資料</div>';
            var html = '';
            cats.forEach(function(cat) {
                var d = panelData[label][cat];
                var main = '累積買賣超：' + fmtNum(d.cumsum||0) + '　本期：' + fmtNum(d.raw||0);
                html += renderCatCard(cat, catColors[cat] || '#64748b', main, institutionSub(d));
            });
            return html;
        }
        """
    elif tab_mode == "tab3":
        build_panel_js = _cat_card_js + """
        function buildPanel(label, panelData, catColors, coverage) {
            var cats = orderedCatsForLabel(label);
            if (!cats.length) return '<div style="color:#94a3b8">無資料</div>';
            var html = '';
            cats.forEach(function(cat) {
                var d = panelData[label][cat];
                var main = '買賣超：' + fmtNum(d.raw||0);
                html += renderCatCard(cat, catColors[cat] || '#64748b', main, institutionSub(d));
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

    cat_colors_json = json.dumps(cat_colors)
    _script_head = (
        f"var figData = {fig_json};\n"
        f"var panelData = {panel_data_json};\n"
        f"var catColors = {cat_colors_json};\n"
        f"var catOrder = {cat_order_json};\n"
        f"var coverageData = {coverage_json};\n"
    )
    _script_trace_fix = """
figData.data.forEach(function(trace) {
    if (trace.meta && trace.meta.helper_trace) {
        trace.hoverinfo = 'skip';
        trace.hovertemplate = null;
        return;
    }
    trace.hovertemplate = '%{x}<extra></extra>';
    delete trace.hoverinfo;
});
figData.layout.hovermode = 'x';
"""
    _script_tab_mode = f"var tabMode = '{tab_mode}';\n"
    _script_plot = (
        "// legend 由 Python 側各 tab 自行設定，JS 不覆寫\n"
        "Plotly.newPlot('chart', figData.data, figData.layout, "
        "{responsive: true, displayModeBar: false});\n"
    )
    _script_panel_wire = """
var chartEl = document.getElementById('chart');
var panelHeader = document.getElementById('panel-header');
var panelBody = document.getElementById('panel-body');

if (tabMode === 'tab4') { panelBody.classList.add('tab4-body'); }

function updatePanel(labelStr) {
    var metaItems = [];
    if (tabMode === 'tab3') {
        metaItems.push('<span>' + tab3TotalMeta(labelStr) + '</span>');
    }
    if (tabMode !== 'tab4' && coverageData[labelStr] !== undefined) {
        var covPct = (coverageData[labelStr] * 100).toFixed(0) + '%';
        metaItems.push('<span>資料覆蓋率：<b style="color:#1e293b">' + covPct + '</b></span>');
    }
    var headerHtml = '<span>📅 ' + labelStr + '</span>';
    if (metaItems.length) {
        headerHtml += '<span style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;justify-content:flex-end;font-weight:400;color:#64748b">';
        headerHtml += metaItems.join('');
        headerHtml += '</span>';
    }
    panelHeader.innerHTML = headerHtml;
    panelBody.innerHTML = buildPanel(labelStr, panelData, catColors, coverageData);
}

var _labels = Object.keys(panelData);
if (_labels.length) {
    updatePanel(_labels[_labels.length - 1]);
}
"""

    html = (
        '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="utf-8">\n'
        '<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>\n'
        f"<style>{_PANEL_CSS}</style>\n</head>\n<body>\n"
        '<div id="panel">\n'
        '  <div id="panel-header">&#8592; 滑鼠移至圖表查看各類股數據</div>\n'
        '  <div id="panel-body"></div>\n'
        "</div>\n"
        '<div id="chart"></div>\n'
        "<script>\n"
        f"{_script_head}"
        f"{_PANEL_JS_HELPERS}"
        f"{_script_trace_fix}"
        f"{_script_tab_mode}"
        f"{_script_plot}"
        f"{panel_js}"
        f"{build_panel_js}"
        f"{_script_panel_wire}"
        f"{_PANEL_VLINE_JS}"
        "</script>\n</body>\n</html>\n"
    )
    components.html(html, height=total_h, scrolling=False)


def build_panel_data(
    tab_mode: str,
    period_labels: list[str],
    cat_list: list[str],
    period_data: dict,
) -> str:
    result: dict = {}
    for i, label in enumerate(period_labels):
        if tab_mode == "tab4":
            result[label] = {
                "foreign": sum(period_data[c]["foreign"][i] for c in cat_list),
                "invest":  sum(period_data[c]["invest"][i]  for c in cat_list),
                "dealer":  sum(period_data[c]["dealer"][i]  for c in cat_list),
            }
            continue

        extra_key = _PANEL_EXTRA_KEY[tab_mode]
        bucket = {}
        for cat in cat_list:
            d = period_data[cat]
            bucket[cat] = {
                "raw":     d["raw"][i],
                extra_key: d[extra_key][i],
                "foreign": d["foreign"][i],
                "invest":  d["invest"][i],
                "dealer":  d["dealer"][i],
            }
        result[label] = bucket
    return json.dumps(result, ensure_ascii=False)
