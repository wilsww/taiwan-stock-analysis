# Agent 文件總索引

> 本專案所有 agent 相關文件的單一入口。任何 agent 行為調整均應從此處定位來源檔。
> 維護原則：**全域 = 通用行為，專案 = 投資 specifics，子目錄 = 索引**。

---

## 1. Instructions（CLAUDE.md 三層）

| 層級 | 路徑 | 職責 |
|------|------|------|
| 全域 | `~/.claude/CLAUDE.md` | Subagent 路由（haiku/sonnet/opus）、`[Model - effort]` 標籤、結構化 JSON 回傳、並行工具呼叫 |
| 專案 | `CLAUDE.md` | 投資 specifics：主題、工具紀律、按需讀取、資料來源、輸出規範、目錄結構 |
| 子目錄 | `research/CLAUDE.md` | research/ 索引（主檔/組合/主題速查） |

---

## 2. Memory（auto-memory）

位置：`~/.claude/projects/-Users-wayne-Desktop-Invest-taiwan-stock-analysis/memory/`

| 檔 | 類型 | 摘要 |
|----|------|------|
| `MEMORY.md` | index | 索引（4 類：feedback / reference / project / user） |
| `feedback_codex_dispatch.md` | feedback | `/codex` 委派模型路由 |
| `feedback_file_operations.md` | feedback | 檔案操作安全邊界 |
| `reference_dram_folder.md` | reference | DRAM 主題檔位置 |
| `reference_cpo_folder.md` | reference | CPO 主題檔位置 |
| `reference_pcb_folder.md` | reference | PCB 主題檔位置 |
| `reference_us_stocks.md` | reference | 美股財務檔（MU/SNDK） |
| `reference_sector_flow_dashboard.md` | reference | 主力資金儀表板別名 |

---

## 3. Slash Commands（`.claude/commands/`，10 個）

| 指令 | description | model |
|------|-------------|-------|
| `/catalyst-check` | 90 天催化劑日曆 + 高密度週標記 | sonnet |
| `/dashboard` | 啟動主力資金 Streamlit 儀表板 | haiku |
| `/deep-analysis [ticker]` | 5 步驟分析 + 三情境估值 | sonnet |
| `/earnings-checklist <ticker> [quarterly\|ir]` | 季報/法說後 P0/P1/P2 更新清單 | sonnet |
| `/macro-pulse` | 美股訊號 → 台股對照 + DRAM 現貨價 | sonnet |
| `/markitdown <file\|URL>` | MarkItDown MCP 轉 Markdown | haiku |
| `/position-sizing <ticker> [capital]` | Half-Kelly 倉位 + 三批進場 | sonnet |
| `/revenue-update [tickers]` | 月營收抓取 + DB + 簡報 | sonnet |
| `/risk-check` | 五大風險評估 | sonnet |
| `/weekly-review` | 週度回顧寫入 reports/ | sonnet |

每個 command 含 frontmatter：`description` / `argument-hint` / `allowed-tools` / `model`。

---

## 4. Hooks（`.claude/hooks/`）

| 檔 | 觸發 | 行為 |
|----|------|------|
| `haiku_prompt_guard.py` | PreToolUse(Agent) | haiku subagent prompt 自動補結尾 phrase |
| `finance_sync_reminder.py` | PostToolUse(Edit/Write/MultiEdit) | `research/財務數據基準.md` 編輯後檢查 `themes/*/snapshots/` 過舊 |

CLAUDE.md §2 / §9.2 為對應規範來源。

---

## 5. Settings

| 檔 | 範圍 | 內容 |
|----|------|------|
| `.claude/settings.json` | 專案共享 | hooks（3 個）+ WebFetch domain whitelist |
| `.claude/settings.local.json` | 本機個人 | 個人 permissions、defaultMode、enabledMcpjsonServers |

Stop hook：`scripts/archive_reports.py` 自動歸檔 reports/ 過期檔。

---

## 6. Docs

| 檔 | 用途 |
|----|------|
| `docs/AGENT_DOCS.md`（本檔） | Agent 文件總索引 |
| `docs/DB_FETCH_GUIDE.md` | `data/revenue/revenue.db` 操作規範（CLAUDE.md 強制必讀） |
| `docs/Claude_Financial_Skills_Guide.md` | Claude 金融 skills 用法 |
| `docs/archive/` | 過時文件（如 `文件結構改善計畫.md` v1.0） |

---

## 7. 維護原則

1. **加新 command** → 必含 frontmatter（description / argument-hint / allowed-tools / model），完成後在第 3 節登記
2. **加新 hook** → 在 `settings.json` 設 matcher、寫 docstring 含 trigger/behavior/CLAUDE.md 章節引用，完成後在第 4 節登記
3. **memory 寫入** → 用相對路徑（除非跨專案），feedback/project 含 **Why** + **How to apply** 段
4. **CLAUDE.md 改動** → 只動本層職責內容，不重複其他層；版本號 + 日期更新
5. **歸檔過時 docs** → 移至 `docs/archive/`，不刪除（保留歷史脈絡）

---

版本：1.0 | 最後更新：2026-04-26
