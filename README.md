# 台灣科技股投資研究 — Claude Code 專案

## 快速開始

### 1. 初始化 / 更新月營收資料庫

```bash
python3 scripts/fetch_revenue.py --ticker 2408 2344 3363 2455 4979 3081 3105 6442 4977 3163 2345 6223
```

### 2. 產出日報（每日收盤後）

```bash
python3 scripts/run_report.py
```

### 3. 產出月報（每月 10 日後執行）

```bash
python3 scripts/monthly_report.py --month 2026-03
```

---

## 目錄結構

```
taiwan-stock-analysis/
├── CLAUDE.md                  ← 核心：Claude 永久分析規則（每次對話自動載入）
├── README.md                  ← 本說明
├── .claude/
│   ├── settings.json          ← Claude Code 權限設定
│   └── commands/              ← 自訂 Slash 指令
│       ├── deep-analysis.md   ← /deep-analysis 五步驟深度分析
│       ├── earnings-checklist.md ← /earnings-checklist 財報更新清單
│       ├── markitdown.md      ← /markitdown PDF/HTML 轉 Markdown
│       ├── revenue-update.md  ← /revenue-update 月營收自動更新
│       └── risk-check.md      ← /risk-check 五大風險評估
├── data/
│   ├── revenue.db             ← 月營收 SQLite 資料庫（自動建立）
│   └── revenue_YYYYMM.json    ← 每月匯出快照
├── docs/
│   └── Claude_Financial_Skills_Guide.md ← Claude Code 金融 Skills 使用指南
├── reports/
│   ├── deep_analysis_{ticker}_{date}.md ← 深度分析報告
│   ├── risk_check_{date}.md   ← 風險評估報告
│   ├── valuation_{ticker}_{date}.md ← 估值模型
│   └── archive/               ← 舊報告歸檔（日報、月報）
├── research/                  ← 核心知識庫（JSX 儀表板 + MD 參照卡 + 財務快照）
│   ├── 記憶體超級循環供應鏈全景圖.jsx
│   ├── 台灣記憶體三情境估值儀表板.jsx
│   ├── 記憶體產業重點公司基本資料卡.md
│   ├── 光通訊CPO供應鏈全景圖.jsx
│   ├── 光通訊CPO產業重點公司基本資料卡.md
│   ├── PCB載板供應鏈全景圖.jsx
│   ├── PCB載板產業重點公司基本資料卡.md
│   ├── PCB載板_研究索引.md
│   ├── 財務數據基準.md        ← 主財務數據（所有標的最新季）
│   ├── 財務快照_DRAM.md       ← DRAM 快照（最近 2 季）
│   ├── 財務快照_CPO.md        ← CPO 快照（最近 2 季）
│   ├── 財務快照_PCB.md        ← PCB 快照（最近 2 季）
│   ├── 追蹤標的清單.md        ← 核心追蹤標的 + 催化劑時間軸
│   ├── MU_Micron_financials.md
│   └── SNDK_SanDisk_financials.md
├── scripts/                   ← 所有 Python 自動化腳本
│   ├── build_comps.py         ← 比較分析產出腳本
│   ├── build_earnings_reports.py ← 財報分析腳本
│   ├── export_revenue.py      ← CSV/Excel 匯出工具
│   ├── fetch_prices.py        ← 股價快照 + 技術指標（yfinance）
│   ├── fetch_revenue.py       ← 月營收抓取（winvest.tw）
│   ├── indicators.py          ← RSI、MACD、MA 計算模組
│   ├── monthly_report.py      ← 月報產出工具
│   ├── render_html.py         ← 靜態 HTML 儀表板產出
│   ├── revenue_live.py        ← 即時營收查詢
│   ├── run_report.py          ← 日報主入口（整合股價+營收+技術指標）
│   └── run_report_b.py        ← 日報 Plan B（平行版）
└── Type/                      ← 財報 PDF 原始資料
    ├── DRAM/
    │   └── 財報 PDF（南亞科 2408、華邦電 2344、力成 6239、Micron、Kioxia）
    ├── CPO/
    │   └── 財報 PDF（全新 2455、聯亞光 3081、華星光 4979、產業深度報告）
    └── PCB/
        └── 財報 PDF（欣興 3037、南電 8046、景碩 3189）
```

---

## 核心追蹤標的

### 第一圈：DRAM / 記憶體

| 代碼 | 公司 | 主題 |
|------|------|------|
| 2408 | 南亞科技 | DDR5 轉型 / 超級循環，EPS 槓桿 8-18x |
| 2344 | 華邦電子 | Specialty DRAM + NOR Flash |

### 第二圈：光通訊 CPO

| 代碼 | 公司 | 層級 |
|------|------|------|
| 3363 | 上詮光纖 | L1 CPO — TSMC COUPE 唯一認證 FAU |
| 2455 | 全新光電 | L1 磊晶 — InP+GaAs 雙平台 |
| 3081 | 聯亞光電 | L1 磊晶 — CW Laser InP，YoY +91.4% |
| 4979 | 華星光通 | L2 封裝 — Marvell 客戶 85-95% |
| 3105 | 穩懋半導體 | L2 晶圓代工 — GaAs，CPO 佔比 15-20% |

### 第三圈：IC 載板

| 代碼 | 公司 | 主題 |
|------|------|------|
| 3037 | 欣興電子 | ABF 載板，AI 營收 30-40%，2025 EPS NT$4.38 |
| 8046 | 南亞電路板（南電） | ABF 載板 #2，產能>90%，2025 EPS NT$3.0 |
| 3189 | 景碩科技 | CoWoS 基板，2026E EPS NT$6.3-8.0（+80-130%） |

### 擴充觀察（CPO 生態周邊）

| 代碼 | 公司 | 定位 |
|------|------|------|
| 6442 | 光聖 | L3 高芯數光纖連接器 |
| 2345 | 智邦 | L4 CPO 交換器系統 |
| 6223 | 旺矽 | 測試層 Probe Card |
| 4977 | 眾達-KY | L3 光模組組裝 |
| 3163 | 波若威 | L3 特種光纖元件 |

---

## 研究架構索引（research/ 資料夾）

| 檔案 | 類型 | 說明 |
|------|------|------|
| 記憶體超級循環供應鏈全景圖.jsx | JSX | DRAM 完整供應鏈互動圖譜 |
| 台灣記憶體三情境估值儀表板.jsx | JSX | DRAM Bear/Base/Bull 三情境估值 |
| 記憶體產業重點公司基本資料卡.md | MD | 南亞科/華邦電/力成財務快照 |
| 光通訊CPO供應鏈全景圖.jsx | JSX | CPO 6層架構互動圖譜（含 NVIDIA $40億投資）|
| 光通訊CPO產業重點公司基本資料卡.md | MD | 8檔台股 + LITE/COHR 參照 |
| PCB載板供應鏈全景圖.jsx | JSX | ABF 5層架構互動圖譜（含 T-Glass 瓶頸）|
| PCB載板產業重點公司基本資料卡.md | MD | 欣興/南電/景碩財務快照 + 三情境估值 |

---

## 與 claude.ai Project 的差異

| 功能 | claude.ai Project | Claude Code（此專案）|
|------|------------------|---------------------|
| 財報 PDF 分析 | ✅ Project Files | ✅ 本地讀取 |
| 月營收抓取 | 手動觸發 | ✅ 自動化腳本 |
| 歷史數據持久化 | ❌ | ✅ SQLite |
| 技術指標計算 | ❌ | ✅ RSI/MACD/MA |
| 每日自動日報 | ❌ | ✅ run_report.py |
| 無工程設定 | ✅ | 需初始化一次 |

---

## 注意事項

- 所有分析僅供個人研究參考，非正式投資建議
- 月營收數據優先從 winvest.tw / histock.tw 抓取
- 上市（.TW）與上櫃（.TWO）在 yfinance 使用不同後綴；6442/4977 為 .TW
- 每季財報後需更新 CLAUDE.md 中的財務基準數據，以及 research/ 各基本資料卡
