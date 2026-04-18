# Claude Code 金融分析 Skills 使用指南
**適用專案：台灣科技股投資研究 2025–2027**
*建立日期：2026-03-29 | 資料來源：anthropics/financial-services-plugins*

---

## 一、套件概覽

Claude Code 官方 `financial-services-plugins` 提供 **41 個專業技能（Skills）**、**38 個工作指令**，涵蓋投資銀行、股票研究、私募股權、財富管理四大模組，並整合 11 個機構級 MCP 數據連接器。

安裝方式：
```bash
# 安裝核心模組（必須先裝）
claude plugin install financial-analysis@financial-services-plugins

# 安裝股票研究模組
claude plugin install equity-research@financial-services-plugins

# 安裝投資銀行模組（選用）
claude plugin install investment-banking@financial-services-plugins
```

---

## 二、對本專案最有用的 Skills

### 2-1 核心財務建模

| 指令 | 功能 | 本專案應用場景 |
|------|------|--------------|
| `/dcf` | DCF 現金流折現估值模型 | 南亞科（2408）/ Micron（MU）絕對估值 |
| `/comps` | 可比公司交易倍數分析 | 台灣光通訊族群 vs Lumentum / Coherent |
| `/3-statement-model` | 損益 + 資產負債 + 現金流三表聯動 | 欣興（3037）、南電（8046）完整財務模型 |
| `/audit-xls` | Excel 公式審計與錯誤排查 | 驗證現有估值模型的公式正確性 |
| `/clean-data-xls` | 清理雜亂試算表數據 | 整理從 MOPS 匯出的原始財務數據 |

### 2-2 股票研究（最貼近本專案工作流程）

| 指令 | 功能 | 本專案應用場景 |
|------|------|--------------|
| `/earnings` | 季報分析 + 研究更新報告（8-12 頁） | 每季法說會後快速產出分析 |
| `/earnings-preview` | 法說前三情境預測 | 對應 CLAUDE.md 的 Bear/Base/Bull 框架 |
| `/thesis` | 建立或更新投資論文 | 南亞科、欣興等核心持倉的論點更新 |
| `/initiate` | 機構級啟動覆蓋報告 | 新進標的（如景碩 3189）深度研究 |
| `/screen` | 股票篩選與投資想法生成 | 台灣半導體族群新標的發掘 |
| `/catalysts` | 催化劑日曆管理 | 對應短線/中線/長線催化劑追蹤框架 |
| `/morning-note` | 晨間快報草稿 | 月營收公布日（每月 10 日）快速彙整 |
| `/sector` | 產業概覽報告 | CPO 滲透率、ABF 超循環結構性分析 |

### 2-3 競爭與風險分析

| 指令 | 功能 | 本專案應用場景 |
|------|------|--------------|
| `/competitive-analysis` | 競爭格局分析 | ABF 載板三雄 vs 日韓競爭者；CXMT 風險量化 |
| `/sector` | 產業深度報告 | CPO 光通訊滲透率結構性分析 |

---

## 三、時間軸使用指南

### 3-1 每月固定節奏

| 時間 | 觸發事件 | 使用指令 | 說明 |
|------|---------|---------|------|
| 每月 **5–9 日** | 法說前準備期 | `/earnings-preview` | 當月有法說的公司先建三情境預測 |
| 每月 **10 日前後** | 台股月營收公布 | `/revenue-update` → `/morning-note` | 先跑月營收更新，再產出市場影響快報 |
| 每月 **10–15 日** | 月營收解讀期 | `/thesis`（僅有重大變化時） | 若月營收偏離預期超過 ±10%，更新投資論文 |
| 每月 **20–31 日** | 美股財報季（Q 末月） | `mcp__sec-edgar` → `/earnings` | 抓 Micron / MSFT 10-Q，分析宏觀傳導影響 |

---

### 3-2 季度關鍵時程（2026 年）

#### Q1 2026 法說會季（4–5 月）

```
4 月上旬（法說前 2 週）
    → /earnings-preview         為各標的建立 Bear/Base/Bull 三情境
    → /catalysts                確認所有標的法說日期，更新催化劑日曆

4 月中旬（法說週）
    → /earnings                 法說當天或隔日：完整 5 步驟季報分析
                                重點：毛利率 QoQ/YoY、產能利用率、CapEx 指引

4 月下旬 – 5 月上旬（法說後更新）
    → /thesis                   更新投資論文（毛利率拐點確認 or 推遲）
    → /dcf + /comps             更新雙法估值 → 加權目標價
    → /audit-xls                驗證更新後 Excel 模型公式正確性
```

**Q1 2026 重點法說參考日期**
| 公司 | 代碼 | 預計法說時間 | 重點觀察 |
|------|------|------------|---------|
| 南亞科技 | 2408 | 2026 年 4 月 | 1B 量產進度、2026 CapEx NT$500 億執行率 |
| 華邦電子 | 2344 | 2026 年 4 月 | 16nm CMS 節點轉換進度、新唐拆分毛利率 |
| 欣興電子 | 3037 | 2026 年 4 月 | T-Glass 瓶頸解除時程、AI 營收佔比 |
| 南電 | 8046 | 2026 年 4 月 | 已於 2026-03-17 法說更新，對照 Q1 數字 |
| 景碩科技 | 3189 | 2026 年 4 月 | 已於 2026-03-17 法說更新，EPS 共識 NT$6.3–8.0 |

---

#### Q2–Q4 2026 季度週期（重複執行）

```
每季法說前 2 週
    → /earnings-preview

每季法說當週
    → /earnings

每季法說後 1–2 週
    → /thesis（如論點有變化）
    → /dcf + /comps（季度目標價更新）
```

---

### 3-3 年度與專題研究時程

| 時間 | 研究任務 | 使用指令 | 說明 |
|------|---------|---------|------|
| **每年 Q1 末**（3–4 月） | 年度產業報告 | `/sector` | CPO 滲透率年度更新；ABF 超循環週期確認 |
| **每年 Q2**（5–6 月） | 競爭格局審查 | `/competitive-analysis` | CXMT DDR3 滲透速度、三星 P4 fab 時程更新 |
| **每年 Q3**（8–9 月） | 新標的評估 | `/screen` → `/initiate` | 篩選台灣半導體族群新進標的，達標則啟動完整覆蓋 |
| **每年 Q4**（11–12 月） | 年度估值審查 | `/dcf` + `/comps` + `/audit-xls` | 更新隔年 EPS 假設，重設三情境加權目標價 |
| **隨時（新進標的）** | 首次研究 | `/initiate` → `/competitive-analysis` | 新標的第一次研究固定走此組合 |

---

### 3-4 事件驅動使用時機

| 觸發事件 | 緊急程度 | 立即使用指令 |
|---------|---------|------------|
| Hyperscaler（MSFT/Google/AWS）財報公布 | 高 | `mcp__yahoo-finance` → `/morning-note` |
| NVIDIA 季報 / GTC 大會 | 高 | `/thesis`（CPO、ABF 影響評估） |
| 美中出口管制新措施 | 高 | `/competitive-analysis`（地緣政治風險章節） |
| 競爭對手重大消息（三星 HBM4、CXMT 擴產） | 中 | `/thesis`（風險章節更新） |
| 月營收大幅偏離（±15% 以上） | 中 | `/earnings-preview`（情境概率重新校準） |
| 新供應商認證消息（如上詮 TSMC COUPE 進展） | 中 | `/thesis`（催化劑章節更新） |
| 個股急漲 >20%（估值過熱檢查） | 中 | `/comps`（倍數泡沫化確認） |
| 市場大跌（台股 >5%） | 低 | `/screen`（尋找超跌機會） |

---

## 四、Python 腳本對照表與整合時機

### 4-1 現有 Python 腳本功能總覽

| 腳本路徑 | 功能 | 輸出 | 執行頻率 |
|---------|------|------|---------|
| `scripts/fetch_revenue.py` | 從 winvest.tw / histock.tw 抓月營收 → 存入 SQLite | `data/revenue/revenue.db` + JSON | 每月 10 日 |
| `scripts/revenue_live.py` | 即時爬取月營收（不依賴本地DB，Plan B） | dict 物件（可獨立執行） | 隨需 |
| `scripts/fetch_prices.py` | 從 yfinance 抓股價、市值（含 .TW/.TWO） | 終端表格 / list[dict] | 每日 / 隨需 |
| `scripts/indicators.py` | 計算 RSI(14)、MACD(12/26/9)、MA(20/60) | dict（含趨勢判斷） | 每日 / 隨需 |
| `scripts/run_report.py` | 主入口：整合股價 + 月營收 + 技術指標 → 日報 | `reports/YYYY-MM-DD_日報.md` | 每日 |
| `scripts/monthly_report.py` | 月報：5步驟分析框架 + 估值三情境模板 | `reports/monthly_report_YYYYMM.md` | 每月 |
| `scripts/export_revenue.py` | 匯出月營收資料庫為 CSV / Excel（3 工作表） | `data/revenue_tracker.xlsx` | 每月 / 季度 |
| `Type/DRAM/build_earnings_reports.py` | 產生華邦電、Micron 季報 Word 文件（含圖表） | `.docx` 研究報告 | 季度法說後 |
| `Type/DRAM/build_comps.py` | 記憶體產業同業比較 Excel（含顏色格式） | `comps.xlsx` | 季度估值審查 |

---

### 4-2 Python 腳本 ↔ Claude Skills 整合對照

```
【資料層：Python 先跑，備妥數據】
fetch_revenue.py  →  提供月營收數字給  →  /revenue-update、/morning-note、/earnings
fetch_prices.py   →  提供股價市值給    →  /comps、/dcf（市場定價參考）
indicators.py     →  提供技術面數據給  →  /thesis（進出場訊號判斷）
export_revenue.py →  輸出 Excel 給     →  /audit-xls（公式審計）、/comps

【分析層：Claude Skills 接手深度分析】
monthly_report.py（5步驟模板框架）→ 再交給 /earnings 深化分析
build_comps.py（同業比較底稿）   → 再交給 /comps 補充倍數解讀與結論
build_earnings_reports.py（季報底稿）→ 再交給 /earnings 加入前瞻分析
```

---

### 4-3 時間軸：Python 與 Skills 的分工時機

#### 每日（有交易日）
```bash
# Step 1：Python 自動執行（約 1 分鐘）
python3 scripts/run_report.py
# → 輸出：reports/YYYY-MM-DD_日報.md（股價 + 技術指標 + 月營收摘要）

# Step 2：若有技術面異常預警（RSI > 70 或 < 30）
#         再叫 Claude 進一步分析
→ 提供日報給 Claude + /thesis（更新出場/進場邏輯）
```

#### 每月 8–10 日（月營收公布）
```bash
# Step 1：Python 抓取數據
python3 scripts/fetch_revenue.py --ticker 2408 2344 3363 2455 4979 3081 3037 8046 3189

# Step 2：匯出供閱覽
python3 scripts/export_revenue.py --summary   # 終端快照
python3 scripts/export_revenue.py             # 輸出 Excel

# Step 3：產月報框架
python3 scripts/monthly_report.py --month 2026-03

# Step 4：把月報 .md 交給 Claude 深化分析
→ /revenue-update    快速月營收彙整
→ /morning-note      產出市場影響快報
→ /earnings          若本月有法說，做完整 5 步驟分析
```

#### 法說前 1–2 週
```bash
# Python 不需執行（數據已備妥）
# 直接使用 Claude Skills：
→ /earnings-preview  建立 Bear / Base / Bull 三情境
→ /catalysts         確認並更新催化劑日曆
```

#### 法說後（季報週）
```bash
# Step 1：Python 產出季報底稿文件
python3 Type/DRAM/build_earnings_reports.py
# → 輸出：華邦電 + Micron 季報 .docx（含圖表）

# Step 2：把 .docx 提供給 Claude 做深度分析
→ /earnings          完整季報分析（5 步驟 + 前瞻）
→ /thesis            更新投資論文

# Step 3：更新估值模型
python3 Type/DRAM/build_comps.py
# → 輸出：同業比較底稿 comps.xlsx

# Step 4：把 comps.xlsx 提供給 Claude
→ /comps             補充倍數解讀與市場隱含預期
→ /dcf               更新 DCF 估值 → 加權目標價
→ /audit-xls         驗證 Excel 模型公式正確性
```

#### 季度估值審查（每季末）
```bash
# Step 1：匯出完整數據
python3 scripts/export_revenue.py --format excel

# Step 2：Claude 建立完整三表模型
→ /3-statement-model   輸入最新財報數字 → 損益表 + 資產負債表 + 現金流
→ /dcf + /comps        雙法估值 → 加權目標價更新
→ /audit-xls           審計 Excel 公式

# Step 3：年度報告（Q1 末）
→ /sector              CPO 滲透率年度報告
→ /competitive-analysis 競爭格局年度審查（CXMT / 三星風險）
```

---

### 4-4 自動化整合建議

#### 方案一：每日定時執行（cron）
```bash
# 每個工作日 08:00 自動產出日報
0 8 * * 1-5 cd /Users/wayne/Desktop/Invest/taiwan-stock-analysis && python3 scripts/run_report.py
```

#### 方案二：月營收公布日自動提醒（每月 10 日）
```bash
# 每月 10 日 09:00 自動抓月營收 + 產月報框架
0 9 10 * * cd /Users/wayne/Desktop/Invest/taiwan-stock-analysis && \
  python3 scripts/fetch_revenue.py && \
  python3 scripts/monthly_report.py && \
  python3 scripts/export_revenue.py
```

> 提示：以上 cron 可透過 `/schedule` 指令請 Claude Code 協助設定

#### 方案三：Claude Code `/loop` 定期監控
```bash
# 每 10 分鐘監控技術面異常
/loop 10m python3 scripts/run_report.py
```

---

## 五、建議工作流程整合（完整版）

```
【每日】
  python3 scripts/run_report.py               ← 日報自動產出
  → 若有 RSI 異常預警 → /thesis（進出場邏輯）

【每月例行】
月 5–9 日    → /earnings-preview（有法說的標的）
月 10 日前後 → python3 scripts/fetch_revenue.py
             → python3 scripts/monthly_report.py
             → /revenue-update → /morning-note
月 10–15 日  → /thesis（若月營收偏離 ±10% 以上）
             → python3 scripts/export_revenue.py（更新 Excel）

【每季例行】
法說前 2 週  → /earnings-preview（三情境建立）
             → /catalysts（確認所有法說日期）
法說當天     → /earnings（5 步驟完整分析）
法說後 1 週  → python3 Type/DRAM/build_earnings_reports.py
             → /thesis（更新投資論文）
             → python3 Type/DRAM/build_comps.py
             → /dcf + /comps（更新加權目標價）
             → /audit-xls（驗證 Excel 模型）

【年度例行】
Q1 末        → /sector（年度產業深度報告）
Q2           → /competitive-analysis（競爭格局年度審查）
Q3           → /screen → /initiate（新標的篩選與啟動覆蓋）
Q4           → /dcf + /comps + /audit-xls（年度估值審查）

【事件驅動】
Hyperscaler 財報  → /morning-note
重大地緣政治事件  → /competitive-analysis
估值明顯過熱      → /comps
市場急跌          → /screen
```

---

## 四、可用 MCP 數據連接器

### 本專案已啟用（免費）
| MCP 名稱 | 用途 | 適用標的 |
|---------|------|---------|
| `mcp__yahoo-finance` | 股價、財報、新聞 | MU、MSFT、Lumentum、Coherent |
| `mcp__fred` | 宏觀數據（利率、工業產出、庫存） | 宏觀校準指標 |
| `mcp__sec-edgar` | 美國公司 10-Q / 10-K 申報文件 | Micron（MU）深度財務分析 |

### 套件支援（需付費訂閱）
- FactSet、S&P Global、Morningstar、PitchBook、LSEG
- 適合機構用戶，個人研究使用上述免費來源即可

### 台灣公司數據（需手動提供）
台灣上市公司財報目前無法透過 MCP 自動拉取，需透過以下方式：
1. **本機 PDF 財報**：`/Users/wayne/Desktop/Invest/Type/` 各子資料夾
2. **MOPS 手動查詢**：`mops.twse.com.tw`（官方月營收來源）
3. **Web Fetch 補充**：`histock.tw`、`winvest.tw` 靜態頁面

---

## 五、各核心標的建議指令組合

### DRAM 主題（南亞科 2408、華邦電 2344）

#### 最新數據快照（scripts 自動產出，更新日：2026-03-29）

| 指標 | 南亞科技（2408） | 華邦電子（2344） |
|------|----------------|----------------|
| **收盤價** | NT$219.5（-2.66%） | NT$92.4（-3.25%） |
| **市值** | NT$6,801 億 | NT$4,158 億 |
| **2月營收** | NT$156.07 億 | NT$119.73 億 |
| **MoM** | +1.9% | +1.6% |
| **YoY** | **+586.7%** | +88.5% |
| **RSI14** | 42.0（偏弱） | 39.1（偏弱） |
| **MACD** | 死叉↓ | 死叉↓ |
| **MA20 偏離** | -9.5%（跌破） | -15.3%（跌破） |
| **MA60 偏離** | -11.7%（跌破） | -11.9%（跌破） |
| **技術趨勢** | 弱勢（跌破雙均線） | 弱勢（跌破雙均線） |
| **2025Q4 毛利率** | 49.0%（QoQ +30.5pp） | 41.9%（合併） |
| **2025 全年 EPS** | NT$2.13 | NT$0.88 |
| **2026E EPS（市場）** | NT$15–25 | NT$4–8 |
| **每股淨值** | NT$54.99 | ~NT$21 |
| **隱含 PB（當前）** | ~4.0x | ~4.4x |
| **來源** | fetch_prices.py + revenue.db | fetch_prices.py + revenue.db |

> ⚠️ **技術面警示（2026-03-29）**：兩者均跌破 MA20 / MA60，RSI 進入偏弱區，相較 3 月 17 日高點（2408: NT$271.5、2344: NT$123.5）分別回撤 **-19.1%** 與 **-25.2%**。留意是否為超跌布局機會或趨勢反轉訊號，建議搭配 `/thesis` 評估進出場邏輯。

#### 關鍵財務底稿（來源：Type/DRAM/ 本機 PDF + 法說文件）

**南亞科技（2408）**
- 1B 製程：已量產；1C 目標 2027 量產
- 2026 CapEx：NT$500 億（歷史最高，待董事會決議）；F 廠 2027 年初裝機
- 流通股數：30.99 億股 | 每股淨值：NT$54.99
- 2025 全年營收：NT$665.87 億；Q4 毛利率 49.0% 歷史性跳升

**華邦電子（2344）**
- 16nm CMS（Specialty DRAM）2026 年量產；24nm Flash 同步轉換
- CUBE 3D 堆疊專案：2026H2 起有客戶應用，2027 年目標貢獻實質營收
- 2026–2027 合計 CapEx：NT$400 億（Flash 擴產 + CMS 升級）
- 產能：2026 全年滿載預訂
- ⚠️ 合併毛利率受新唐（4919）Logic IC 稀釋 ~9pp，分析務必拆分記憶體段落

#### 建議指令組合
```bash
# 當前技術面偏弱，優先確認基本面支撐
/thesis             # 更新：回撤是否改變投資論點？確認 EPS 上修趨勢是否完整
/earnings-preview   # 法說前（4月）：HBM/DDR5 需求三情境 + Bear 加入技術面壓力
/earnings           # 法說後：毛利率拐點確認 + EPS 槓桿分析
/dcf                # 超級循環高峰 EPS 代入絕對估值（2026E NT$15–25 / NT$4–8）
/comps              # vs Micron（MU）、SK Hynix 倍數比較；確認當前 PB 4x 是否合理
```

> **更新指令**（每月 10 日月營收公布後執行）：
> ```bash
> python3 scripts/fetch_revenue.py --ticker 2408 2344
> python3 scripts/fetch_prices.py
> python3 scripts/run_report.py
> ```

### CPO 光通訊主題

#### 全追蹤標的快照（scripts 產出，更新日：2026-03-29）

**原有五支（L1/L2 核心層）**

| 代碼 | 公司 | 層級 | 收盤價 | 市值 | 2月營收 | YoY | 定位 |
|------|------|------|--------|------|--------|-----|------|
| 3363 | 上詮光纖 | L3 FAU | NT$642 | NT$730億 | NT$1.28億 | +27.7% | TSMC COUPE 唯一認證光通訊夥伴 |
| 2455 | 全新光電 | L1 磊晶 | NT$270.5 | NT$497億 | NT$0.31億 | +15.9% | 台灣唯一 InP+GaAs 雙平台，LITE 直接供應商 |
| 4979 | 華星光通 | L3 封裝 | NT$396.5 | NT$558億 | NT$0.33億 | -10.0% ⚠️ | Marvell 客戶 85-95%，CW Laser 後段 |
| 3081 | 聯亞光電 | L1 磊晶 | NT$1,720 | NT$1,591億 | NT$2.90億 | **+91.4%** | CW Laser InP 磊晶，LITE 直接供應商 |
| 3105 | 穩懋半導體 | L2 晶圓代工 | NT$382.5 | NT$1,622億 | NT$14.74億 | +25.9% | GaAs 純代工，LITE 一階客戶（二階受益） |

**新增五支（L3/L4/測試層）**

| 代碼 | 公司 | 層級 | 收盤價 | 市值 | 2月營收 | YoY | 定位 |
|------|------|------|--------|------|--------|-----|------|
| 6442 | 光聖 | L3 連接 | NT$2,115 | NT$1,647億 | NT$7.39億 | **+44.1%** | 高芯數光纖跳接線，CPO 互連核心材料 |
| 4977 | 眾達-KY | L3 ELS組裝 | NT$200 | NT$158億 | NT$0.88億 | -17.4% ⚠️ | Broadcom CPO ELS 唯一供應；MoM +169% 但 YoY 仍負 |
| 3163 | 波若威 | L2 收發器 | NT$854 | NT$688億 | NT$1.74億 | +5.3% | 光收發器模組；2025 全年 NT$22.26億 |
| 2345 | 智邦 | L4 系統 | NT$1,655 | NT$9,250億 | NT$235.83億 | **+82.7%** | 800G CPO 交換器，AI 基礎設施系統層 |
| 6223 | 旺矽 | 測試 | NT$3,665 | NT$3,479億 | NT$13.16億 | **+45.5%** | MEMS Probe Card；CPO 量產測試需求爆發受益 |

> ⚠️ 華星光通（4979）2月 YoY -10.0%，MoM -20.1%，族群唯一負成長，需追蹤 Marvell SiPh 外包策略變化。
> ⚠️ 眾達-KY（4977）YoY -17.4%，等待 Broadcom CPO ELS 正式放量（預期 2026H2）。

---

#### 推薦新增｜台股

##### 第二圈擴充（建議正式納入追蹤）

| 代碼 | 公司 | 層級 | 2月營收 | YoY | 股價 | 市值 | 新增理由 |
|------|------|------|--------|-----|------|------|---------|
| **6442** | **光聖** | L3 連接材料 | NT$7.39億 | +44.1% | ~NT$1,690 | 大型 | 高芯數光纖跳接線，CPO 互連核心材料；2025全年NT$105億；NVIDIA 生態系受益 |
| **6223** | **旺矽** | L3 測試 | — | — | — | 中型 | MEMS Probe Card 龍頭；CPO 量產後測試需求爆發受益；2025 EPS NT$33.49；2026 年增目標 40% |
| **2345** | **智邦** | L3 系統 | NT$235.83億 | +82.7% | NT$1,655 | 大型 | 800G CPO 交換器量產；1.6T CPO 次世代佈局；YoY +82.7% 顯示 AI 交換器需求強烈 |

##### 觀察名單（尚待業績確認）

| 代碼 | 公司 | 層級 | 2月營收 | YoY | 觀察重點 |
|------|------|------|--------|-----|---------|
| **4977** | **眾達-KY** | L2 ELS組裝 | NT$0.88億 | -17.5% ⚠️ | Broadcom CPO ELS 唯一供應鏈；2月 MoM +169% 但 YoY 仍負；等待 Broadcom CPO 正式放量確認 |
| **3163** | **波若威** | L2 收發器模組 | NT$1.74億 | +5.3% | VCSEL 光收發器；2025全年NT$22億；800G 模組出貨進度待確認 |

---

#### 推薦新增｜美股參考標的

| 代碼 | 公司 | 定位 | 新增理由 |
|------|------|------|---------|
| **LITE** | **Lumentum Holdings** | CW Laser / CPO 雷射晶片龍頭 | CEO 宣布 2026「雷射晶片爆發年」；已收史上最大單筆 CPO 超高功率雷射訂單；聯亞（3081）/ 全新（2455）InP 磊晶最大下游客戶；Q2 2026 季營收目標 $600M+；一階受益者，正式升格追蹤 |
| **MTSI** | **MACOM Technology** | 高速類比光子半導體 | FQ1 2026 營收 $271.6M（YoY +24.5%）；資料中心業務上修至 YoY +35-40%；1.6T 收發器類比前端晶片 + CW laser 製造；直接對應聯亞/全新光電的美系對標 |
| **AAOI** | **Applied Optoelectronics** | 垂直整合 LPO 收發器 | 美國本土製造戰略資產；LPO 低功耗方案，Microsoft 主要供應商；作為 LPO vs CPO 路線競爭的風險對沖標的 |
| **MRVL** | **Marvell Technology** | CPO ASIC + SiPh IC | 華星光通（4979）最大客戶（佔比 85-95%）；Marvell 自研 SiPh 光引擎進度直接影響 4979 訂單；建議正式升格為第三圈追蹤 |

##### 美股標的業務定位詳解（2026-03-29 更新）

**LITE vs COHR 本質差異**

| 面向 | LITE（Lumentum） | COHR（Coherent） |
|------|-----------------|-----------------|
| 定位 | **上游雷射晶片廠**（die level） | **垂直整合型全鏈廠**（材料→模組） |
| FY2025 營收 | $16.5億 | $58.1億（3.5倍大）|
| AI 業務佔比 | 85%+（Cloud & Networking）| 約 59%（Networking $34.2億）|
| CPO 角色 | **CW Laser 光源供應者**（CPO 心臟）| **收發器模組廠**（參與 CPO 但非核心光源）|
| NVIDIA 關係 | $20億投資 + 多年採購承諾；**UHP 雷射鎖定供應** | $20億投資；**Spectrum-X 認證模組夥伴** |
| 對台灣 L1 磊晶 | **直接採購 3081/2455 InP 磊晶** | 有自有材料部門，較少外購台灣 InP |
| EML 市佔 | 全球 **50-60%**（800G/1.6T 核心）| 較低 |
| 收發器市佔 | 擴張中（1.6T 模組 2026 夏量產）| 全球 **~25%** |

**LITE InP 擴產事實（已公開確認，需長期追蹤）**

| 時程 | 事件 | 對台股影響 |
|------|------|---------|
| 2024 底 | 啟動現有 4 座 fab InP 產能 +40% | 中性（需求同步增加，仍需外購）|
| 2025 Q3–Q4 | 再追加 +40%，過半完成 | 中性偏正（under-shipping 25-30%，外包增加）|
| **2025 Q4 → 2026 Q4** | **再追加 +50%（現有 4 fab 執行）** | ✅ **利多**：仍需外購補缺口 |
| **2026-03-02** | **NVIDIA $20億戰略投資 + 多年採購承諾** | ✅ 3081/2455 訂單能見度提升 |
| **2026 夏季** | 1.6T 模組開始出貨，使用 LITE 自有雷射 | 觀察 CW Laser 自製 vs 外購比例 |
| **2028 年中** | **北卡第 5 座 InP fab 量產**（240,000 sq ft）| ⚠️ 專注 UHP，CW Laser 影響待定 |

> **關鍵區分**：北卡新 fab 主力為 **UHP（超高功率）雷射**，非 3081/2455 主力產品 CW Laser。近中期（2025-2026）產業趨勢為**外包增加**（TrendForce 2025/12 確認），3081/2455 風險延後至 2028 年後，屆時需確認北卡 fab 是否擴展至 CW Laser 品項。

**現有美股參考標的**

| 代碼 | 公司 | 2026 關鍵訊號 |
|------|------|-------------|
| COHR | Coherent | NVIDIA Spectrum-X 認證合作夥伴；FY2025 營收 $5.81B（YoY +23%）；光收發器全球市佔 ~25%；垂直整合型，非台灣 InP 直接採購方 |
| FN | Fabrinet | 新廠破土動工（200 萬平方呎，+50% 產能）；可釋放額外年營收 $2.4B；2026 年增 28.5% 預估 |

---

#### CPO 產業關鍵里程碑（2026–2028）

| 時程 | 事件 | 相關標的 | 意義 |
|------|------|---------|------|
| **2026 Q1–Q2** | TSMC COUPE 平台量產導入 | 3363（唯一認證） | 結構性訂單鎖定 |
| **2026 Q2** | LITE 季營收目標 $600M+ | LITE → 3081/2455 訂單確認 | 外購需求驗證 |
| **2026 Q2** | 上詮 1.6T CPO FAU 系統廠驗證結果 | 3363 | 最重要催化劑 |
| **2026 夏季** | LITE 1.6T 模組出貨（使用自有雷射） | 3081/2455 外購比例觀察點 | 關鍵觀察 |
| **2026 下半年** | 全球 800G+ 收發器 24M → 63M（YoY +163%） | 全鏈受益 | 需求量化驗證 |
| **2026 H2** | 眾達-KY Broadcom CPO ELS 正式放量 | 4977 轉正關鍵 | 觀察名單轉正條件 |
| **2026 H2** | 旺矽 MEMS Probe Card CPO 量產測試 | 6223 | 新需求確認 |
| **2027** | CPO 滲透率突破 10%（結構性訊號） | 全鏈估值重評 | 長線里程碑 |
| **2028 年中** | LITE 北卡第 5 座 InP fab 量產（UHP 專用） | 3081/2455 長線風險點 | ⚠️ 追蹤是否擴展至 CW Laser |

---

#### 供應鏈完整圖譜（2026-03-29 更新，含美系上下游）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 美系需求端（訂單來源）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 NVIDIA / Broadcom        → CPO ASIC 設計，定義規格
 Marvell（MRVL）          → SiPh 光引擎 IC，直接向 4979 下單
 LITE（Lumentum）         → CW Laser 晶片廠，向 3081/2455 買 InP 磊晶
                            ★ 自有 4 座 InP fab + 2028 北卡第 5 座（UHP 專用）
                            ★ NVIDIA $20億投資（2026-03）
 COHR（Coherent）         → 垂直整合型，主賣整模組給 Hyperscaler
                            ★ 有自有材料部門，較少外購台灣 InP
                            ★ NVIDIA $20億投資，Spectrum-X 認證夥伴
 MTSI（MACOM）            → 類比光子前端 IC，1.6T 驅動晶片
 FN（Fabrinet）           → 全鏈最終組裝代工
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 台灣供應鏈（由上游至系統層）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 [L1 磊晶層] — 技術壁壘最高，LITE 直接採購方
   聯亞光電 3081  InP CW Laser 磊晶 ──採購──→ LITE / COHR（少量）
   全新光電 2455  InP+GaAs 雙平台   ──採購──→ LITE / 台灣封裝廠
        ↓ 磊晶片供應
 [L2 晶圓代工層]
   穩懋半導體 3105  GaAs 晶圓代工   ──採購──→ LITE（一階客戶，二階受益）
   波若威   3163   光收發器模組     ──出貨──→ 資料中心（CPO+傳統插拔並行）
        ↓ 元件供應
 [L3 封裝／連接層] — 台灣最核心差異化層
   華星光通 4979   CW Laser 後段封裝 ──出貨──→ Marvell（85-95%集中）
   上詮光纖 3363   FAU 光纖陣列     ──認證──→ TSMC COUPE（唯一認證，護城河 2-3 年）
   光聖     6442   高芯數光纖連接器  ──出貨──→ 資料中心佈線
   眾達-KY  4977   ELS 雷射光源組裝  ──出貨──→ Broadcom CPO（2026H2 放量）
        ↓ 模組整合
 [L4 系統層]
   智邦     2345   CPO 交換器系統   ──出貨──→ 超大規模雲端廠商
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 [測試層] — 橫跨各層，量產規模正比
   旺矽     6223   MEMS Probe Card  — 每層晶片量產皆需探針測試
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 ★ 關鍵上下游依存關係
   LITE 訂單   →  3081 / 2455（最直接指標）
   Marvell 策略 →  4979（85-95% 集中，風險最高）
   TSMC COUPE  →  3363（結構性護城河）
   Broadcom    →  4977（2026H2 放量為轉正條件）
   NVIDIA CapEx →  整鏈（系統性指標）
```

---

#### 建議指令組合
```bash
# 現有持倉論文更新
/thesis             # 華星光通（4979）YoY 轉負異常確認
/earnings           # 聯亞（3081）法說後：新增 CSP 客戶確認

# 新增標的初始研究（建議優先順序）
/initiate 6442      # 光聖：高芯數光纖連接器完整覆蓋
/initiate 2345      # 智邦：CPO 交換器系統層定位分析
/initiate MTSI      # MACOM：美股光子類比半導體切入角度
/initiate LITE      # Lumentum：CW Laser 龍頭，台灣供應鏈一階下游

# 產業競爭格局
/competitive-analysis  # L1 磊晶：聯亞 vs 全新 vs LITE 內部供應（外購 vs 自製比例）
/competitive-analysis  # LITE vs COHR：CW Laser 晶片廠 vs 垂直整合模組廠策略分歧
/sector             # 2026 CPO 滲透率年度報告（含 LPO vs CPO 路線競爭）

# 觀察名單確認
/screen             # 眾達 4977 / 波若威 3163 業績確認後重評
```

> **更新指令**（每月 10 日月營收公布後執行）：
> ```bash
> python3 scripts/fetch_revenue.py --ticker 3363 2455 4979 3081 3105 6442 4977 3163
> python3 scripts/fetch_prices.py
> python3 scripts/run_report.py
> ```

### IC 載板主題（欣興 3037、南電 8046、景碩 3189）
```bash
/earnings           # 季報：ABF 產能利用率 + T-Glass 瓶頸
/3-statement-model  # 欣興 / 景碩 完整三表財務模型
/comps              # 台灣三雄 vs 日本 Ibiden / Shinko
/earnings-preview   # 2026 CapEx 週期高峰三情境預測
```

---

## 六、注意事項

1. **台灣財報數據須手動輸入**：Skills 建模時，請先提供從本機 PDF 或 MOPS 取得的財務數字，Claude 才能正確建立模型。

2. **三情境必須對齊 CLAUDE.md 規範**：每次使用 `/earnings-preview` 或 `/dcf` 時，Bear（20%）/ Base（55%）/ Bull（25%）概率設定須與專案規則一致。

3. **華邦電需拆分子公司**：使用 `/3-statement-model` 分析華邦電時，務必要求拆分新唐（4919）子公司，避免合併毛利率稀釋 ~9pp 影響純記憶體段落估值。

4. **DeepSeek 尾部風險**：使用 `/earnings-preview` 時，Bear 情境必須納入 AI 效率突破導致 Hyperscaler CapEx 下修的需求衝擊。

---

*最後更新：2026-03-29（DRAM + CPO 快照由 fetch_prices.py + revenue_live.py 自動產出）*
*參考來源：[anthropics/financial-services-plugins](https://github.com/anthropics/financial-services-plugins)*
