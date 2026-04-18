# DB 抓取指引（AI Agent 專用）

> 目的：規範 Claude Agent 對 `data/revenue/revenue.db` 的抓取/清理行為，避免誤動、重複抓、或丟失資料。
> 對象：sector_flow 儀表板相關所有抓取腳本。
> 最後更新：2026-04-17

---

## 0. 核心原則

1. **DB 是 session 之間持久化的狀態**，絕非暫存檔。絕不預設清空。
2. **任何 `DELETE`/`DROP`/`TRUNCATE` 必須先備份 + 使用者授權**。
3. 抓取腳本必須 **idempotent**：重跑不重複抓、不破壞既有資料（用 `INSERT OR REPLACE`）。
4. 錯誤資料（schema 對位錯、單位錯）**先備份、再整表重抓**；不可只覆寫局部。

---

## 1. DB 結構總覽（`data/revenue/revenue.db`）

| 表 | 主鍵 | 內容 | 寫入來源 |
|----|------|------|---------|
| `institutional_flow` | (ticker, trade_date) | 三大法人買賣超（股數 + 金額千元） | `scripts/sector_flow.py` via TWSE T86 |
| `daily_price` | (ticker, trade_date) | 日收盤價 | `scripts/sector_flow.py` via TWSE MI_INDEX / STOCK_DAY_ALL |
| `trading_calendar` | trade_date | 台股實際開盤日 | `scripts/sector_flow.py` via TWSE FMTQIK |
| `margin_flow` | (ticker, trade_date) | 融資融券餘額（單位：張） | `scripts/sector_flow.py --include-margin` via TWSE MI_MARGN + TPEx margin_bal |
| `broker_flow` | (ticker, trade_date, broker_name) | 券商分點（張，僅當日） | `scripts/sector_flow.py --fetch-broker-today` via HiStock `branch.aspx` |
| `futures_oi` | (trade_date, contract, role) | 期貨未平倉（口） | `--include-futures` via TAIFEX CSV（TXF/EXF） |
| `foreign_ownership` | (ticker, trade_date) | 外資持股/上限（%） | `--include-qfii` via TWSE MI_QFIIS + TPEx OpenAPI |
| `shareholder_distribution` | (ticker, data_date, tier_code) | TDCC 集保分級（週資料） | `--include-tdcc` via TDCC OpenData id=1-5 |

---

## 2. 抓取前必做（SOP）

### 2.1 備份

```bash
cp data/revenue/revenue.db data/revenue/revenue.db.bak.$(date +%Y%m%d_%H%M)
```

> **任何會修改 schema 或大量覆寫資料的操作前都要備份**。備份檔保留 ≥ 3 份，超過清舊。

### 2.2 確認當前狀態

```bash
sqlite3 data/revenue/revenue.db "
SELECT 'institutional_flow' tbl, COUNT(*) rows, COUNT(DISTINCT ticker) tickers,
       COUNT(DISTINCT trade_date) dates, MIN(trade_date), MAX(trade_date)
FROM institutional_flow
UNION ALL SELECT 'daily_price', COUNT(*), COUNT(DISTINCT ticker),
       COUNT(DISTINCT trade_date), MIN(trade_date), MAX(trade_date) FROM daily_price
UNION ALL SELECT 'trading_calendar', COUNT(*), 0,
       COUNT(DISTINCT trade_date), MIN(trade_date), MAX(trade_date) FROM trading_calendar;
"
```

### 2.3 評估增量 vs 全量

- 若是**新增日期**（最新資料延伸）→ 直接跑 `sector_flow.py --start X --end Y`，利用 DB 快取
- 若是**欄位 bug/schema 變更**需重抓 → **必須先問使用者**是否清表重抓
- 若是**標的清單擴充**（universe 新增 ticker）→ 新 ticker 從起始日全量補抓

---

## 3. 授權邊界

### 3.1 **無需使用者授權**的操作

- 讀取（SELECT）
- 新增資料列（`INSERT OR REPLACE`，不覆蓋他人資料）
- 新增表（`CREATE TABLE IF NOT EXISTS`）
- 新增索引
- 新增欄位（`ALTER TABLE ADD COLUMN` — 不刪舊欄位）
- 執行 `sector_flow.py` 正常抓取（即便補大量缺漏日也算正常）

### 3.2 **必須先取得使用者授權**的操作

- `DELETE FROM <table>`（任何 WHERE 條件都算）
- `DROP TABLE` / `DROP INDEX`
- `ALTER TABLE DROP COLUMN` / `RENAME COLUMN`
- 覆寫整表（例如 `INSERT OR REPLACE` 但覆蓋 > 50% 現有列數）
- 刪除備份檔
- 跨電腦同步/搬移 DB

### 3.3 授權話術範本

> 「現況：`{表名}` 有 {筆數} 筆資料，跨 {X} 天。
> 偵測到 {問題描述}。
> 建議：先備份 `revenue.db` → {DELETE/ALTER 動作} → 重抓 {預估筆數 × 速率 = 預估時間}。
> 是否授權執行？」

---

## 4. 抓取流程規範（scripts/sector_flow.py）

### 4.1 完整增量抓取

```bash
python3 scripts/sector_flow.py \
    --start <最早未抓日期> --end <今日> \
    --tier <ai_supply_chain|broad_themes|all> \
    --no-save   # 單純補 DB 不寫報告
```

- 預設會按 `trading_calendar` 補缺漏 T86 + MI_INDEX（收盤價）
- 速率：每日兩次 API × 0.4s sleep ≈ 每月 20 天約 16 秒

### 4.2 特定標的補抓

`sector_flow.py` 只抓 `stock_universe.json` 當前 tier 內標的。若要新增 ticker：

1. 修 `research/stock_universe.json` 加入 ticker
2. 清快取：`rm -rf ~/.streamlit/cache/` 或 dashboard 內「從 TWSE 補抓缺漏日期」按鈕
3. 跑 `sector_flow.py --start <新 ticker 起始> --end <今日> --tier <其所屬 tier>`

### 4.3 單位 / 金額回填

- `institutional_flow.foreign_value / invest_value / dealer_value / total_value` 欄位為千元
- 計算方式：`股數 × daily_price.close / 1000`
- 在 `ensure_data()` 中會自動先叫 `ensure_prices()` 抓價，再算 value 一併寫入
- **若 daily_price 該日某 ticker 無資料 → value 會是 0（非 NULL）**。查「金額為 0 但股數非 0」可發現這種髒資料：

```sql
SELECT ticker, trade_date FROM institutional_flow
WHERE total_net != 0 AND (total_value IS NULL OR total_value = 0);
```

發現後手動跑一次 `ensure_prices` 補完，或整天重抓。

---

### 4.4 券商分點特殊規範

- HiStock `branch.aspx` **只有當日資料**，**無歷史回溯**
- 每股 `sleep 2.5 秒`（反爬，勿低於 2 秒）
- 32 檔 ai_supply_chain ≈ 1.3 分鐘
- **建議每日盤後 15:30 cron 執行一次**（`--fetch-broker-today`），歷史靠累積
- 無券商代碼，僅中文名稱；外資判定靠關鍵字（高盛/摩根/美林/花旗/瑞銀/野村/美商/新加坡商/港商/法商/匯豐/麥格理/德意志/日商/星展）
- 只前 15 買方 + 15 賣方，中間量體小的券商不會進 DB

---

## 5. 常見反模式（禁止）

| ❌ 禁止行為 | ✅ 正確做法 |
|------------|-----------|
| `DELETE FROM X` 不備份 | 先 `cp` 備份再動 |
| `DROP TABLE` 重建以「清理」 | 只 `DELETE` 或用 `ALTER TABLE` |
| 用 Python 寫 loop 逐筆 SELECT | 一次 `IN (...)` 批次查詢 |
| 抓 API 不 sleep | 至少 0.4s，大量批次 1s+ |
| 假日也呼叫 TWSE API | 先查 `trading_calendar` 跳過 |
| 忽略 `stat != 'OK'` 就當成功 | 必須檢查 stat + data 非空 |
| 覆寫 `trading_calendar` 無理由 | 該表由 TWSE 權威提供，不手改 |

---

## 6. 偵錯工具

### 6.1 快速健檢

```bash
sqlite3 data/revenue/revenue.db "
-- 每月資料覆蓋率
SELECT substr(trade_date,1,7) AS month,
       COUNT(DISTINCT trade_date) AS days,
       COUNT(*) AS rows
FROM institutional_flow
GROUP BY month ORDER BY month;
"
```

### 6.2 檢測欄位對位錯誤

```sql
-- 若發現 invest_net 絕對值常大於 foreign_net，可能是 T86 欄位對位錯
SELECT AVG(ABS(foreign_net)) AS avg_foreign,
       AVG(ABS(invest_net))  AS avg_invest,
       AVG(ABS(dealer_net))  AS avg_dealer
FROM institutional_flow
WHERE trade_date >= '2026-01-01';
-- 正常台股：外資 >> 自營 > 投信
```

### 6.3 比對原始 API

單日對帳：

```bash
python3 -c "
from scripts.sector_flow import fetch_t86
print(fetch_t86('20260416', {'2330':'台積電'}))
" 
```

再 `SELECT * FROM institutional_flow WHERE ticker='2330' AND trade_date='2026-04-16'` 比對。

---

## 7. T86 欄位對照（重要）

TWSE T86 `response=json` 2022-2026 穩定 19 欄位：

| idx | 欄位 | 存入 DB |
|-----|------|---------|
| 0 | 證券代號 | ticker |
| 1 | 證券名稱 | — |
| 2-4 | 外陸資買/賣/買賣超（不含外資自營） | — / — / foreign_net 的一部分 |
| 5-7 | 外資自營商買/賣/買賣超 | — / — / foreign_net 的另一部分 |
| 8-10 | 投信買/賣/買賣超 | — / — / invest_net |
| 11 | 自營商買賣超（合計） | dealer_net |
| 12-14 | 自營商（自行買賣）買/賣/買賣超 | — |
| 15-17 | 自營商（避險）買/賣/買賣超 | — |
| 18 | 三大法人買賣超 | total_net |

**外資合計規則**：`foreign_net = row[4] + row[7]`（外陸資 + 外資自營商）。
**常見 bug**：誤用 `invest=row[7], dealer=row[10], total=row[11]` — 此版本已於 2026-04-17 修正。

---

## 8. 備份檔管理

- 檔名：`data/revenue/revenue.db.bak.YYYYMMDD_HHMM`
- 保留最近 3 份，超過自動清舊（於 `scripts/sector_flow.py` 啟動時可選執行清理）
- 年度備份另存 `data/archive/revenue.db.yearly.YYYY`

---

*此指引僅適用本專案。跨專案 DB 操作需獨立評估。*
