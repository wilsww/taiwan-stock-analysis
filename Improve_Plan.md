# 儀表板改善計畫

> 目標：Tab 1 / Tab 2 在「開盤無資料」日期（如春節、國定假日、系統缺漏）的圖表段不繪製，並保留 hover panel 資料完整。
> 狀態：2026-04-18 擬定
> 位置：`scripts/sector_flow_dashboard.py`

---

## 1. 目前問題

已嘗試：在缺漏日將 `pos_vals` / `cumsum_vals` 改成 `None` 並加 `connectgaps=False`（[sector_flow_dashboard.py:981-992, 1018-1031](scripts/sector_flow_dashboard.py)）。

實測結果：**Tab2 春節（1/27–2/3）圖表仍為連續線段**，未斷開。

### 推測根因

| # | 原因 | 說明 |
|---|-----|------|
| A | `fill="tozeroy"` 忽略 None | Plotly Scatter 的 fill 會把 None 區段當成 0，填色依舊跨越缺漏日，視覺上像未斷開 |
| B | `stackgroup="one"` + None 在 Tab1 被當 0 | stacked area 模式下，None 會被補 0 參與堆疊，該欄位高度仍是其他類股相加，不會留白 |
| C | x 軸為類別字串 | `period_labels` 是 `"2026-01-27"` 這類 string（非 datetime），Plotly 對 string 類別軸的 gap 處理不一致 |
| D | `split` 參數影響 | 若 `split=week/month`，缺漏日已被 aggregate 掉（不會出現在 `period_labels`），只有 `split=day` 會保留缺漏日 |

---

## 2. 修改方案（採多段 trace 切片法）

核心思路：**不靠 None 斷開，而是把連續有資料段切成多個 trace**，缺漏日完全不出現在任何 trace 的 x/y。同一類股多段共用 `legendgroup` + `showlegend=False`（只第一段顯示 legend）避免重複圖例。

### 實作步驟

#### STEP 1：抽出通用切段函式

在 `render_chart_with_panel` 上方新增：

```python
def split_by_missing(labels: list[str], values: list, missing_set: set) -> list[tuple[list, list]]:
    """把 labels/values 依 missing_set 切成多個連續有效段。
    回傳：[(seg_labels, seg_values), ...]，缺漏日完全不在任何段內。
    """
    segments = []
    cur_x, cur_y = [], []
    for lbl, val in zip(labels, values):
        if lbl in missing_set:
            if cur_x:
                segments.append((cur_x, cur_y))
                cur_x, cur_y = [], []
        else:
            cur_x.append(lbl)
            cur_y.append(val)
    if cur_x:
        segments.append((cur_x, cur_y))
    return segments
```

#### STEP 2：Tab2 改為多段 trace

現況（`sector_flow_dashboard.py:1016-1046`）：

```python
fig2 = go.Figure()
_missing_set2 = set(missing_labels)
for cat in cat_list:
    color = cat_colors[cat]
    cumsum_vals = [None if lbl in _missing_set2 else v for lbl, v in ...]
    fig2.add_trace(go.Scatter(x=period_labels, y=cumsum_vals, ...))
```

改為：

```python
fig2 = go.Figure()
_missing_set2 = set(missing_labels)
for cat in cat_list:
    color = cat_colors[cat]
    rgba_fill = "rgba({},{},{},0.15)".format(
        int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    )
    segments = split_by_missing(period_labels, period_data[cat]["cumsum"], _missing_set2)
    for i, (sx, sy) in enumerate(segments):
        fig2.add_trace(go.Scatter(
            x=sx, y=sy,
            name=cat,
            legendgroup=cat,
            showlegend=(i == 0),       # 僅首段顯示圖例
            mode="lines",
            line=dict(width=1.5, color=color),
            fill="tozeroy",
            fillcolor=rgba_fill,
            hovertemplate="%{x}<extra></extra>",
        ))
```

#### STEP 3：Tab1 stacked area 斷開策略

Tab1 因為 `stackgroup="one"`, groupnorm="percent"`，多段 trace 無法共用同一個 stackgroup（stacked 會把各段獨立堆疊，結果錯亂）。

**採替代方案：每段用獨立 stackgroup**

```python
fig1 = go.Figure()
_missing_set = set(missing_labels)

# 先算每個日期的總 abs（供 percent 轉換）
segments_per_cat = {cat: split_by_missing(period_labels, period_data[cat]["pos"], _missing_set) for cat in cat_list}
n_segments = len(segments_per_cat[cat_list[0]]) if cat_list else 0

for seg_idx in range(n_segments):
    for cat in cat_list:
        sx, sy = segments_per_cat[cat][seg_idx]
        fig1.add_trace(go.Scatter(
            x=sx, y=sy,
            name=cat,
            legendgroup=cat,
            showlegend=(seg_idx == 0),
            stackgroup=f"g{seg_idx}",        # 每段一組獨立堆疊
            groupnorm="percent",
            fill="tonexty",
            line=dict(width=0.5, color=cat_colors[cat]),
            fillcolor=cat_colors[cat],
            opacity=0.85,
            connectgaps=False,
            hovertemplate="%{x}<extra></extra>",
        ))
```

前提：所有 cat 的 `split_by_missing` 切段數一致（因為 missing_set 相同、labels 相同，所以切段一致）。若為 empty，特殊處理。

#### STEP 4：保留 hover panel 與垂直線

- `_panel_tab1` / `_panel_tab2` 的 JSON 結構不動（仍以 `period_labels` 為 key）—— 若使用者 hover 在缺漏日周邊的空白區，Plotly 不會觸發 hover 事件（因為該日無 trace 點），panel 停留在最後一個 hover 點。
- 垂直追蹤線由 JS `plotly_hover` 觸發，缺漏日無 trace 點也不會觸發，無需調整。

#### STEP 5：x 軸連續性處理

切段後預設 x 軸是 string 類別軸，會把所有 label（含缺漏日）保留為 category。若要讓缺漏日在 x 軸上仍佔位（視覺上留白）：

- **選項 A**（推薦）：保留 x 軸含缺漏日，圖形自然留白。不動 `period_labels`，只動 trace 的 `x`。
- **選項 B**：把缺漏日從 x 軸移除（`period_labels` 過濾後傳給 Plotly），圖形兩段自然相鄰（春節前後直接接起來，無留白）。

採選項 A：缺漏日有留白、有灰色虛線 marker（`add_missing_markers`），視覺上明確。

---

## 3. 驗收標準

| 情境 | 預期 |
|------|------|
| Tab1 春節（1/27–2/3） | 該 7 日整欄無面積填色，顯示灰色底色 + 既有灰虛線 marker |
| Tab2 春節 | 該 7 日無線段、無 fill，兩邊線段在 1/24 與 2/4 各自收尾/開始 |
| Hover panel | 仍正常顯示最後 hover 日資料；hover 在缺漏日無動作（不更新） |
| 垂直追蹤線 | 不出現在缺漏日 |
| Legend | 每類股只顯示一次（不因多段 trace 重複） |
| Tab3/Tab4 | 不變（bar chart 本身缺漏日 y=0，不需改） |

---

## 4. 風險 / 備案

- **多段 stackgroup 的 percent 計算**：若 Plotly 對不同 stackgroup 的 groupnorm 行為不如預期，改方案為單段 stackgroup + 每個 cat 缺漏日手動補 0 的小技巧（但此法會讓百分比分母改變，非理想）。先試 STEP 3 原方案。
- **切段數過多**：若缺漏日極多（如整年散落 50 天），trace 數 = cat × (缺漏段+1)，可能超過 100 個 trace。Plotly 可承受，但 legend 會爆炸 → 必須靠 `legendgroup + showlegend=False` 壓成每類股一個。
- **回歸測試**：實作後手動確認 split=day/week/month 三模式，以及 tier=ai_supply_chain / core 切換。

---

版本：1.0 | 2026-04-18
