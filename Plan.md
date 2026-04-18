# 主力資金類股輪動儀表板 — 功能強化計畫

> 對象：`scripts/sector_flow_dashboard.py` + `scripts/sector_flow.py`
> 目標：在不重構現有架構前提下，擴充資料維度、提升展示資訊密度
> 版本：v1.2 | 2026-04-18
>
> **執行狀態總覽（2026-04-18）**：
>
> **已完成（11 項）：**
> - ✅ A1 T86 欄位 bug fix + 金額欄位 + 單位切換
> - ✅ A2 TPEx 上櫃整合（補 9 檔 OTC 光通訊標的）
> - ✅ A3 融資融券（schema + TWSE/TPEx 雙源 + Tab 6 散戶情緒）
> - ✅ B1+B2 券商分點 DB + Tab 7 券商動向（HiStock branch.aspx + Treemap + 外資 vs 本土對比）
> - ✅ B4 HHI 籌碼集中度（Tab 5 尾端熱表）
> - ✅ C1 期貨未平倉（TAIFEX CSV + Tab 8 期現連動）
> - ✅ C3 外資持股上限（TWSE MI_QFIIS + TPEx OpenAPI + 個股明細欄）
> - ✅ C4 TDCC 大戶持股（OpenData 1-5 + 個股明細「大戶≥1000張%」「散戶<5萬股%」欄）
> - ✅ D2 警示摘要區（title 下方 4 metric）
> - ✅ D3 Preset 持久化（`research/dashboard_presets.json` + sidebar selectbox）
> - ✅ D4 時間軸 scrubber（title 下 expander + 橫向長條 snapshot）
>
> **附屬維護：**
> - ✅ universe ticker 4256 誤值移除（正名 6770 力積電歸入 HBM/DRAM）
> - ✅ `docs/DB_FETCH_GUIDE.md` AI Agent DB 操作 SOP 建立
>
> **尚未執行（6 項）：**
> - ⏳ A4 借券賣出（SBL）整合（TWSE TWT93U + 空方壓力疊加）
> - ⏳ B3 個股分點下鑽（明細表展開顯示該股近 N 日前 15 大買/賣超券商 + 連續天數）
> - ⏳ C2 選擇權 P/C Ratio（TAIFEX optContractsDate）
> - ⏳ C5 當沖比率（TWSE TWTB4U，Tab 3 副軸疊加）
> - ⏳ C6 產業別 BFI82U 官方產業驗證
> - ⏳ D1 CSV 下載按鈕 / 法人過濾器（部分）
>
> **資料抓取狀態（DB：`data/revenue/revenue.db`，截至 2026-04-18）：**
>
> | 表 | 筆數 | 涵蓋範圍 | 狀態 |
> |------|------|---------|------|
> | `institutional_flow` | 4098 | 31 檔 × 148 天（2025-09-01 ~ 2026-04-16） | ✅ 完整回填（含 TPEx OTC 9 檔） |
> | `daily_price` | 4205 | 31 檔 × 148 天 | ✅ 完整（TWSE MI_INDEX + TPEx） |
> | `trading_calendar` | 148 | 2025-09 ~ 2026-04 | ✅ 由 TWSE FMTQIK 填充 |
> | `margin_flow` | 609 | 29 檔 × 21 天（2026-03-17 ~ 2026-04-16） | ⚠️ 僅回填 1 個月測試，需擴至全期 |
> | `foreign_ownership` | 5 | 5 檔 × 1 天（測試） | ⚠️ 僅測試日；dashboard 勾選後自動抓最新一天 |
> | `shareholder_distribution` | 85 | 5 檔 × 17 tier × 1 週 | ⚠️ 僅測試 5 檔；TDCC 為全市場週資料，可一次補全 |
> | `futures_oi` | 0 | — | ❌ schema 就緒，未回填；dashboard 勾選後自動抓 |
> | `broker_flow` | 0 | — | ❌ schema + fetcher 就緒，當日資料需每日盤後 cron 抓 |
>
> **待抓取（授權後執行）：**
> 1. `margin_flow` 回填全期（2025-09-01 ~ 2026-04-16，~148 天 × 2 API ≈ 2 分鐘）
> 2. `foreign_ownership` 回填全期（TWSE MI_QFIIS 按日抓，~148 天 ≈ 1 分鐘）
> 3. `shareholder_distribution` 全市場補全（TDCC 1-5 單次下載即覆蓋所有標的 × 歷史週數）
> 4. `futures_oi` 回填（TXF + EXF × 148 天 × 0.5s ≈ 2.5 分鐘）
> 5. `broker_flow` 需每日盤後 15:30 cron（HiStock 無歷史回溯）
>
> **CLI 指令（新增 flags）：**
> ```bash
> python3 scripts/sector_flow.py \
>   --start 2025-09-01 --end 2026-04-18 --tier ai_supply_chain \
>   --include-margin       # 融資融券（TWSE MI_MARGN + TPEx margin_bal）
>   --include-qfii         # 外資持股（TWSE MI_QFIIS + TPEx OpenAPI）
>   --include-futures      # 期貨未平倉（TAIFEX CSV，TXF + EXF）
>   --include-tdcc         # TDCC 集保分級（週資料，自動判斷 7 天 TTL）
>   --fetch-broker-today   # 當日券商分點（HiStock，每股 sleep 2.5s）
>   --no-save              # 僅補 DB 不寫報告
> ```
>
> **Dashboard UI 實作細節（與原 Plan v1.0 差異）：**
> - 💰 **顯示單位**為三選（金額（億元）預設 / 股數 / 金額（千元）），非原計畫兩選
> - Tab 6/7/8 採 **sidebar 勾選動態啟用**（避免無資料時 Tab 空白），對應 `_margin_auto / _broker_auto / _fut_auto`
> - 警示摘要區 4 metric 自動運算：外資 TOP3 / 連續買超類股 / 融資-法人背離天數 / 外資接近上限標的
> - ⏮️ 時間軸回放採 Title 下 **expander + slider** 形式，獨立於 Tab 結構
> - Preset 檔：`research/dashboard_presets.json`（6 組：AI 主軸 / DRAM 專注 / CPO 專注 / ABF 專注 / 散熱電源 / 伺服器鏈）
>
> **已知備份：** `data/revenue/revenue.db.bak.20260417`（332 KB，A1 bug fix 前狀態，可保留或清理）
>
> **煙測驗收結果（2026-04-18）：**
> - ✅ 所有 8 個 Tab + 警示區 + scrubber + 個股明細在 `streamlit run` HTTP 200 無 error
> - ✅ 單位切換三模式資料計算正確（load_data 通過）
> - ✅ T86 欄位 sanity：外資 437 萬 >> 投信 81 萬 > 自營 52 萬（日均絕對值）
> - ✅ TPEx OTC 9 檔補齊（3081/3105/3163/3324/3363/4979/6182/6223/6488）
> - ✅ 2408 南亞科金額驗算：4,991,977 股 × 213.5 = +10.66 億
> - ✅ TDCC 抽測：2330 大戶 85.69% / 2344 華邦電 61.40% / 4979 華星光 38.80%
> - ✅ TAIFEX TXF 2026-04-16：外資淨空 39,683 口 / 投信淨多 42,625 口

---

## 第一部分：功能改善說明（給使用者審核）

### 現況盤點

| 項目 | 現況 |
|------|------|
| 資料源 | 僅 TWSE T86（三大法人股數）+ FMTQIK（開盤日曆） |
| 資料單位 | 股數（無金額、無億元換算，僅在 Tab 4 用 ×30/1e8 粗估） |
| 市場範圍 | 僅上市（sii），缺上櫃（otc） |
| 維度 | 三大法人合計/外資/投信/自營，類股聚合 |
| Tab 數 | 5 個（強度佔比、累積、量體、法人對比、摘要） |
| 互動 | hover 顯示各類股 panel；個股明細展開 |
| 缺口 | 無券商分點、無金額、無融資融券、無借券、無期貨、無外資上限、無當沖、無 TDCC 大戶 |

### 強化功能清單（分 3 階段，由輕至重）

---

#### 🅰️ **階段 A：資料維度擴充**（低風險，僅加欄位）

**A1. T86 欄位升級：加入「買賣超金額（千元）」**
- 現況：T86 API 其實同時提供股數（col 4/7/10/11）與金額（col 5/8/10/12，千元）
- 改動：`institutional_flow` 新增 `foreign_value / invest_value / dealer_value / total_value`（REAL，單位：千元）
- 價值：儀表板可切換「股數 / 金額（億元）」顯示，貼近實務「今天外資買超多少億」語感
- UI：sidebar 新增 radio「顯示單位」→ 股數 / 金額（千元） / 金額（億元）

**A2. 上櫃（TPEx）整合**
- 來源：`https://www.tpex.org.tw/openapi/v1/tpex_institutionalinvestors_dealingquiries`
- 改動：`fetch_t86` 擴充為 `fetch_institutional_flow`，同時抓 TWSE + TPEx
- 價值：光通訊/CPO 不少標的在上櫃（如 3363 上詮、4977 眾達-KY、6442 光聖），目前資料庫完全缺失會低估該類股流入
- 影響範圍：`stock_universe.json` 中凡 4 位數但實際上櫃的標的都能補回

**A3. 融資融券整合**
- 來源：TWSE MarginBalance `MI_MARGN` + TPEx `tpex_margin_balance_queries`
- 新 DB 表：`margin_flow(ticker, trade_date, margin_buy, margin_sell, margin_balance, short_sell, short_cover, short_balance)`
- 新 Tab 6：「散戶情緒」（融資餘額變化 vs 三大法人買賣超對比 → 背離訊號）
- 價值：融資減少 + 外資買超 = 散戶殺出、籌碼轉穩；融資暴增 + 外資賣 = 散戶追高危險

**A4. 借券賣出（SBL）整合**
- 來源：TWSE `TWT93U` 借券賣出統計
- 新欄位：`short_sale_balance`（借券賣出餘額）
- 價值：真實空方壓力指標；外資借券賣出是做空訊號
- UI：Tab 6 第二子圖「空方壓力」= 融券 + 借券賣出

---

#### 🅱️ **階段 B：券商分點進出（重點亮點）**

**B1. 券商分點每日聚合 DB**
- 主來源：TWSE BSR `https://bsr.twse.com.tw/bshtm/bsMenu.aspx`（當日，需 CAPTCHA）
- 備援：HiStock `https://histock.tw/stock/chip.aspx?no={ticker}&dt={date}`（歷史可查）
- 聚合來源：神秘金字塔 `norway.twsthr.info`（連續買超天數、多日合計）
- 新 DB 表：`broker_flow(ticker, trade_date, broker_id, broker_name, buy_shares, sell_shares, net_shares)`
- 寫入策略：**不硬抓全市場**，只在使用者點擊「查看該股分點」時按需抓
- 快取：pickle 或 SQLite；TTL = 當日（隔日重抓以更新）

**B2. 類股級別「前 15 大買超券商」排行**
- 計算：對某類股所有成員股，聚合每家券商跨股買賣超
- 新 Tab 7：「券商動向」
  - 左圖：類股前 15 大買超券商（橫向長條，依淨買超股數/金額排序）
  - 右圖：該券商所買的類股成員股分佈（Treemap）
- 價值：「哪家券商在搬 AI 類股」一目瞭然；外資分點（摩根士丹利、美林、JPM）vs 本土（凱基、元大、富邦）分流明顯

**B3. 個股分點下鑽**
- 個股明細表新增「查看分點」按鈕
- 展開顯示：該股最近 N 日前 15 大買超/賣超券商
- 附「連續買超天數」欄（來自神秘金字塔聚合）
- 價值：完整主力追蹤鏈（類股 → 成員股 → 主力券商）

**B4. 籌碼集中度指標（HHI）**
- 計算：Herfindahl-Hirschman Index = Σ(券商買超佔比)²
- HHI > 2500 = 高度集中（單一主力介入）
- HHI < 1500 = 分散買盤（散戶盤）
- 新增於 Tab 5 輪動摘要第三子區塊「籌碼集中度熱圖」

---

#### 🅲 **階段 C：進階指標與外部情境**

**C1. 期貨未平倉（TAIFEX）**
- 來源：`https://www.taifex.com.tw/cht/3/futContractsDate`（台指期/電子期/金融期）
- 新 DB 表：`futures_oi(trade_date, contract, role, long_contracts, short_contracts, net_contracts)`
- 新 Tab 8：「期現連動」
  - 三大法人台指期淨多空口數 vs 現貨買賣超
  - 電子期 vs AI 類股資金流向（驗證類股輪動是否有期貨對沖）

**C2. 選擇權 P/C Ratio**
- 來源：`https://www.taifex.com.tw/cht/3/optContractsDate`
- 面板顯示 Put/Call Ratio 折線（恐慌指標）
- 疊加於 Tab 8

**C3. 外資持股上限警示**
- 來源：TWSE `MI_QFII_sort`（外資持股比例即時）
- 個股明細新增欄「外資持股 / 上限 / 剩餘可買」
- UI：接近上限（剩餘 <5%）標紅；TSMC 類常年接近上限
- 價值：解釋「為什麼外資不再買 XXX」— 不是不想，是不能

**C4. TDCC 集保大戶持股**
- 來源：`https://www.tdcc.com.tw/portal/zh/smWeb/qryStock`（週資料）
- 新 DB 表：`shareholder_distribution(ticker, week_date, tier, holders, shares, pct)`
- 新 Tab 5 子區塊：「大戶結構變化」
  - 400 張以上大戶持股比例趨勢
  - 散戶（<10 張）比例趨勢
  - 大戶 ↑ + 外資買 = 強多；大戶 ↓ + 散戶 ↑ = 出貨中

**C5. 當沖比率（TWSE TWTB4U）**
- 新欄位：`day_trade_ratio`（當沖佔當日成交比率 %）
- UI：Tab 3 量體圖疊加「當沖比率」線（副軸）
- 警示：當沖 >40% = 籌碼不穩（熱門股末期）

**C6. 產業別法人買賣超（BFI82U，作為驗證）**
- 來源：TWSE 按官方產業分類的法人買賣超
- 用途：驗證自訂類股分類是否偏離市場共識（例如 TWSE「半導體業」vs 我們的「DRAM + CPO + ABF + IC 設計」）
- UI：Tab 5 新增「TWSE 官方產業流對照」子表

---

#### 🅳 **階段 D：展示體驗強化**

**D1. Streamlit Plotly 互動強化**
- Tab 1-4 加入「數值切換 toggle」：股數 ⇄ 金額（億元）
- Tab 3 加入「過濾器」：只看外資 / 投信 / 自營 / 合計
- 全部 Tab 加「下載 CSV」按鈕

**D2. 警示摘要區（新增於 title 下方）**
- 自動偵測並顯示：
  - 今日外資買超前 5 類股
  - 連續 3 日以上買超的類股
  - 融資+借券異常增加的類股
  - 外資持股接近上限（<5%）的標的

**D3. 自訂類股分組持久化**
- sidebar 多選過濾當前已有，但重整會消失
- 改用 `st.session_state` + `research/dashboard_presets.json` 儲存預設組合
- 預設：「AI 主軸」「DRAM 專注」「CPO 專注」「ABF 專注」

**D4. 時間軸 scrubber**
- sidebar 加入「歷史回放」滑桿，拖動觀察某特定日期的類股資金分佈
- 配合 Tab 1 100% 堆疊面積圖做時間點快照

---

### 建議優先順序（基於工作量 / 價值比）

| 優先度 | 項目 | 工作量 | 價值 | 備註 |
|--------|------|--------|------|------|
| 🔴 P0 | A1（T86 金額欄位） | 小 | 高 | 一次改 schema + fetch，UI 大升級 |
| 🔴 P0 | A2（上櫃整合） | 中 | 高 | 補缺失的半個 CPO 資料 |
| 🟠 P1 | B1+B2（分點 + 類股券商排行） | 大 | 極高 | 儀表板最大亮點，主力追蹤核心 |
| 🟠 P1 | A3（融資融券） | 中 | 高 | 散戶情緒 vs 法人背離 |
| 🟡 P2 | C3（外資上限警示） | 小 | 中 | 快速加分 |
| 🟡 P2 | C1（期貨未平倉） | 中 | 中 | 需熟悉 TAIFEX 格式 |
| 🟡 P2 | D2（警示摘要區） | 小 | 中 | 依賴 A/B 先完成 |
| 🟢 P3 | A4（借券） | 中 | 中 | 補 A3 |
| 🟢 P3 | B3+B4（個股分點 + HHI） | 中 | 中 | B1 完成後附加 |
| 🟢 P3 | C4（TDCC 大戶） | 中 | 中 | 週更非日更 |
| 🟢 P3 | C5（當沖比率） | 小 | 低 | 錦上添花 |
| 🟢 P3 | C6（產業別驗證） | 小 | 低 | 診斷用 |
| 🟢 P3 | D1/D3/D4（UI 體驗） | 中 | 中 | 並行進行 |
| ⚪ 觀察 | C2（P/C Ratio） | 小 | 低 | TAIFEX 選擇權 |

---

## 第二部分：Claude Agent 執行步驟（技術規格）

> 以下為給 Claude Code 的**具體實作指引**，每階段獨立可執行。
> 原則：**不重構現有架構**，只新增函式、新增 DB 表、新增 Tab。

---

### 階段 A：資料維度擴充

#### Task A1：T86 金額欄位

**檔案修改：** `scripts/sector_flow.py`

1. `init_db()` 中 `institutional_flow` 表 ALTER：
   ```sql
   ALTER TABLE institutional_flow ADD COLUMN foreign_value REAL;
   ALTER TABLE institutional_flow ADD COLUMN invest_value REAL;
   ALTER TABLE institutional_flow ADD COLUMN dealer_value REAL;
   ALTER TABLE institutional_flow ADD COLUMN total_value REAL;
   ```
   包在 try/except 內（已存在會報錯）。

2. `fetch_t86()`：確認 T86 回傳欄位順序（截至 2026 年）：
   - 實測檢查 `data["fields"]`，可能是 `[證券代號, 證券名稱, 外資買進股數, 外資賣出股數, 外資買賣超股數, 投信買進股數, 投信賣出股數, 投信買賣超股數, 自營商買賣超股數, 自營商買進股數, 自營商賣出股數, 自營商買賣超股數, 三大法人買賣超股數]`
   - **實作前先抓一天 `print(data["fields"])`** 驗證欄位。金額不在 T86；金額版端點是 TWSE `/rwd/zh/fund/T86?response=json` 新版 API，欄位較多。
   - **若 T86 無金額，改用 `MI_QFIIS_cat`（上市法人買賣超金額日報）或計算：金額 ≈ 股數 × 當日收盤價**。後者需整合 `STOCK_DAY_ALL` 或 `STOCK_DAY` 收盤價端點。
   - **決策點**：若 T86 新版有金額 → 直接取；若無 → 在 DB 另建 `daily_price(ticker, trade_date, close)` 表，`total_value = total_net × close / 1000`（千元）

3. `save_to_db()` / `load_from_db()`：新增 value 欄位讀寫。

4. `aggregate_by_category()`：result 字典加 `foreign_value / invest_value / dealer_value / total_value` 累加。

**檔案修改：** `scripts/sector_flow_dashboard.py`

5. sidebar 新增：
   ```python
   st.subheader("💰 顯示單位")
   unit_label = st.radio("單位", options=["股數", "金額（億元）"], index=1)
   ```

6. `load_data()` 回傳的 `period_data[cat]["raw"/"pos"/"cumsum"]` 根據 unit 切換。定義 helper：
   ```python
   def to_display_unit(val_shares, val_thousand_twd, unit):
       if unit == "股數": return val_shares
       return val_thousand_twd / 1e5  # 千元 → 億元
   ```

7. 全部 Tab 圖表的 `yaxis.title` / `hover panel fmtNum` 依 unit 切換後綴（"股" → "億元"）。

**測試：**
```bash
cd /Users/wayne/Desktop/Invest/taiwan-stock-analysis
python3 -c "from scripts.sector_flow import fetch_t86; import json; print(json.dumps(fetch_t86('20260416', {'2330':'台積電'}), indent=2, ensure_ascii=False))"
```
確認欄位數量與金額存在。

---

#### Task A2：上櫃（TPEx）整合

**檔案修改：** `scripts/sector_flow.py`

1. 新增 `fetch_tpex_institutional(trade_date_str, all_tickers)`：
   - URL: `https://www.tpex.org.tw/openapi/v1/tpex_institutionalinvestors_dealingquiries`
   - 參數：`date=民國年/月/日`（如 `115/04/16`）—— 需格式轉換
   - 回傳格式同 `fetch_t86`

2. 新增輔助 `detect_market(ticker)`：
   - 先查 `research/stock_universe.json` 中是否有 `market` 欄位；若無，嘗試 TWSE `STOCK_DAY` 若 404 則判定為 OTC
   - 建議**預先批次建表**：執行一次 `scripts/classify_market.py` 將結果寫入 `data/ticker_market.json`

3. 修改 `ensure_data()`：依 market 分流呼叫 `fetch_t86` 或 `fetch_tpex_institutional`，合併後寫入同一張 `institutional_flow` 表，新增欄位 `market TEXT`。

4. 更新 `research/stock_universe.json`：每個 ticker 補 `"market": "TWSE"|"TPEx"` 欄位。建議先：
   ```bash
   python3 scripts/classify_market.py  # 自動判斷並寫回
   ```

**檔案新增：** `scripts/classify_market.py`
- 讀 `stock_universe.json`，對每個 ticker 呼叫 TWSE `STOCK_DAY` 當月資料
- 回 200 且 stat=OK → TWSE；否則試 TPEx，成功 → TPEx
- 寫回 JSON

**測試：**
```bash
python3 scripts/classify_market.py
python3 scripts/sector_flow.py --start 2026-04-01 --end 2026-04-16 --tier ai_supply_chain
# 確認 log 中有「補抓 TPEx ...」訊息
```

---

#### Task A3：融資融券整合

**DB schema：** 新增於 `scripts/sector_flow.py` `init_db()`:
```sql
CREATE TABLE IF NOT EXISTS margin_flow (
    ticker          TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    margin_buy      REAL,
    margin_sell     REAL,
    margin_balance  REAL,
    short_sell      REAL,
    short_cover     REAL,
    short_balance   REAL,
    updated_at      TEXT,
    PRIMARY KEY (ticker, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_margin_date ON margin_flow(trade_date);
```

**檔案新增：** `scripts/margin_fetch.py`
- `fetch_margin_twse(date_str)`：TWSE `MI_MARGN`
- `fetch_margin_tpex(date_str)`：TPEx 對應端點
- `ensure_margin_data(dates, all_tickers)`：快取邏輯同 `ensure_data`

**Dashboard 修改：**
- `load_data()` 增加 margin 欄位載入
- 新增 Tab 6：「散戶情緒 vs 法人」
  - 上圖：融資餘額變化（柱）+ 外資買賣超（線，副軸）
  - 下圖：融資變化與外資買賣超的散佈圖，標註背離期
- 警示邏輯：`|融資變化| > 均值 + 2σ` 且方向與外資相反 → 標紅

**測試：**
```bash
python3 scripts/margin_fetch.py --date 2026-04-16
```

---

#### Task A4：借券賣出（SBL）

**DB：** 擴充 `margin_flow` 加 `sbl_short_sale` / `sbl_balance` 欄位（ALTER TABLE）。

**檔案修改：** `scripts/margin_fetch.py`
- 新增 `fetch_sbl_twse(date_str)`：`https://www.twse.com.tw/rwd/zh/SBL/TWT93U`

**Dashboard：** Tab 6 下半部加「空方壓力」= 融券餘額 + 借券賣出餘額，與股價對比。

---

### 階段 B：券商分點

#### Task B1：分點 DB + 按需抓取

**DB：** 新增於 `init_db()`:
```sql
CREATE TABLE IF NOT EXISTS broker_flow (
    ticker        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    broker_id     TEXT NOT NULL,
    broker_name   TEXT,
    buy_shares    REAL,
    sell_shares   REAL,
    net_shares    REAL,
    updated_at    TEXT,
    PRIMARY KEY (ticker, trade_date, broker_id)
);
CREATE INDEX IF NOT EXISTS idx_broker_date ON broker_flow(trade_date);
CREATE INDEX IF NOT EXISTS idx_broker_id ON broker_flow(broker_id, trade_date);
CREATE INDEX IF NOT EXISTS idx_broker_ticker_date ON broker_flow(ticker, trade_date);
```

**檔案新增：** `scripts/broker_fetch.py`

主源：HiStock（無 CAPTCHA）
- `fetch_broker_histock(ticker, date_str)`: GET `https://histock.tw/stock/chip.aspx?no={ticker}&dt={YYYY-MM-DD}`
- 解析 HTML：`<table id="tablesorterTop">` 類表格，欄位券商名/買張/賣張/差異
- User-Agent 偽裝 + Referer `https://histock.tw/`
- 回傳 `[{broker_id, broker_name, buy_shares, sell_shares, net_shares}, ...]`

備援：神秘金字塔
- `fetch_broker_twsthr(ticker)`: GET `https://norway.twsthr.info/StockHolders.aspx?stock={ticker}`
- 提供歷史「連續買超天數」聚合，單次回傳多日資料
- 解析 HTML 表格

限流：每次請求 sleep 3 秒，每類股批次最多 20 檔/分鐘。

**Dashboard 修改：**
- 新增 sidebar 按鈕「載入分點資料（當前類股）」
- 點擊後對當前 `cat_list` 成員股逐一呼叫 `fetch_broker_histock`，寫入 DB
- 進度條：`st.progress` 顯示 `N/總檔數`

---

#### Task B2：類股券商排行 Tab

**Dashboard 修改：** 新增 `tab7 = st.tabs([..., "🏦 券商動向"])`

Tab 7 內容：
1. 讀 `broker_flow` 表，篩選當前日期區間 + 當前類股成員股
2. 按 `broker_id` 聚合 `sum(net_shares)`
3. 左欄（60%）：Plotly 橫向長條圖，前 15 大買超券商
   - 顏色：外資券商紅（券商代碼 1440/1470/9800/9900 等）、本土藍
   - hover 顯示該券商在每個成員股的買賣超
4. 右欄（40%）：選定某券商後的 Treemap，顯示其對成員股的買超分佈

外資券商代碼 whitelist（硬編碼於 dashboard）：
```python
FOREIGN_BROKERS = {
    "1440": "美商美林",
    "1470": "台灣摩根士丹利",
    "9800": "元富",  # 實為本土，僅示意，請實查
    # ... 需實查 TWSE 券商代碼表
}
```
**執行前先 fetch TWSE 券商清單端點**：`https://www.twse.com.tw/brokerService/brokerList`

---

#### Task B3：個股分點下鑽

**Dashboard 修改：** 個股明細表（`with st.expander("個股明細...")`）內：
- 每列加入「展開」checkbox（用 `st.dataframe` 的 selection 或 `st.data_editor`）
- 選中後下方顯示該股最近 20 交易日前 15 大券商排行
- 附「連續買超天數」欄（從神秘金字塔快照或自行從 broker_flow 計算）

計算連續天數 SQL：
```sql
-- 以 broker_id + ticker 為 group，倒序取每日 net_shares，計算連續正值天數
SELECT broker_id, broker_name, COUNT(*) AS streak
FROM (
    SELECT broker_id, broker_name, net_shares,
           ROW_NUMBER() OVER (PARTITION BY broker_id ORDER BY trade_date DESC) AS rn
    FROM broker_flow WHERE ticker = ?
    ORDER BY trade_date DESC
)
WHERE net_shares > 0
GROUP BY broker_id;
```

---

#### Task B4：HHI 籌碼集中度

**計算函式：** 新增於 `scripts/sector_flow.py`:
```python
def calc_hhi(broker_nets: list[float]) -> float:
    total_abs = sum(abs(v) for v in broker_nets) or 1
    return sum((abs(v) / total_abs * 100) ** 2 for v in broker_nets)
```

**Dashboard：** Tab 5 輪動摘要新增第四區塊「籌碼集中度熱圖」
- x 軸：類股，y 軸：日期，值：HHI
- 顏色：HHI > 2500 紅、1500-2500 黃、< 1500 綠

---

### 階段 C：進階指標

#### Task C1：期貨未平倉

**DB：**
```sql
CREATE TABLE IF NOT EXISTS futures_oi (
    trade_date       TEXT NOT NULL,
    contract         TEXT NOT NULL,  -- TX, MTX, TE, TF
    role             TEXT NOT NULL,  -- foreign, invest, dealer
    long_contracts   REAL,
    short_contracts  REAL,
    net_contracts    REAL,
    updated_at       TEXT,
    PRIMARY KEY (trade_date, contract, role)
);
```

**檔案新增：** `scripts/futures_fetch.py`
- `fetch_taifex_oi(date_str)`: POST `https://www.taifex.com.tw/cht/3/futContractsDate` with form `queryDate=YYYY/MM/DD&commodity_idTWF=TXF`
- HTML scrape，解析表格

**Dashboard：** 新 Tab 8「期現連動」
- 上：外資台指期淨多空（線圖）+ 現貨三大法人合計（副軸）
- 下：電子期淨多空 vs AI 類股（當前篩選）資金流向

---

#### Task C3：外資持股上限

**一次性抓取：** 新增 `scripts/foreign_limit_fetch.py`
- URL: `https://www.twse.com.tw/rwd/zh/fund/MI_QFII_sort?response=json`
- 每日更新寫入：
```sql
CREATE TABLE IF NOT EXISTS foreign_ownership (
    ticker          TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    foreign_pct     REAL,
    foreign_limit   REAL,
    remaining_pct   REAL,
    PRIMARY KEY (ticker, trade_date)
);
```

**Dashboard：** 個股明細表新增 3 欄「外資持股 %」「上限 %」「剩餘 %」，剩餘 < 5 用紅字。

---

#### Task C4：TDCC 大戶持股

**檔案新增：** `scripts/tdcc_fetch.py`
- TDCC 頁面需 POST 與 CAPTCHA，建議改用第三方：
  - `https://norway.twsthr.info/StockHolders.aspx?stock={ticker}` 有整理好的每週大戶比例
- 解析 HTML

**DB：**
```sql
CREATE TABLE IF NOT EXISTS shareholder_distribution (
    ticker        TEXT NOT NULL,
    week_date     TEXT NOT NULL,
    tier          TEXT NOT NULL,  -- '400+', '100-400', '10-100', '<10'
    holders       INTEGER,
    shares        REAL,
    pct           REAL,
    PRIMARY KEY (ticker, week_date, tier)
);
```

**Dashboard：** Tab 5 新增子區塊「大戶結構變化」，折線圖：400+ % vs <10 % 時間序列。

---

### 階段 D：UI 體驗

#### Task D2：警示摘要區

**位置：** `st.title("主力資金類股輪動")` 之後

**實作：** `st.container()` 內放 4 個 `st.columns(4)` metric：
1. 今日外資買超前 3 類股
2. 連續買超 ≥3 天類股數
3. 融資異常類股數（>2σ）
4. 外資持股接近上限標的數

每個 metric 下附「展開詳情」expander。

---

#### Task D3：Preset 持久化

**檔案新增：** `research/dashboard_presets.json`
```json
{
  "AI 主軸": ["HBM/DRAM 記憶體", "CPO 光通訊核心", "CPO 光通訊周邊", "先進封裝 CoWoS", "ABF 載板"],
  "DRAM 專注": ["HBM/DRAM 記憶體"],
  "CPO 專注": ["CPO 光通訊核心", "CPO 光通訊周邊"],
  "ABF 專注": ["ABF 載板", "IC 載板 PCB"]
}
```

**Dashboard：** sidebar「類股篩選」上方新增 selectbox「快速選擇」，選中後覆寫 `_selected_cats`。

---

### 共用：執行順序與相依

```
A1 (金額) ─┐
A2 (TPEx) ─┼─> B1 (分點 DB) ─> B2 (券商排行) ─> B3 (個股下鑽) ─> B4 (HHI)
           │
A3 (融資) ─┼─> D2 (警示摘要)
A4 (借券) ─┘

C1 (期貨)  獨立
C3 (外資上限) 獨立
C4 (TDCC) 獨立

D1/D3/D4 (UI) 任何階段後皆可
```

---

### 風險與注意事項

1. **爬蟲限流**：HiStock / 神秘金字塔有 UA / Referer 檢查，sleep 至少 3 秒，大量請求需分批
2. **TWSE CAPTCHA**：BSR 需驗證碼，建議優先用 HiStock 或官方 OpenAPI（若上線）
3. **TPEx 日期格式**：民國年，需轉換
4. **DB schema migration**：新增欄位用 `ALTER TABLE`，包 try/except（已存在會錯）
5. **Streamlit 快取失效**：新欄位後記得 `st.cache_data.clear()`
6. **資料回補**：新增欄位後歷史資料全為 NULL，提供 backfill script

---

### 驗收標準

每階段完成後執行：
```bash
# 確認 DB schema
sqlite3 data/revenue/revenue.db ".schema"

# 確認資料筆數
sqlite3 data/revenue/revenue.db "SELECT COUNT(*) FROM institutional_flow; SELECT COUNT(*) FROM margin_flow; SELECT COUNT(*) FROM broker_flow;"

# 啟動儀表板
streamlit run scripts/sector_flow_dashboard.py

# 手動驗證每個新 Tab 顯示正常、hover 正常、切換單位正常
```

---

*計畫版本 v1.0 | 依使用者審核後再分階段 commit*
