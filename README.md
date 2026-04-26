# 台灣科技股投資研究 — Claude Code 專案

個人研究工具，聚焦台灣半導體、光通訊、IC 載板。投資時間軸 2025–2027。**非投資建議**。

> Agent 文件總索引 → [`docs/AGENT_DOCS.md`](docs/AGENT_DOCS.md)
> Claude 行為規則 → `CLAUDE.md`（本機 only，未入 git）

---

## 快速開始

```bash
# 1. 抓取月營收（DRAM + CPO + PCB）
python3 scripts/fetch_revenue.py --ticker 2408 2344 3363 2455 4979 3081 3105 4919

# 2. 產出日報
python3 scripts/run_report.py

# 3. 產出月報
python3 scripts/monthly_report.py --month 2026-03

# 4. 啟動主力資金儀表板
streamlit run scripts/sector_flow_dashboard.py
```

---

## 目錄結構

```
taiwan-stock-analysis/
├── CLAUDE.md                       本機 Claude 規則（gitignored）
├── README.md
├── .claude/                        本機 agent 設定（gitignored）
│   ├── commands/                   10 個 slash command（/dashboard, /deep-analysis, ...）
│   ├── hooks/                      PreToolUse + PostToolUse + Stop hooks
│   ├── settings.json               專案共享：hooks + WebFetch domain whitelist
│   └── settings.local.json         本機 permissions
│
├── themes/                         主題資料夾（PDF + 分析 + 快照）
│   ├── DRAM/{filings,analysis,snapshots,us_peers}/
│   ├── CPO/{filings,analysis,snapshots}/
│   └── PCB/{filings,analysis,snapshots}/
│
├── research/                       跨主題層級
│   ├── CLAUDE.md                   research/ 索引
│   ├── 財務數據基準.md              主檔（所有標的最新季）
│   ├── 追蹤標的清單.md              代碼 / 定位 / 催化劑
│   ├── 投資組合.md                  持倉 + 配置
│   ├── 出場訊號清單.md
│   ├── 法說會重點紀錄.md
│   ├── stock_universe.json         類股分類（sector_flow 使用）
│   ├── sector_flow_plan.md
│   ├── dashboard_presets.json
│   └── archive/                    歷史財務數字歸檔
│
├── reports/                        依輸出類型分層
│   ├── daily/                      YYYY-MM-DD_日報.md（保留 7 天）
│   ├── monthly/                    monthly_report_YYYYMM.md（保留 3 個月）
│   ├── deep_analysis/              deep_analysis_{ticker}_{date}.md
│   ├── valuation/
│   ├── risk/
│   ├── sector_flow/
│   └── archive/
│
├── data/
│   ├── revenue/                    revenue.db + csv/xlsx/json
│   ├── institutional/YYYY-MM/      三大法人買賣超
│   ├── margin/YYYY-MM/             融資融券
│   └── archive/
│
├── docs/
│   ├── AGENT_DOCS.md               Agent 文件總索引
│   ├── DB_FETCH_GUIDE.md           revenue.db 操作規範
│   ├── Claude_Financial_Skills_Guide.md
│   └── archive/                    過時文件
│
└── scripts/                        自動化腳本（見下節）
```

---

## 核心追蹤標的

### DRAM / HBM 超級循環

| 代碼 | 公司 | 主題 |
|------|------|------|
| 2408 | 南亞科技 | DDR5 轉型，EPS 槓桿 8–18× |
| 2344 | 華邦電子 | Specialty DRAM + NOR Flash（新唐稀釋 ~9pp 須段落拆分） |
| 4919 | 新唐科技 | 嵌入式控制器（華邦電子公司） |

### 光通訊 CPO

| 代碼 | 公司 | 層級 |
|------|------|------|
| 3363 | 上詮光纖 | L1 — TSMC COUPE 唯一認證 FAU |
| 2455 | 全新光電 | L1 磊晶 — InP+GaAs 雙平台 |
| 3081 | 聯亞光電 | L1 磊晶 — CW Laser InP |
| 4979 | 華星光通 | L2 封裝 — Marvell 佔比 85–95% |
| 3105 | 穩懋半導體 | L2 GaAs 晶圓代工（二階受益者） |

CPO 生態周邊（觀察）：6442 光聖、2345 智邦、6223 旺矽、4977 眾達-KY、3163 波若威。

### IC 載板（ABF / BT）

| 代碼 | 公司 | 主題 |
|------|------|------|
| 3037 | 欣興電子 | ABF 全球龍頭，~35% 市佔 |
| 8046 | 南電 | ABF #2，台塑集團，產能 >90% |
| 3189 | 景碩科技 | ABF+BT+CoWoS，2026E EPS YoY +80–130% |

完整清單與催化劑時間軸：[`research/追蹤標的清單.md`](research/追蹤標的清單.md)。

---

## 主要 Scripts

| 類別 | 腳本 | 用途 |
|------|------|------|
| 月營收 | `fetch_revenue.py` | 從 winvest.tw 抓取，寫入 `data/revenue/revenue.db` |
| 月營收 | `export_revenue.py` | DB → CSV / Excel |
| 月營收 | `revenue_live.py` | 即時查詢 |
| 報告 | `run_report.py` | 日報主入口（股價+營收+技術指標） |
| 報告 | `run_report_b.py` | 日報 Plan B（平行版） |
| 報告 | `monthly_report.py` | 月報 |
| 報告 | `build_earnings_reports.py` | 財報分析 |
| 資金流 | `sector_flow.py` | TWSE T86 三大法人買賣超抓取 |
| 資金流 | `sector_flow_dashboard.py` | Streamlit 儀表板 |
| 資金流 | `fetch_institutional.py` / `fetch_margin.py` | 法人 / 融資融券補抓 |
| 行情 | `fetch_prices.py` / `fetch_quote.py` / `fetch_intraday.py` / `fetch_ohlcv.py` | yfinance / TWSE 行情抓取 |
| 行情 | `indicators.py` | RSI / MACD / MA 計算 |
| 比較 | `peer_compare.py` / `build_comps.py` | 同業比較 |
| 工具 | `extract_pdf_summary.py` | PDF 摘要提取 |
| 工具 | `fetch_news.py` | 新聞抓取 |
| 工具 | `render_html.py` | 靜態 HTML 儀表板 |
| 維運 | `archive_reports.py` | reports/ 歸檔（Stop hook 自動觸發） |

---

## Slash Commands（10 個）

| 指令 | 用途 |
|------|------|
| `/deep-analysis [ticker]` | 5 步驟深度分析 + 三情境估值 |
| `/risk-check` | 五大風險評估 |
| `/revenue-update [tickers]` | 月營收抓取 + DB + 簡報 |
| `/earnings-checklist <ticker> [quarterly\|ir]` | 財報 / 法說後 P0/P1/P2 清單 |
| `/weekly-review` | 週度回顧 |
| `/catalyst-check` | 90 天催化劑日曆 |
| `/macro-pulse` | 美股訊號 → 台股對照 |
| `/position-sizing <ticker> [capital]` | Half-Kelly 倉位 + 三批進場 |
| `/dashboard` | 啟動主力資金 Streamlit |
| `/markitdown <file\|URL>` | MarkItDown MCP 轉 Markdown |

詳見 [`docs/AGENT_DOCS.md`](docs/AGENT_DOCS.md)。

---

## 注意事項

- 所有分析僅供個人研究，**非投資建議**
- 月營收優先從 winvest.tw / histock.tw 抓取；備援 mops.twse.com.tw
- 上市（`.TW`）與上櫃（`.TWO`）在 yfinance 後綴不同
- 季報後須更新 `research/財務數據基準.md` 並同步三個 `themes/{DRAM,CPO,PCB}/snapshots/財務快照_*.md`（hook `finance_sync_reminder` 自動提醒）
- `reports/` 歸檔由 `scripts/archive_reports.py` 在 Stop hook 自動執行
