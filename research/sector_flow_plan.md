# 主力資金類股輪動 — Streamlit 河流圖儀表板

## Context

追蹤台股主力（三大法人：外資/投信/自營）的資金在**不同主題類股**之間的比例移轉，以「100% 堆疊面積圖（比例河流）」呈現各類股資金份額隨時間的消長，判斷資金從哪一類移往哪一類。

確認設計決策：
- 視覺：100% 堆疊面積圖（Plotly 的 `stackgroup + groupnorm="percent"`）
- 載體：**Streamlit 本地 App**（`streamlit run` 開啟 localhost，個人每日查閱，無需分享）
- 持股資料：累積買賣超作 proxy（TWSE 僅外資有每日持股 %，投信/自營無）
- 更新方式：手動執行腳本時更新，Streamlit 提供 Sidebar 互動控制
- 標的範圍：Tier 1 AI 供應鏈精選（32 檔，9 主題）+ Tier 2 台股廣義主題（15 額外檔）

---

## 架構

```
research/
  stock_universe.json              ← NEW: 兩層標的清單 + 類股分類

scripts/
  sector_flow.py                   ← MAJOR UPDATE: 讀 universe JSON、加 --tier/--json 參數
  sector_flow_dashboard.py         ← NEW: Streamlit 儀表板主程式

依賴（新增）：
  pip install streamlit plotly
```

HTML 靜態輸出從計畫中**移除**，改以 Streamlit 互動介面取代。

---

## Step 1 — `research/stock_universe.json`

```json
{
  "companies": {
    "2408": {"name": "南亞科技"},
    "2344": {"name": "華邦電子"},
    "4256": {"name": "力積電"},
    "2337": {"name": "旺宏電子"},
    "2311": {"name": "日月光投控"},
    "2325": {"name": "矽品精密"},
    "6239": {"name": "力成科技"},
    "3037": {"name": "欣興電子"},
    "8046": {"name": "南亞電路板"},
    "3189": {"name": "景碩科技"},
    "3363": {"name": "上詮光纖"},
    "2455": {"name": "全新光電"},
    "4979": {"name": "華星光通"},
    "3081": {"name": "聯亞光電"},
    "3105": {"name": "穩懋半導體"},
    "6442": {"name": "光聖"},
    "4977": {"name": "眾達-KY"},
    "3163": {"name": "波若威"},
    "2345": {"name": "智邦科技"},
    "6223": {"name": "旺矽科技"},
    "3324": {"name": "雙鴻科技"},
    "3017": {"name": "奇鋐科技"},
    "2308": {"name": "台達電子"},
    "2301": {"name": "光寶科技"},
    "2382": {"name": "廣達電腦"},
    "3231": {"name": "緯創資通"},
    "2356": {"name": "英業達"},
    "5388": {"name": "中磊電子"},
    "2332": {"name": "友訊科技"},
    "4526": {"name": "東台精機"},
    "6488": {"name": "環球晶圓"},
    "6182": {"name": "合晶科技"},
    "2330": {"name": "台積電"},
    "2303": {"name": "聯華電子"},
    "5347": {"name": "世界先進"},
    "2454": {"name": "聯發科"},
    "2379": {"name": "瑞昱半導體"},
    "3034": {"name": "聯詠科技"},
    "6770": {"name": "力積電"},
    "2348": {"name": "海悅"},
    "8150": {"name": "南茂科技"},
    "2603": {"name": "長榮海運"},
    "2609": {"name": "陽明海運"},
    "2615": {"name": "萬海航運"},
    "2882": {"name": "國泰金控"},
    "2881": {"name": "富邦金控"},
    "2886": {"name": "兆豐金控"}
  },
  "tiers": {
    "ai_supply_chain": {
      "label": "AI 供應鏈精選",
      "categories": {
        "HBM/DRAM 記憶體":  ["2408","2344","4256","2337"],
        "先進封裝 CoWoS":   ["2311","2325","6239"],
        "ABF 載板":         ["3037","8046","3189"],
        "CPO 光源核心":     ["3363","2455","4979","3081","3105"],
        "CPO 光通周邊":     ["6442","4977","3163","2345","6223"],
        "AI 散熱/電源":     ["3324","3017","2308","2301"],
        "伺服器 ODM":       ["2382","3231","2356"],
        "網通基礎設施":     ["5388","2332","4526"],
        "矽晶圓/材料":      ["6488","6182"]
      }
    },
    "broad_themes": {
      "label": "台股廣義主題",
      "categories": {
        "晶圓代工":         ["2330","2303","5347"],
        "IC 設計 AI":       ["2454","2379","3034","6770"],
        "PCB 傳統":         ["2348","8150"],
        "航運":             ["2603","2609","2615"],
        "金融":             ["2882","2881","2886"]
      }
    }
  }
}
```

**Tier 1（ai_supply_chain）：32 檔，分 9 大主題**
**Tier 2（broad_themes）：額外 15 檔跨主題對照組**

注意：`6770` 與 `4256` 均為力積電，JSON 中保留兩個 key 供 tier 分類引用，實際抓取時去重。

---

## Step 2 — `scripts/sector_flow.py` 更新

### 新增 / 修改參數

| 參數 | 說明 | 預設 |
|------|------|------|
| `--tier` | `ai_supply_chain` / `broad_themes` / `all` | `ai_supply_chain` |
| `--json` | 輸出 `data/sector_flow_{start}_{end}.json` | 關閉 |
| 移除 `--html` | 改由 Streamlit 處理，不再產生靜態 HTML | — |

### 新增函式

| 函式 | 功能 |
|------|------|
| `load_universe(tier)` | 讀 `research/stock_universe.json`，回傳 `{cat: [tickers]}` 與 `{ticker: name}` |
| `aggregate_periods(data, date_groups)` | 回傳各期各類股 `{foreign, invest, dealer, total}` dict |
| `export_json(periods, meta, path)` | 輸出標準 JSON（供 Dashboard 或外部使用） |

### `load_universe` 取代硬編碼

現有 `CATEGORIES`、`ALL_TICKERS`、`TICKER_TO_CAT` 三個全域 dict 改由 `load_universe()` 動態產生，舊介面（無 `--tier`）行為不變。

### JSON 輸出格式

```json
{
  "meta": {
    "start": "2026-01-01",
    "end": "2026-04-16",
    "split": "month",
    "tier": "ai_supply_chain",
    "tier_label": "AI 供應鏈精選",
    "generated_at": "2026-04-16T10:30:00"
  },
  "categories": ["HBM/DRAM 記憶體", "先進封裝 CoWoS", "ABF 載板", "..."],
  "periods": [
    {
      "label": "2026-01",
      "date_range": ["2026-01-02", "2026-01-30"],
      "data": {
        "HBM/DRAM 記憶體": {"foreign": -5200000, "invest": 0, "dealer": -200000, "total": -5400000},
        "ABF 載板":         {"foreign": 3100000,  "invest": 0, "dealer":  800000, "total":  3900000}
      }
    }
  ]
}
```

---

## Step 3 — `scripts/sector_flow_dashboard.py`（Streamlit）

### 啟動方式

```bash
streamlit run scripts/sector_flow_dashboard.py
# → 自動開啟 http://localhost:8501
```

### UI 佈局

```
┌─ Sidebar ────────────────┐  ┌─ Main ────────────────────────────────────┐
│                           │  │                                            │
│  📅 日期區間              │  │  主力資金類股輪動                          │
│  開始：[2026-01-01 ▼]    │  │  AI 供應鏈精選 | 32 檔 | 合計 | 月份分組  │
│  結束：[2026-04-16 ▼]    │  │                                            │
│                           │  │  ┌──────────────────────────────────┐     │
│  🏦 法人類型              │  │  │ 100%┤▓▓▓▓▓░░░▒▒▒▒▒░░░░▒▒▒▒▒▒▒  │     │
│  ● 合計  ○ 外資           │  │  │     │ HBM  ABF  CPO  散熱  ODM  │     │
│  ○ 投信  ○ 自營           │  │  │   0%┤────────────────────────── │     │
│                           │  │  │      Jan   Feb   Mar   Apr      │     │
│  📦 標的範圍              │  │  └──────────────────────────────────┘     │
│  ● AI 供應鏈精選          │  │                                            │
│  ○ 台股廣義主題           │  │  輪動摘要                                  │
│  ○ 全部                   │  │  ▲ 流入：ABF 載板 +12.3%                  │
│                           │  │  ▼ 流出：CPO 光源核心 -9.2%               │
│  📊 時間分組              │  │  → 資金從 CPO 光源核心 移轉至 ABF 載板    │
│  ○ 週  ● 月               │  │                                            │
│                           │  │  個股明細（展開）                          │
│  [🔄 更新資料]            │  │  ┌──────────────────────────────────┐     │
│  （重新抓 TWSE）          │  │  │ 類股 | 代碼 | 公司 | 外資 | 合計│     │
│                           │  │  └──────────────────────────────────┘     │
└───────────────────────────┘  └────────────────────────────────────────────┘
```

### 圖表規格（Plotly）

```python
import plotly.graph_objects as go

fig = go.Figure()
for cat in categories:
    fig.add_trace(go.Scatter(
        x=period_labels,
        y=values[cat],          # 買超（負值設為 0）
        name=cat,
        stackgroup="one",
        groupnorm="percent",    # 100% 正規化
        fill="tonexty",
        line=dict(width=0.5, color=COLORS[cat]),
        fillcolor=COLORS[cat],
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "買賣超：%{customdata[0]:+,.0f} 股<br>"
            "佔比：%{y:.1f}%<extra></extra>"
        ),
        customdata=raw_values[cat],
    ))

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0f172a",
    plot_bgcolor="#0f172a",
    hovermode="x unified",
    yaxis=dict(ticksuffix="%", range=[0, 100]),
)
st.plotly_chart(fig, use_container_width=True)
```

### 顏色方案（9 類股）

| 類股 | 顏色 |
|------|------|
| HBM/DRAM 記憶體 | `#3b82f6`（藍） |
| 先進封裝 CoWoS  | `#8b5cf6`（紫） |
| ABF 載板        | `#06b6d4`（青） |
| CPO 光源核心    | `#f59e0b`（琥珀） |
| CPO 光通周邊    | `#f97316`（橙） |
| AI 散熱/電源    | `#ef4444`（紅） |
| 伺服器 ODM      | `#10b981`（綠） |
| 網通基礎設施    | `#84cc16`（草綠） |
| 矽晶圓/材料     | `#94a3b8`（灰） |

### Streamlit 快取策略

```python
@st.cache_data(ttl=3600)
def load_data(start, end, split, tier):
    """從 SQLite 讀取並聚合，避免重複計算"""
    ...

# Sidebar「更新資料」按鈕
if st.sidebar.button("🔄 更新資料"):
    st.cache_data.clear()
    fetch_missing_dates(start, end)   # 呼叫 sector_flow.ensure_data()
    st.rerun()
```

---

## 執行指令

```bash
# 安裝依賴（只需一次）
pip install streamlit plotly

# 啟動 Dashboard
streamlit run scripts/sector_flow_dashboard.py

# 純資料更新（不啟動 UI）
python3 scripts/sector_flow.py \
  --start 2026-01-01 --end 2026-04-16 \
  --split month --tier ai_supply_chain

# 匯出 JSON（備用）
python3 scripts/sector_flow.py \
  --start 2026-01-01 --end 2026-04-16 \
  --split month --tier all --json
```

---

## 不改動

- `fetch_institutional.py`（原始抓取邏輯）
- SQLite DB schema（`institutional_flow` 表不改）
- Markdown 輸出（`sector_flow_*.md` 繼續產生）
- 現有 `sector_flow.py` 命令列介面（`--start/--end/--split/--no-fetch` 參數不變）

---

## 驗證清單

- [ ] `pip install streamlit plotly` 成功
- [ ] `stock_universe.json` 格式正確，`load_universe()` 可讀取兩層
- [ ] `sector_flow.py --tier ai_supply_chain` 抓取 32 檔（去重後）T86 資料
- [ ] `streamlit run` 無錯誤，localhost:8501 開啟
- [ ] 100% 堆疊面積圖渲染，X 軸月份，Y 軸 0–100%，深色主題
- [ ] Sidebar 法人切換（外資/投信/自營/合計）圖表即時更新
- [ ] Sidebar 日期區間/Tier/分組切換正常
- [ ] Hover tooltip：類股名 + 買賣超絕對值 + 佔比 %
- [ ] 輪動摘要文字正確（▲流入 / ▼流出 / → 移轉判斷）
- [ ] 個股明細表格可展開
- [ ] 「更新資料」按鈕清除快取並重新抓 TWSE

---

## AI 執行 Guideline

> 本節供 AI Agent 實作時遵循，確保品質與一致性。

### 實作順序（不可打亂）

```
1. research/stock_universe.json        ← 先建，後續兩個步驟依賴此檔
2. scripts/sector_flow.py              ← 更新，需能單獨執行不依賴 Streamlit
3. scripts/sector_flow_dashboard.py   ← 最後，依賴前兩步
```

### 每步完成後的驗證指令

```bash
# Step 1 完成後
python3 -c "
import json; d = json.load(open('research/stock_universe.json'))
t1 = d['tiers']['ai_supply_chain']['categories']
all_t = [t for cats in t1.values() for t in cats]
print(f'Tier1 類股數: {len(t1)}, 標的數: {len(set(all_t))}')
"
# 預期輸出：Tier1 類股數: 9, 標的數: 32

# Step 2 完成後
python3 scripts/sector_flow.py \
  --start 2026-04-01 --end 2026-04-16 \
  --split none --tier ai_supply_chain --no-fetch
# 預期：印出類股合計表，無 Python 錯誤

# Step 3 完成後
streamlit run scripts/sector_flow_dashboard.py --server.headless true &
sleep 5 && curl -s http://localhost:8501 | grep -q "streamlit" && echo "OK"
```

### 關鍵實作約束

| 約束 | 說明 |
|------|------|
| `sector_flow.py` 向後相容 | 現有 `--start/--end/--split/--no-fetch` 行為不變 |
| 負值處理 | 河流圖只計 `total > 0` 的類股；負值在圖中設為 `0`，但 tooltip 仍顯示真實值 |
| 資料快取 | `@st.cache_data(ttl=3600)` 包住 SQLite 查詢，UI 切換不重打 API |
| 去重 | `6770`（力積電）與 `4256`（力積電）在抓資料時取 unique ticker set |
| 顏色固定 | 每個類股顏色硬編碼，Tier 切換後顏色不變（避免視覺混亂） |
| 深色主題 | Plotly `template="plotly_dark"` + `paper_bgcolor="#0f172a"`（與現有 JSX 一致） |
| 中文字型 | Plotly layout 加 `font=dict(family="PingFang TC, Microsoft JhengHei, sans-serif")` |

### 禁止事項

- 不在 `sector_flow_dashboard.py` 內直接呼叫 TWSE API；API 呼叫一律透過 `sector_flow.ensure_data()`
- 不修改 SQLite DB schema
- 不刪除 `sector_flow.py` 的 Markdown 輸出邏輯
- 不在 Streamlit 內引入 React/JSX/Babel

### 錯誤處理規範

| 情境 | 處理方式 |
|------|---------|
| TWSE API 無回應 | `st.warning("TWSE API 無回應，使用快取資料")` 繼續顯示舊資料 |
| 某類股當期無資料 | 設為 `0`，不拋例外 |
| `stock_universe.json` 不存在 | `st.error("找不到 research/stock_universe.json")` 後 `st.stop()` |
| 日期區間無任何交易日 | `st.warning("選定區間無交易資料")` 後 `st.stop()` |

---

版本：2.0 | 更新：2026-04-16（載體改為 Streamlit；移除靜態 HTML 輸出）
