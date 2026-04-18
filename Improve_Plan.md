# 儀表板優化計畫（不改功能 / 不改渲染結果）

> 目標：在**維持現有功能、視覺輸出、數值結果完全一致**的前提下，對 `scripts/sector_flow_dashboard.py`（Phase A+B 完成後 2016 行，Phase A 前 2022 行）做結構、效能、可讀性重構。
> 範圍：純重構，不新增 feature、不改 UI、不改 Plotly 視覺。
> 狀態：2026-04-18 擬定；Phase A+B+C 已實作（見 §6）；Phase D 為 AI agent 執行規格
> 版本：1.3

---

## 0. 總體原則

1. **行為保持（behavior-preserving）**：每個 step commit 後須視覺比對 dashboard 輸出（Tab1–Tab8、sidebar、scrubber、panel hover、missing markers）與 baseline 一致。
2. **小步提交**：每 STEP 獨立 commit，便於 bisect 回溯。
3. **分級執行**：先做低風險（常數抽取、變數合併、函式提升），再做中風險（模組架構重構）。
4. **禁用改動清單**：不動資料路徑、DB schema、Plotly trace 屬性語意、`period_data` 結構、`panel_data` JSON key 名稱。

---

## 1. 問題現況（審計結果摘要）

| 類別 | 項目數 | 代表位置 |
|------|-------|---------|
| 重複計算 / 重複宣告 | 8 | `_missing_set` × 3（L1167/1228/1283）、hex→rgba 迴圈內轉換（L1232）、`_today` 重複（L259/L393）、`trading_dates_in_range` 散落 5 處、`cached_load_universe` 解包 7 處、`_active_tkrs` × 4 |
| 重複結構（copy-paste） | 5 | `build_panel_data` tab1/tab3（L1118）、`build_panel_js` tab1/2/3（L838）、`yaxis2` 透明軸（L1202/L1262）、`LAYOUT_BASE.legend` 被各 tab override（L108）、`render_chart_with_panel` f-string 每次重建（L926） |
| Magic numbers / colors | 1 | `#cbd5e1`（15+ 次）、`rgba(148,163,184,0.22)`、`rgba(100,116,139,0.24)`、`rgba(241,245,249,0.85)`、`#94a3b8` 散落 |
| 函式位置不當 | 4 | `_bar_trace`（tab4 內，L1375）、`_hhi_bg`（tab5 內，L1590）、`_is_foreign`（tab7 內，L1760）、`_color_num` 依賴全域 `unit` |
| Type hints 缺失 | 1 | `_render_alerts`、`add_missing_markers`、`render_chart_with_panel(fig)` |
| 模組架構 | 1 | 頂層 2000 行直接執行，sidebar / data load / tabs 無函式包覆 |
| 效能 | 1 | `_render_alerts` 內 `load_from_db` 逐日呼叫（L519，O(N) DB 查詢） |

---

## 2. 重構計畫（分階段）

### Phase A — 低風險速戰（常數 / 變數合併） ✅ 已完成（commit `6ee7ec8`）

目標：消除 80% 重複，零行為風險。

#### STEP A1：建立共用常數區

位置：模組頂部（`LAYOUT_BASE` 附近）。

```python
# ── 共用顏色常數 ───────────────────────────────────────────
GRID_COLOR      = "#cbd5e1"
NEU_ZERO_COLOR  = "#94a3b8"          # zero line / neutral
MISSING_FILL    = "rgba(148,163,184,0.22)"
MISSING_BORDER  = "rgba(100,116,139,0.24)"
MISSING_TEXT    = "rgba(100,116,139,0.85)"
LEGEND_BG       = "rgba(241,245,249,0.85)"

# ── 共用 layout 片段 ───────────────────────────────────────
HIDDEN_Y2 = dict(overlaying="y", range=[0, 1], visible=False, fixedrange=True)
```

替換所有散落字面量。驗收：grep `"#cbd5e1"` 於 `sector_flow_dashboard.py` 回傳 0 筆（常數定義除外）。

**風險：低**

---

#### STEP A2：`_missing_set` 單一化

現況：L1167 / L1228 / L1283 各建一次。

改為：於 `missing_labels` 定義後（L589 附近）建立一次：

```python
_missing_set: set[str] = set(missing_labels)
```

Tab1/2/3 直接引用 `_missing_set`，刪除 `_missing_set2` / `_missing_set3`。

**風險：低**

---

#### STEP A3：`_today` 去重複

現況：L259 + L393 兩次 `_today = date.today()`（遮蔽）。

改為：只在 sidebar 最頂（L259）宣告一次。

**風險：低**

---

#### STEP A4：`cat_rgba` 預算表

現況：Tab2 迴圈 L1232-1234 每個 cat 每個 segment 重算 hex→int→rgba。

改為：於 `cat_colors` 定義後，一次預算：

```python
cat_rgba_015: dict[str, str] = {
    cat: "rgba({},{},{},0.15)".format(
        int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    )
    for cat, c in cat_colors.items()
}
```

Tab2 迴圈改用 `cat_rgba_015[cat]`。

**風險：低**

---

#### STEP A5：`cached_load_universe` 單次解包

現況：`cached_load_universe(tier)` 在 L439/506/533/1563/1657/1763/1939 各解包一次，視覺噪音。

改為：於 tier 選定後立即：

```python
_universe_cats, all_tickers, _ticker_to_cat, _universe_meta = cached_load_universe(tier)
```

後續全部引用此四變數，不再重解包。

**風險：低**（`@st.cache_data` 已確保不重算）

---

#### STEP A6：`active_tickers` 預算

現況：L507/534/1658/1764 各建一次相同 set comprehension。

改為：`cat_list` 篩選完成後（L459）：

```python
active_tickers: set[str] = {
    tk for cat in cat_list for tk in _universe_cats.get(cat, {}).keys()
}
```

四處引用 `active_tickers`。

**風險：低**

---

#### STEP A7：`trading_dates_in_range` 結果快取

現況：5 處以相同 `start_dt` / `end_dt` 重算。

改為：於 `start_date` / `end_date` 定義後一次計算：

```python
_trading_dates: list[date] = trading_dates_in_range(start_date, end_date)
```

同時消除 L501 / L536 / L1647 / L1879 / L1940 重複的 `datetime.strptime(start_str, "%Y-%m-%d").date()`。

**風險：低**

---

#### STEP A8：`_bar_trace` / `_hhi_bg` / `_is_foreign` 提升至模組頂層

現況：定義在 `with tab4:` / `with tab5:` / `with tab7:` 內部，每次 rerun 重新定義。

改為：移至模組頂層（與 `_color_num` 同區），加 type hints。

**風險：低**

---

#### STEP A9：`_color_num` 去全域依賴

現況：依賴全域 `unit` / `_unit_suffix`。

改為：改為 `_color_num(v: float, unit: str, suffix: str) -> str`，呼叫點顯式傳入。

**風險：低**

---

#### STEP A10：`scrubber` hover text 用 `_unit_fmt`

現況：L573 重複條件判斷。

改為：`text=[f"{v:+{_unit_fmt}}" for v in _sc_data]`。

**風險：低**

---

### Phase B — 中風險（結構重構） ✅ 已完成（commit `5a1a48a`）



目標：消除 copy-paste 結構，每步後完整視覺比對。

#### STEP B1：合併 `build_panel_data` tab1 / tab3 分支

現況：L1118-1125 tab1/tab3 幾乎相同欄位（`raw/pos/foreign/invest/dealer`），tab2 多 `cumsum`，tab4 獨立。

改為：

```python
def build_panel_data(tab: str, ...) -> dict:
    base = _common_fields(...)            # raw/pos/foreign/invest/dealer
    if tab == "tab2":
        base["cumsum"] = ...
    elif tab == "tab4":
        return _tab4_specific(...)
    return base
```

驗收：`panel_data_json` 輸出與 baseline 逐 key 相等（可用 `json.dumps(..., sort_keys=True)` diff）。

**風險：中**

---

#### STEP B2：`build_panel_js` 抽 `renderCatCard` JS helper

現況：L838-897 tab1/2/3 三個 JS 版本 90% 相同（僅 header 差異）。

改為：共用 JS helper：

```javascript
function renderCatCard(cat, d, color, bodyLines) {
    return `<div style="...">...${bodyLines.join("")}...</div>`;
}
```

三個 `buildPanel` 呼叫時傳入差異化的 `bodyLines`。

驗收：瀏覽器 DevTools inspect 每個 cat card 的 HTML 與 baseline diff 為 0。

**風險：中**（JS 字串 template 組裝錯誤會壞渲染）

---

#### STEP B3：`render_chart_with_panel` 固定 CSS / JS 抽常數

現況：L926-1092 每次呼叫重建 3KB f-string（含固定 CSS、`formatVal`/`fmtNum`/`fmtSub` JS helpers）。

改為：模組常數 `_PANEL_CSS`、`_PANEL_JS_HELPERS`，f-string 只插入 `{fig_json}` / `{panel_data_json}` / `{build_panel_js}`。

**風險：中**（HTML/JS escape 邊界需確認）

---

#### STEP B4：`LAYOUT_BASE.legend` 策略決定

現況：`LAYOUT_BASE` 有 `legend` 預設，但 Tab3/4/6/8 均 override，形成「預設存在但從未被用」的錯覺。

**選項 A**（推薦）：保持 `LAYOUT_BASE.legend` 但讓 Tab1/2 依賴此預設，確認 Tab3/4/6/8 的 override 是必要的（標示注釋說明原因）。
**選項 B**：移除 `LAYOUT_BASE.legend`，每 tab 顯式傳入。

選 A 以降低風險。

**風險：中**（選 B 時漏掉任一 fig 會改變 legend 位置）

---

### Phase C — 中高風險（效能） ✅ 已完成（commit `1a0a48d`）

#### STEP C1：`_render_alerts` 內 `load_from_db` 批次化

> 本節為 Codex 可直接執行的指令規格。**對照目前 HEAD（commit `5a1a48a` 之後）`scripts/sector_flow_dashboard.py`。**

**目標檔案**：`scripts/sector_flow_dashboard.py`
**目標函式**：`_render_alerts()`（目前位於 `def _render_alerts():` 起算區塊）

##### C1.1 問題定位

目前程式碼（Phase B 完成後）：

```python
# scripts/sector_flow_dashboard.py:516-539（_render_alerts 第 3 區塊）
if _margin_auto:
    try:
        _m_db = load_margin_from_db(_trading_dates)
        if _m_db:
            _by_date_a = {}
            for (tk, dt), v in _m_db.items():
                if tk not in active_tickers:
                    continue
                slot = _by_date_a.setdefault(dt, [0, 0])
                slot[0] += (v.get("margin_balance", 0) or 0) - (v.get("margin_prev", 0) or 0)
            _div = 0
            for dt in sorted(_by_date_a.keys()):
                m_chg = _by_date_a[dt][0]
                # 當日法人合計（股）
                i_db = load_from_db([dt])                       # ← 每個日期一次查詢
                i_net = sum(v.get("total", 0) for (tk, _d), v in i_db.items() if tk in active_tickers)
                if (m_chg > 0 and i_net < 0) or (m_chg < 0 and i_net > 0):
                    _div += 1
            _a3.metric("📊 融資-法人 背離天數", f"{_div}")
        else:
            _a3.metric("📊 融資-法人 背離", "—")
    except Exception:
        _a3.metric("📊 融資-法人 背離", "—")
```

瓶頸：`load_from_db([dt])` 在 `for dt in sorted(_by_date_a.keys())` 迴圈內每日一次呼叫。假設 90 天區間 → 90 次 SQLite connect + WHERE IN 查詢。

`load_from_db` 定義（`scripts/sector_flow.py:1437`）：

```python
def load_from_db(dates: list[str]) -> dict[tuple, dict]:
    # 回傳 {(ticker, trade_date): {foreign, invest, dealer, total, foreign_value, ...}}
```

可一次傳入所有日期，回傳 `(ticker, date) → dict`，本身已按日期索引，無需額外分組結構。

##### C1.2 精確改動

將上述 `if _margin_auto:` block 替換為：

```python
if _margin_auto:
    try:
        _m_db = load_margin_from_db(_trading_dates)
        if _m_db:
            _by_date_a: dict[str, float] = {}
            for (tk, dt), v in _m_db.items():
                if tk not in active_tickers:
                    continue
                _by_date_a[dt] = _by_date_a.get(dt, 0.0) + (
                    (v.get("margin_balance", 0) or 0)
                    - (v.get("margin_prev", 0) or 0)
                )

            # 一次批次查法人資料，按日期聚合
            _i_db_all = load_from_db(sorted(_by_date_a.keys())) if _by_date_a else {}
            _inst_net_by_date: dict[str, float] = {}
            for (tk, dt), v in _i_db_all.items():
                if tk not in active_tickers:
                    continue
                _inst_net_by_date[dt] = _inst_net_by_date.get(dt, 0.0) + v.get("total", 0)

            _div = 0
            for dt, m_chg in _by_date_a.items():
                i_net = _inst_net_by_date.get(dt, 0.0)
                if (m_chg > 0 and i_net < 0) or (m_chg < 0 and i_net > 0):
                    _div += 1
            _a3.metric("📊 融資-法人 背離天數", f"{_div}")
        else:
            _a3.metric("📊 融資-法人 背離", "—")
    except Exception:
        _a3.metric("📊 融資-法人 背離", "—")
```

細節要求：

1. **資料結構簡化**：原本 `_by_date_a[dt] = [margin_chg, 0]`（list 第二格從未使用）→ 改用 `dict[str, float]` 直接存 `margin_chg`。
2. **批次查詢**：`load_from_db(sorted(_by_date_a.keys()))` 單次呼叫取代 O(N) 次 `load_from_db([dt])`。
3. **聚合保持等價**：原迴圈對每個 `dt` 算 `sum(v.get("total", 0) for (tk, _d), v in i_db.items() if tk in active_tickers)`；新版先全量展開成 `_inst_net_by_date[dt] += v.get("total", 0)`，數學上等價（可交換加總）。
4. **排序不影響結果**：`_div` 計數與迭代順序無關，可直接 `for dt, m_chg in _by_date_a.items()` 取代 `for dt in sorted(_by_date_a.keys())`。
5. **Exception 路徑**：保留 `try/except Exception` 與 `"—"` / `"未啟用"` fallback，邏輯不動。
6. **`active_tickers` 過濾**：兩處（margin 側與 institutional 側）都要保留，**不可簡化成一邊過濾**，因為 `_m_db` 與 `_i_db_all` 的 ticker 集合可能不同。

##### C1.3 驗收（Codex 執行後須回報）

1. **語法與 import 檢查**

   ```bash
   python3 -m py_compile scripts/sector_flow_dashboard.py
   ```

2. **DB 查詢次數下降**：手動啟動 `streamlit run scripts/sector_flow_dashboard.py` 並勾選 sidebar「散戶情緒（融資融券）」顯示。開啟 sqlite trace 或暫時在 `load_from_db` 頂端插入 `print("load_from_db called with", len(dates), "dates")`（驗收後移除），確認原本 90 次下降為 1 次。

3. **數值等價**：`📊 融資-法人 背離天數` metric 必須與改動前完全相同（同一 tier / 同一日期區間 / 同一 unit）。建議手法：
   - Phase B commit（`5a1a48a`）checkout 一份，啟動 streamlit，截 `_a3` metric 數字。
   - 切回 Phase C 後再啟動，比對 `_a3` 數字完全相等。
   - 或以 pytest 拆出純函式測試（見 C1.4 選配）。

4. **其他 metric 不受影響**：`_a1`（TOP3 外資買超）、`_a2`（連續買超）、`_a4`（外資接近上限）渲染結果不得改變。

##### C1.4 選配：拆純函式並加 unit test（建議）

若時間允許，將核心聚合抽成純函式便於測試：

```python
def _margin_inst_divergence(
    margin_rows: dict[tuple[str, str], dict],
    inst_rows: dict[tuple[str, str], dict],
    active_tickers: set[str],
) -> int:
    by_date_margin: dict[str, float] = {}
    for (tk, dt), v in margin_rows.items():
        if tk not in active_tickers:
            continue
        by_date_margin[dt] = by_date_margin.get(dt, 0.0) + (
            (v.get("margin_balance", 0) or 0) - (v.get("margin_prev", 0) or 0)
        )

    by_date_inst: dict[str, float] = {}
    for (tk, dt), v in inst_rows.items():
        if tk not in active_tickers:
            continue
        by_date_inst[dt] = by_date_inst.get(dt, 0.0) + v.get("total", 0)

    return sum(
        1 for dt, m_chg in by_date_margin.items()
        if (m_chg > 0 and by_date_inst.get(dt, 0.0) < 0)
        or (m_chg < 0 and by_date_inst.get(dt, 0.0) > 0)
    )
```

並在 `_render_alerts` 中呼叫：

```python
_i_db_all = load_from_db(sorted({dt for (_, dt) in _m_db.keys()})) if _m_db else {}
_div = _margin_inst_divergence(_m_db, _i_db_all, active_tickers)
```

測試（放於 `tests/test_sector_flow_dashboard.py`，若目錄不存在可跳過）：

```python
def test_divergence_counts_opposite_signs():
    margin = {("2330", "2026-04-01"): {"margin_balance": 200, "margin_prev": 100}}  # +100
    inst   = {("2330", "2026-04-01"): {"total": -500}}                              # 背離
    assert _margin_inst_divergence(margin, inst, {"2330"}) == 1

def test_divergence_ignores_inactive_tickers():
    margin = {("9999", "2026-04-01"): {"margin_balance": 200, "margin_prev": 100}}
    inst   = {("9999", "2026-04-01"): {"total": -500}}
    assert _margin_inst_divergence(margin, inst, {"2330"}) == 0

def test_divergence_handles_missing_inst_date():
    margin = {("2330", "2026-04-01"): {"margin_balance": 200, "margin_prev": 100}}
    inst   = {}
    assert _margin_inst_divergence(margin, inst, {"2330"}) == 0
```

##### C1.5 Codex 提交規範

- **commit message 樣板**：

  ```text
  perf(sector_flow_dashboard): batch load_from_db in _render_alerts (C1)

  - replace per-date load_from_db([dt]) inside margin-divergence loop with a single batched call
  - collapse _by_date_a from dict[str, list] to dict[str, float]
  - preserve divergence count semantics: active_tickers filter applied on both margin and institutional sides; iteration order irrelevant
  ```

- **禁止一併處理**：不要在同一個 commit 中處理 Phase D、不要改動其他 tab、不要調整 `load_from_db` 簽章。
- **風險點須自我審閱**：
  - `_by_date_a` 外部是否被其他 tab / expander 使用？（當前不會，但若未來改寫須回查）
  - `active_tickers` 是否已在函式 scope 可見？（是，為模組層變數，見 `scripts/sector_flow_dashboard.py:473`）
  - 若 `_m_db` 為空，`_i_db_all` 必須維持空 dict，不可誤呼叫 `load_from_db([])`（SQLite placeholders 會為 0 個）。

**風險：中**（DB 回傳順序 / 分組邏輯需小心保持；見 C1.2 第 3、6 點）

---

### Phase D — 高收益架構重構（可選，最後做）

> 本節為 AI agent（Codex / Claude）可直接執行的指令規格。
> **必要前置**：Phase C 已合併、baseline 截圖已存檔、分支必須與 `main` 分離（建議 `refactor/phase-d1`、`refactor/phase-d2`）。
> **兩個 STEP 各自獨立 PR，不合併**，因為 D1 須先通過視覺回歸再進 D2。

#### STEP D1：抽 `render_sidebar()` 函式

##### D1.1 現況定位

目前（Phase C 合併後）`scripts/sector_flow_dashboard.py`：

- `scripts/sector_flow_dashboard.py:268-413` 為 `with st.sidebar:` 頂層區塊，直接 mutate 模組層變數 `start_date` / `end_date` / `institution_label` / `institution` / `unit_label` / `unit` / `tier_label_sel` / `tier` / `split_label` / `split` / `_preview_cats` / `_selected_cats` / `_fut_auto` / `_broker_auto` / `_margin_auto`。
- 其中 `_fut_auto` / `_broker_auto` / `_margin_auto` 於模組後段（tab 顯示、auto-fetch）使用；`tier_label_sel` 於 L454 `st.caption` 使用；其他參數於 `load_data` 與各 tab 廣泛引用。
- Sidebar 內部共有 4 個 `with st.expander:` 按鈕會呼叫 `st.rerun()`，其中「🔄 更新資料」會寫入 `st.session_state["last_update"]`。

`st.session_state` 使用盤點（D1 須全部保留，時序敏感）：
- `_qs` / `_qe`：快速區間按鈕寫入，下次 rerun 讀取作為 `date_input` 預設值。
- `last_update`：更新資料按鈕寫入，expander 內讀取顯示狀態。
- `db_initialized`（L417）、`auto_fetch_*`（L423）由模組層段使用。

##### D1.2 目標設計

在 `sector_flow_dashboard.py` 中**新增**（不拆獨立檔）以下 dataclass 與函式：

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SidebarParams:
    # 日期 / 顯示設定
    start_date: date
    end_date: date
    institution_label: str          # radio 原始顯示值（"合計" / "外資" / ...）
    institution: str                # INSTITUTION_MAP 映射後的 key
    unit_label: str                 # "金額（億元）" / "股數" / "金額（千元）"
    unit: str                       # UNIT_MAP 映射後的 key
    tier_label_sel: str
    tier: str
    split_label: str
    split: str
    # 類股篩選
    selected_cats: list[str]        # 空 list = 全選（保持原語意）
    # 可選 tab 開關
    margin_auto: bool
    broker_auto: bool
    fut_auto: bool


def render_sidebar() -> SidebarParams:
    """
    渲染 sidebar 所有 widget，封裝既有副作用：
    - st.session_state[_qs] / [_qe]：由快速區間按鈕寫入
    - st.session_state[last_update]：由「更新資料」按鈕寫入
    - _broker_auto 按鈕 → fetch_broker_today(...)
    - _margin_auto 按鈕 → ensure_margin_data(...)
    - 「從 TWSE 補抓缺漏日期」按鈕 → ensure_calendar + ensure_data
    所有 st.stop() / st.rerun() 行為保持原樣。
    """
    with st.sidebar:
        st.title("控制面板")
        # ... 將 L268-413 整段內容搬入 ...
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
```

模組頂層（L415 之後）改為：

```python
params = render_sidebar()
# 相容層（D1 階段保留，D2 時移除）：
start_date        = params.start_date
end_date          = params.end_date
institution_label = params.institution_label
institution       = params.institution
unit_label        = params.unit_label
unit              = params.unit
tier_label_sel    = params.tier_label_sel
tier              = params.tier
split_label       = params.split_label
split             = params.split
_selected_cats    = params.selected_cats
_margin_auto      = params.margin_auto
_broker_auto      = params.broker_auto
_fut_auto         = params.fut_auto
```

##### D1.3 精確改動步驟

1. **不動** L1-265（imports / 常數 / `cached_load_universe` / `load_data`）。
2. 在 `load_data` 函式之後、`with st.sidebar:` 之前，插入 `@dataclass` 與 `def render_sidebar()` 定義。
3. 把原 L268-413 `with st.sidebar:` 區塊**整段搬**進 `render_sidebar()` 函式體，不改內部任何邏輯、變數名、session_state key、`st.stop()` / `st.rerun()` 行為。
4. 於原 L268 位置插入 `params = render_sidebar()` 與相容層解包（D1.2 最後一段）。
5. 其他段落（資料載入、alerts、tabs）**完全不動**。
6. 確認 `_today` 在 sidebar 內有 `_today = date.today()`（L273）且函式 scope 內自足；沒有洩漏模組層需求。

##### D1.4 驗收

| 檢查 | 方法 |
|------|------|
| Python 語法 | `python3 -m py_compile scripts/sector_flow_dashboard.py` |
| Streamlit 啟動不 crash | `streamlit run scripts/sector_flow_dashboard.py`，首頁載入 |
| Widget 初值 | 每個 radio / selectbox / date_input / multiselect 的 `index` / `value` 與 pre-D1 一致 |
| 快速區間按鈕 | 點「30 天 / 90 天 / 半年 / 今年」，`date_input` 立即更新、`_qs`/`_qe` session_state 寫入 |
| 「補抓缺漏日期」按鈕 | 成功 / 失敗兩路徑都寫入 `last_update`；expander 內顯示同樣的成功 / 失敗訊息 |
| `_margin_auto` / `_broker_auto` / `_fut_auto` | 勾選後對應 tab 出現；unchecked 時 tab 消失 |
| 類股 preset | `dashboard_presets.json` 存在時選單能載入；選中後 `multiselect` 反映 preset 內容 |
| 資料新鮮度 caption | 🟢 / 🟡 / 🔴 / ⚪ 四種狀態顯示正確 |
| tab1-tab8 渲染 | 與 pre-D1 baseline 截圖逐張比對無差異 |

##### D1.5 提交規範

- **branch**：`refactor/phase-d1-sidebar`
- **commit message 樣板**：

  ```text
  refactor(sector_flow_dashboard): wrap sidebar in render_sidebar() (D1)

  - introduce frozen dataclass SidebarParams enumerating all sidebar-owned values
  - move L268-413 into render_sidebar() verbatim; no logic / session_state key changes
  - add compatibility unpack layer so downstream tab code (Phase D2 scope) continues to see module-level names
  ```

- **禁止**：改動 session_state key 名、改 widget `index` / `value` 預設、提早移除相容層、在同一 commit 內開始 D2。

##### D1.6 回滾策略

若視覺或互動行為與 baseline 不一致，`git revert` 整個 commit；因 D1 僅搬程式碼，回滾安全。

**風險：中高**（`st.session_state` 存取時序敏感，須完整回歸測試）

---

#### STEP D2：抽 `load_app_data(params)` 與 `render_tab_N(params, data)`

> **前置**：D1 已合併並完成視覺比對。
> **規模**：本 STEP 拆 3 個 sub-PR 進行，每個 sub-PR 獨立驗收。

##### D2.1 現況定位

Phase C 合併後：

- `scripts/sector_flow_dashboard.py:415-450`：資料載入副作用區（`init_db` / `auto_fetch_*` session flag / `ensure_*` 系列 / `load_data`）
- `scripts/sector_flow_dashboard.py:452-476`：單位字尾、`_selected_cats` 篩選、`_missing_set` / `active_tickers` / `_trading_dates` 預算
- `scripts/sector_flow_dashboard.py:478-551`：`_render_alerts()` 定義與呼叫
- `scripts/sector_flow_dashboard.py:553-589`：scrubber expander
- `scripts/sector_flow_dashboard.py:591-1162`：模組頂層 helpers（`build_missing_spans` / `build_period_xaxis` / `add_missing_markers` / `split_by_missing` / `add_transparent_xaxis_helper` / `_color_num` / `_style_num_col` / `_bar_trace` / `_hhi_bg` / `_is_foreign` / `render_chart_with_panel` / `_PANEL_CSS` 等 / `build_panel_data`）
- `scripts/sector_flow_dashboard.py:1164-2016`：Tab 宣告 + Tab1-8 + 個股明細 expander

##### D2.2 目標設計

**新增目錄結構**（不要提前拆太細，先以 3 檔為界）：

```text
scripts/
├── sector_flow_dashboard.py          # 僅 main() + SidebarParams + AppData + render_sidebar
├── sector_flow/
│   ├── __init__.py                   # 既有模組，不動
│   └── ... （既有業務邏輯）
└── dashboard/                         # 新增
    ├── __init__.py
    ├── panels.py                      # render_chart_with_panel / _PANEL_CSS / _PANEL_JS_HELPERS / _PANEL_VLINE_JS / build_panel_data / _PANEL_EXTRA_KEY
    ├── helpers.py                     # build_missing_spans / build_period_xaxis / add_missing_markers / split_by_missing / add_transparent_xaxis_helper / _color_num / _style_num_col / _bar_trace / _hhi_bg / _is_foreign / _FOREIGN_BROKER_KEYWORDS / GRID_COLOR 等色票常數 / HIDDEN_Y2 / LAYOUT_BASE
    └── tabs.py                        # render_tab1(ctx) ~ render_tab8(ctx) + render_alerts(ctx) + render_scrubber(ctx) + render_detail(ctx)
```

**新增** dataclass 承接資料載入結果：

```python
# sector_flow_dashboard.py
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
    trading_dates: list[date]
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
    """封裝 L415-450 資料載入副作用 + L452-476 預算 + panel_data 建立。"""
    ...
```

**tab render 簽章統一**：

```python
# dashboard/tabs.py
@dataclass(frozen=True)
class TabContext:
    params: SidebarParams
    data: AppData

def render_tab1(ctx: TabContext) -> None: ...
def render_tab2(ctx: TabContext) -> None: ...
# ... tab3-8 同樣
def render_alerts(ctx: TabContext) -> None: ...
def render_scrubber(ctx: TabContext) -> None: ...
def render_detail(ctx: TabContext) -> None: ...
```

**main() 樣貌**：

```python
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

    tab_labels = ["📊 資金強度佔比", "📈 累積買賣超（倉位變化）",
                  "📉 每期買賣超量體", "🔀 三大法人對比", "📋 輪動摘要"]
    if params.margin_auto: tab_labels.append("💳 散戶情緒（融資融券）")
    if params.broker_auto: tab_labels.append("🏦 券商動向")
    if params.fut_auto:    tab_labels.append("📈 期現連動")
    tabs = st.tabs(tab_labels)

    tab_idx = 5
    with tabs[0]: render_tab1(ctx)
    with tabs[1]: render_tab2(ctx)
    with tabs[2]: render_tab3(ctx)
    with tabs[3]: render_tab4(ctx)
    with tabs[4]: render_tab5(ctx)
    if params.margin_auto:
        with tabs[tab_idx]: render_tab6(ctx); tab_idx += 1
    if params.broker_auto:
        with tabs[tab_idx]: render_tab7(ctx); tab_idx += 1
    if params.fut_auto:
        with tabs[tab_idx]: render_tab8(ctx)

    render_detail(ctx)


if __name__ == "__main__" or True:   # streamlit 直接執行
    main()
```

##### D2.3 拆三個 sub-PR

**D2-A：搬 helpers.py / panels.py，主檔 import**

1. 新建 `scripts/dashboard/__init__.py`（空檔）。
2. 把下列程式碼**原封不動搬**進 `scripts/dashboard/helpers.py`：
   - 色票常數（`POS_COLOR` / `NEG_COLOR` / `NEU_COLOR` / `GRID_COLOR` / `NEU_ZERO_COLOR` / `MISSING_FILL` / `MISSING_BORDER` / `MISSING_TEXT` / `LEGEND_BG` / `HIDDEN_Y2` / `COLORS` / `DEFAULT_COLOR` / `INSTITUTION_MAP` / `UNIT_MAP` / `TIER_MAP` / `SPLIT_MAP` / `LAYOUT_BASE`）
   - Helper 函式（`build_missing_spans` / `_day_label_dt` / `build_period_xaxis` / `add_missing_markers` / `split_by_missing` / `add_transparent_xaxis_helper` / `_color_num` / `_style_num_col` / `_bar_trace` / `_hhi_bg` / `_is_foreign` / `_FOREIGN_BROKER_KEYWORDS`）
3. 把 `_PANEL_CSS` / `_PANEL_JS_HELPERS` / `_PANEL_VLINE_JS` / `render_chart_with_panel` / `_PANEL_EXTRA_KEY` / `build_panel_data` 搬進 `scripts/dashboard/panels.py`。
4. `scripts/sector_flow_dashboard.py` 頂部新增：
   ```python
   from dashboard.helpers import (
       POS_COLOR, NEG_COLOR, NEU_COLOR, GRID_COLOR, NEU_ZERO_COLOR,
       MISSING_FILL, MISSING_BORDER, MISSING_TEXT, LEGEND_BG, HIDDEN_Y2,
       COLORS, DEFAULT_COLOR, INSTITUTION_MAP, UNIT_MAP, TIER_MAP, SPLIT_MAP,
       LAYOUT_BASE, build_missing_spans, build_period_xaxis, add_missing_markers,
       split_by_missing, add_transparent_xaxis_helper,
       _color_num, _style_num_col, _bar_trace, _hhi_bg, _is_foreign,
   )
   from dashboard.panels import render_chart_with_panel, build_panel_data
   ```
5. **不改**其他邏輯；`render_chart_with_panel` / `build_panel_data` 須改為**接收所有相依**（原本隱式讀模組層 `period_labels` / `period_data` / `cat_list` / `unit` / `_unit_suffix` / `cat_colors`）→ 改顯式參數：
   ```python
   def build_panel_data(
       tab_mode: str,
       period_labels: list[str],
       cat_list: list[str],
       period_data: dict,
   ) -> str: ...

   def render_chart_with_panel(
       fig,
       panel_data_json: str,
       tab_mode: str,
       cat_colors: dict,
       *,
       unit: str,
       unit_suffix: str,
       cat_order: list[str] | None = None,
       height: int = 500,
       n_cats: int = 0,
       coverage_json: str = "{}",
   ) -> None: ...
   ```
6. 所有呼叫點（原 Tab1-Tab4）加上新參數。
7. 驗收：`streamlit run` 後 tab1-8 + panel hover 與 pre-D2-A baseline 完全一致。

**D2-B：抽 `load_app_data` + `main()` 骨架**

1. 新增 `@dataclass(frozen=True) class AppData` 於 `sector_flow_dashboard.py`（或拆 `dashboard/state.py`）。
2. 新增 `def load_app_data(params: SidebarParams) -> AppData`，把 L415-476 全部副作用搬進去。
3. 包一個臨時 `def main():`，其中 tab1-8 仍暫留 `with tabs[i]:` inline 區塊但全部讀 `data.*` 與 `params.*`。
4. 模組末尾加 `main()`。
5. **相容層拆除**：D1 保留的 `start_date = params.start_date` 等 15 行刪除；所有 Tab 內讀取改為 `ctx.params.start_date` 或 `ctx.data.active_tickers` 等。
6. 驗收：視覺回歸 + widget 互動全通過。

**D2-C：tabs.py 拆檔**

1. 將 `def render_alerts` / `render_scrubber` / `render_tab1`-`render_tab8` / `render_detail` 搬進 `scripts/dashboard/tabs.py`。
2. `main()` 按 D2.2 樣式呼叫。
3. `scripts/sector_flow_dashboard.py` 只保留：imports、`SidebarParams` / `AppData` 定義、`render_sidebar()`、`load_app_data()`、`main()`。
4. 期望行數：`sector_flow_dashboard.py < 500` 行；`dashboard/tabs.py < 1200` 行；`dashboard/panels.py < 400` 行；`dashboard/helpers.py < 400` 行。
5. 驗收：截圖逐 tab 比對 + 所有 session_state key 行為一致。

##### D2.4 資料流與 session_state 規則

- `st.session_state` 只能在 `render_sidebar` / `load_app_data` 內讀寫。tab render 函式**不得**讀寫 session_state（若發現必要，先標 TODO 並停止 D2 改動）。
- `@st.cache_data` 裝飾的函式（`cached_load_universe` / `_cached_latest_date` / `load_data`）**保留於主檔**或 `dashboard/cache.py`；不要同時在多處 import 同名 cached 函式（會註冊兩份 cache key）。
- Plotly figure 物件不得跨 tab 共用；每個 `render_tab*` 內自行建 `go.Figure()`。

##### D2.5 驗收

| 檢查 | 方法 |
|------|------|
| 行數目標 | `wc -l scripts/sector_flow_dashboard.py` < 500；三個 dashboard/* 檔各自 < 1200 |
| import 週期 | `python3 -c "import importlib; importlib.import_module('scripts.sector_flow_dashboard')"` 不丟 `ImportError` |
| 視覺回歸 | Tab1-8 + alerts + scrubber + 個股明細 expander 全部與 pre-D2 baseline 截圖 diff = 0 |
| 互動回歸 | 快速區間 / preset / 更新資料按鈕 / margin_auto rerun / broker_auto fetch 全部與 pre-D2 行為一致 |
| cache 一致 | `streamlit run` 啟動後 `st.cache_data.get_stats()`（若啟用 debug）key 數與 pre-D2 相同 |
| session_state 清查 | `grep -nE "st\\.session_state" scripts/dashboard/*.py` 回傳 0 筆 |

##### D2.6 提交規範

- **branch**：`refactor/phase-d2`（包 D2-A / D2-B / D2-C 三個 commit）
- **PR 拆法**：若 reviewer 要求，D2-A 可獨立 PR（因 panels/helpers 搬檔較單純）；D2-B + D2-C 合併為第二 PR。
- **commit message 樣板（D2-C 為例）**：

  ```text
  refactor(sector_flow_dashboard): split tab rendering into dashboard/tabs.py (D2-C)

  - move render_alerts / render_scrubber / render_tab1..tab8 / render_detail to dashboard/tabs.py
  - main() orchestrates sidebar -> load_app_data -> tab rendering via TabContext
  - sector_flow_dashboard.py shrinks to orchestration-only (< 500 lines)
  ```

- **禁止**：
  - 在 D2 期間修改 trace / layout / panel_data schema（違反 §5 非目標）
  - 混用舊模組層變數與 `ctx.data.*`（必須一刀切乾淨）
  - 為了搬檔建新 feature flag 或 backwards-compat wrapper（本檔為個人研究工具，無對外 API）

##### D2.7 回滾策略

- D2-A 回滾：revert 搬檔 commit，imports 恢復原狀；helper 函式無行為變更。
- D2-B 回滾：revert `main()` 與 `load_app_data`，回到 D1 相容層。
- D2-C 回滾：將 tabs.py 內容 inline 回主檔（或 revert commit），D2-B 不受影響。

**風險：高**（大範圍，需分多個 sub-PR；最後才做）

---

## 3. 執行順序建議

```text
Phase A  (A1 → A10)  ── 1-2 個 commit，低風險速戰
  ↓ 視覺比對 baseline
Phase B  (B1 → B4)   ── 每 STEP 獨立 commit
  ↓ 視覺比對 baseline
Phase C  (C1)        ── 單 commit
  ↓ 功能回歸測試
Phase D  (D1 → D2)   ── 可選，最後做
```

---

## 4. 驗收準則

每 STEP 完成後：

| 檢查項 | 方法 |
|-------|-----|
| Tab1 100% 堆疊面積 | 截圖比對；`fig.to_json()` diff |
| Tab2 cumsum 河流圖 | 截圖比對；`fig.to_json()` diff |
| Tab3 正負 stacked bar + 累積淨額線 | 截圖比對 |
| Tab4/5/6/7/8 | 數字與配色比對 |
| Panel hover | DevTools inspect HTML diff |
| Missing markers | 春節 / 國定假日範圍視覺一致 |
| Scrubber | hover text 格式與位置一致 |
| Sidebar | 所有 widget state 一致 |
| DB query count (C1) | `cProfile` 確認下降 |

---

## 5. 非目標（明確不做）

- ❌ 新增 tab / 新增 filter / 新增資料源
- ❌ 改動 Plotly trace 的視覺屬性（顏色、filltype、hovertemplate）
- ❌ 改動 `period_data` / `panel_data` JSON schema
- ❌ 改動 DB schema / CSV 路徑
- ❌ 變更 `@st.cache_data` 的 key 結構

---

## 6. 實作紀錄

### Phase A — `6ee7ec8` refactor(sector_flow_dashboard): Phase A low-risk dedup

| STEP | 實際改動 |
|------|---------|
| A1 | 新增 `GRID_COLOR` / `NEU_ZERO_COLOR` / `MISSING_FILL` / `MISSING_BORDER` / `MISSING_TEXT` / `LEGEND_BG` / `HIDDEN_Y2`；Python 端 gridcolor / zerolinecolor / missing 填色 / legend bg / Tab1-2 `yaxis2` 全部改引用常數。JS / CSS 字串的 `#94a3b8` / `#cbd5e1` / `rgba(...)` 字面量留至 B3 處理。 |
| A2 | `_missing_set: set[str]` 於 `cat_list` 篩選後建立一次；Tab1/2/3 的 `_missing_set` / `_missing_set2` / `_missing_set3` 全部刪除改引用此一 set。 |
| A3 | 移除「資料新鮮度」expander 內重複的 `_today = date.today()` 遮蔽。 |
| A4 | `cat_rgba_015: dict[str, str]` 於 `cat_colors` 之後一次性預算，Tab2 河流圖 `rgba_fill` 直接查表。 |
| A5 | `_universe_cats, all_tickers, _ticker_to_cat, _universe_meta = cached_load_universe(tier)` 於模組頂部資料載入段單次解包；`_render_alerts` / Tab5 HHI / Tab6 / Tab7 / Tab8 / 個股明細全部改引用此四個變數，移除 `_universe_cats_a` / `_universe_cats_q` / `_universe_cats_h` / `_detail_cats` / `_detail_ticker_to_cat` / `_u_t2c`。Sidebar 內既有呼叫保留（`@st.cache_data` 直命中）。 |
| A6 | `active_tickers: set[str]` 於 `_missing_set` 後一次建立；`_active_tkrs_a` / `_active_tkrs_q` / `_active_tkrs` / `_bt_tkrs`（Tab7）全部替換。Tab7 的 `_bt_tkrs = set(); for cat in cat_list: for tk in _universe_cats.get(cat, {}).keys(): _bt_tkrs.add(tk)` 這段整塊移除。 |
| A7 | `_trading_dates: list[date] = trading_dates_in_range(start_date, end_date)`，取代 `_render_alerts` / Tab6 / Tab8 / 個股明細 expander 共 4 處的 `datetime.strptime(start_str, "%Y-%m-%d").date()` + `trading_dates_in_range(...)` 組合。 |
| A8 | `_bar_trace` / `_hhi_bg` / `_is_foreign` + 常數 `_FOREIGN_BROKER_KEYWORDS` 全部提升至模組頂層；Tab4 / Tab5 / Tab7 的 local 定義刪除。 |
| A9 | `_color_num(v)` 改為 `_color_num(v: float, unit: str, suffix: str)`，內部用單一 `fmt = "+,.2f" if unit == "value_oku" else "+,.0f"` 產生正負值文字。Tab5 兩處呼叫改為 `_color_num(diff, unit, _unit_suffix)`。 |
| A10 | `_unit_fmt` 修正為 `",.2f"`（原為 `".2f"` 缺千分位）以反映 hover 面板 `formatVal` 的實際格式；scrubber `text=` 改用 f-string `f"{v:+{_unit_fmt}}"`，移除 inline 條件式。 |

### Phase C — `1a0a48d` perf(sector_flow_dashboard): batch load_from_db in _render_alerts

| STEP | 實際改動 |
|------|---------|
| C1 | `_render_alerts` 內的融資/法人背離迴圈：`load_from_db([dt])` 逐日呼叫改為 `load_from_db(sorted(_by_date_a.keys()))` 單次批次；`_by_date_a` 由 `dict[str, list[int, int]]`（第二格從未使用）收斂為 `dict[str, float]`；新增 `_inst_net_by_date` 預聚合 dict，迴圈 O(N) DB 查詢降為 1 次。行為等價已用多 ticker / inactive ticker / margin_prev=None / 空 margin 等 fixture 驗證（old==new）。`active_tickers` 過濾雙側保留；空 margin 路徑 guard `if _by_date_a else {}` 避免 `load_from_db([])`。 |

等價性驗證腳本（已跑過）：

```python
# 多 ticker + inactive filter + None 值 + 空 margin + 全 inactive
# old()=2, new()=2；edge cases 全通
```

### Phase B — `5a1a48a` refactor(sector_flow_dashboard): Phase B structural dedup

| STEP | 實際改動 |
|------|---------|
| B1 | 新增 `_PANEL_EXTRA_KEY = {"tab1": "pos", "tab3": "pos", "tab2": "cumsum"}`；`build_panel_data` 非 tab4 分支改為統一迴圈、用 `_PANEL_EXTRA_KEY[tab_mode]` 決定第二個欄位。dict key 順序（`raw` → extra → `foreign` → `invest` → `dealer`）保留；以 Python 單元測試確認 tab1/2/3/4 的 `json.dumps` 輸出 byte-identical。 |
| B2 | 在 `render_chart_with_panel` 內部新增共用 JS `_cat_card_js`，提供 `renderCatCard(cat, color, mainLine, subLine)` 與 `institutionSub(d)`。Tab1 / Tab2 / Tab3 的 `buildPanel` 只保留差異化 main line，其餘卡片外框 HTML 與「外資／投信／自營」子行統一由 helper 組裝。Tab4 仍為獨立 3-row flex 版型，不共用。 |
| B3 | 抽離模組常數 `_PANEL_CSS` / `_PANEL_JS_HELPERS`（`orderedCatsForLabel` + `tab3TotalMeta`）/ `_PANEL_VLINE_JS`（`setVLine` + hover / unhover handler）；原本 `render_chart_with_panel` 內超大 f-string 改為 `_script_head` / `_script_trace_fix` / `_script_tab_mode` / `_script_plot` / `_script_panel_wire` 幾段 concat。Script 執行順序（head → helpers → trace fix → tab_mode → plot → panel_js → build_panel_js → wire + init → vline）完整保留；JS 變數作用域維持原樣（`POS_COLOR` 等在 `panel_js` 中宣告，於 helper 呼叫時已存在）。 |
| B4 | `LAYOUT_BASE` 新增標頭註解說明 Tab1/2 直接套用預設 `legend`，Tab3/4/6/8 客製 override 的原因；不改 layout 資料結構。 |

### 延伸建議

- Phase C 等價性已用 fixture 單元驗證；視覺 / DB query 次數仍待人工 `streamlit run` 回歸（勾選融資融券，確認 `📊 融資-法人 背離天數` metric 與 `5a1a48a` baseline 相同）。
- 進 Phase D 前建議先 checkout `1a0a48d` 產生 baseline 截圖（Tab1–Tab8 + scrubber + sidebar + alerts 四格），作為 D1 / D2 視覺比對標準。
- Phase D 須獨立開分支（`refactor/phase-d1`、`refactor/phase-d2`），因為 `st.session_state` 存取與 tab rendering 順序敏感。

---

版本：1.3 | 2026-04-18
