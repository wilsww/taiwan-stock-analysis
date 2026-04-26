# 發現與決策

## 需求
- 盤點 + 優化整個專案的 agent 文件體系
- 對齊現代化 Claude Code 規範（frontmatter、相對路徑、職責分層）
- 不破壞現有 commands/hooks/scripts 行為

## 盤點清單

### A. Instructions（CLAUDE.md 體系）
| 路徑 | 行 | 角色 | 問題 |
|------|---|------|------|
| `~/.claude/CLAUDE.md` | 77 | 全域 agent 行為 | 與專案 CLAUDE.md 路由表重複 |
| `taiwan-stock-analysis/CLAUDE.md` | 185 | 專案主指令 | 路由表與全域重複；無 version frontmatter |
| `research/CLAUDE.md` | 43 | 子目錄索引 | 與主 CLAUDE.md「按需讀取」段落部分重複 |

### B. Memory（auto-memory，8 檔）
位置：`~/.claude/projects/-Users-wayne-Desktop-Invest-taiwan-stock-analysis/memory/`

| 檔 | 類型 | 問題 |
|-----|------|------|
| `MEMORY.md` | index | 缺 user 區塊（CLAUDE.md 規範要求 4 類） |
| `feedback_codex_dispatch.md` | feedback | 已含 Why/How，OK |
| `feedback_file_operations.md` | feedback | 已含 Why/How，OK |
| `reference_dram_folder.md` | reference | 含絕對路徑 `/Users/wayne/Desktop/Invest/...` |
| `reference_cpo_folder.md` | reference | 含絕對路徑 |
| `reference_pcb_folder.md` | reference | 含絕對路徑 |
| `reference_us_stocks.md` | reference | 含絕對路徑 |
| `reference_sector_flow_dashboard.md` | reference | 已用相對路徑，OK |

### C. Slash Commands（10 個，全部缺 frontmatter）
| 檔 | 行 | 缺項 |
|-----|---|------|
| catalyst-check.md | 109 | description / argument-hint / allowed-tools / model |
| dashboard.md | 100 | 同上 |
| deep-analysis.md | 122 | 同上 |
| earnings-checklist.md | 188 | 同上 |
| macro-pulse.md | 98 | 同上 |
| markitdown.md | 60 | 同上 |
| position-sizing.md | 113 | 同上 |
| revenue-update.md | 118 | 同上 |
| risk-check.md | 63 | 同上 |
| weekly-review.md | 117 | 同上 |

### D. Hooks（2 個 Python）
- `haiku_prompt_guard.py` — PreToolUse(Agent) 自動補 haiku prompt 結尾
- `finance_sync_reminder.py` — PostToolUse(Edit/Write) 財務快照過舊提醒

### E. Settings（2 檔）
- `.claude/settings.json` — permissions allow + 3 hooks
- `.claude/settings.local.json` — 本機 permissions + MCP servers

### F. Prompts（孤兒）
- `prompts/earnings_analysis.md` — 與 `/deep-analysis`、`/earnings-checklist` 框架高度重疊

### G. Docs（agent 相關 3 檔）
- `docs/Claude_Financial_Skills_Guide.md`（615 行）— 金融 skills 指南
- `docs/DB_FETCH_GUIDE.md`（228 行）— revenue.db 規範（CLAUDE.md 強制必讀）
- `docs/文件結構改善計畫.md`（184 行）— v1.0 結構計畫，已完成 A/B/C 階段，**過時**

## 技術決策

| 決策 | 理由 |
|------|------|
| 三層 CLAUDE.md 分工：全域=通用行為、專案=投資 specifics、子目錄=索引 | 消除路由表雙寫，責任邊界清晰 |
| Slash command frontmatter 標準：`description` / `argument-hint` / `allowed-tools` / `model` | 對齊 Claude Code 現代 metadata 規範 |
| Memory reference 全改相對路徑（相對於專案根） | 跨機器可移植 |
| `prompts/earnings_analysis.md` 合併進 `/deep-analysis` STEP 1-5 → 刪除 `prompts/` 目錄 | 框架重疊；目錄孤兒 |
| `docs/文件結構改善計畫.md` 移至 `docs/archive/` | 已執行完畢，保留作歷史紀錄 |
| 全域 `~/.claude/CLAUDE.md` 本次只補 version 標記，不改邏輯 | 影響所有專案，避免越界 |
| 不動 `settings.local.json` 個人 permissions | 屬本機個人設定 |

## Frontmatter 範本（slash command）

```yaml
---
description: 一句話用途（≤60 字）
argument-hint: "[ticker]"  # 或 "[YYYY-MM]" 等
allowed-tools: Read, Bash, WebFetch, Agent
model: sonnet  # 或 haiku
---
```

## 路徑改寫規則（memory reference）

從：`/Users/wayne/Desktop/Invest/taiwan-stock-analysis/themes/DRAM/filings/`
改：`themes/DRAM/filings/`（相對於 `$CLAUDE_PROJECT_DIR`）

例外：跨專案才需絕對路徑（如 `~/.claude/...`）。

## 遇到的問題
| 問題 | 解決方案 |
|------|---------|
|      |         |

## 資源
- Anthropic 官方 slash command 文件：frontmatter 規範
- Claude Code sub-agents 文件：`.claude/agents/` 機制（本專案未用）
- 全域 CLAUDE.md：subagent 路由 + 並行規則

## 視覺/瀏覽器發現
- 無

---
