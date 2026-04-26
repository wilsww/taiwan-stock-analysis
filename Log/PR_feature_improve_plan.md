# 📘 PR 摘要：Phase D 重構完成、文件移檔與 optional cleanup

## 🎯 目的

在不改變 dashboard 功能、視覺結果與資料語意的前提下，完成 `sector_flow_dashboard` 的 Phase D 架構重構，並同步整理改善計畫文件與低風險 API cleanup。

## ✅ 本次變更

### 1. Phase D 架構重構完成

- 將 sidebar 包裝為 `render_sidebar()`，以 `SidebarParams` 集中控制參數
- 將資料載入流程整理為 `AppData` 與 `load_app_data()`
- 將主流程收斂為 `main()` orchestration
- 新增 `scripts/dashboard/data.py`
- 新增 `scripts/dashboard/tabs.py`
- 將 alerts / scrubber / Tab1-Tab8 / detail rendering 自主檔抽離
- 主檔 `scripts/sector_flow_dashboard.py` 收斂至 466 行

### 2. 共用模組整理延續完成

- 共用 helper 保留於 `scripts/dashboard/helpers.py`
- panel rendering / panel data builder 保留於 `scripts/dashboard/panels.py`
- `_unit_scale()` / `_key_for_unit()` 已成為跨 data / tabs 共用 helper

### 3. 🧪 驗證與人工確認

- `python3 -m py_compile` 通過
- bare import 通過
- `scripts/dashboard/*` 已無 `st.session_state` 依賴
- 已完成 `streamlit run` 人工確認
- 已確認：
  - Tab1-Tab8 顯示
  - hover panel
  - 快速區間 / 更新資料按鈕 rerun
  - Tab6-Tab8 條件顯示
  - scrubber 單期 snapshot
  - 個股明細 expander

### 4. 🧹 Optional cleanup

- `use_container_width=True` 改為 `width="stretch"`
- `Styler.applymap(...)` 改為 `Styler.map(...)`
- 已清除上述兩類 deprecation

### 5. 🗂️ 文件整理

- `Improve_Plan.md` 移動並更名為：
  - `Log/sector_flow_dashboard__Improve_Plan_20260417.md`
- 文件內容已補齊：
  - Phase D 實作紀錄
  - 人工確認結果
  - optional cleanup 紀錄
  - 延伸評估說明

### 6. 🛠️ Agent 文件全面優化（task_plan 階段 1–8）

對齊現代化 Claude Code 規範，消冗餘、補 metadata、統一相對路徑。

- **CLAUDE.md 三層分工**
  - 全域 `~/.claude/CLAUDE.md`（v1.3）：本次不動，避免越界
  - 專案 `taiwan-stock-analysis/CLAUDE.md`：移除路由表（改引用全域）、改用編號小節 1–12、補 `docs/AGENT_DOCS.md` 入口、加 `streamlit run`、版本升 4.4
  - 子目錄 `research/CLAUDE.md`：純索引化，合併快照同步規則段
- **Slash Commands 現代化**
  - 10 個 commands 全部加 frontmatter（description / argument-hint / allowed-tools / model）
  - 模型分派：dashboard + markitdown 用 haiku（純執行），其餘 8 個用 sonnet
  - 刪除 `prompts/earnings_analysis.md` 與空目錄（與 `/deep-analysis` 重複）；README 同步移除引用
- **Memory 體系重寫**
  - 4 個 reference memory 改相對路徑、移除「原 XXX」過時命名、補 **Why** 段
  - `MEMORY.md` 補 Project / User 區塊佔位（規範四類齊全）
- **Hooks 與 Settings 整理**
  - `haiku_prompt_guard.py` + `finance_sync_reminder.py` docstring 補強
  - **修 bug**：`finance_sync_reminder.py` SNAPS 路徑由 `research/財務快照_*.md` 改 `themes/{DRAM,CPO,PCB}/snapshots/財務快照_*.md`
  - `settings.json` 移除與 .local 重複的寬域 Bash、無條件 Edit/Write；WebFetch 改 domain-list 並補 mopsov / irengage / nanyapcb 三個實際使用 domain
  - `settings.local.json` 屬個人 permissions，不動
- **Docs 歸檔與索引**
  - `docs/文件結構改善計畫.md` 移至 `docs/archive/`（v1.0 已執行完）
  - 新建 `docs/AGENT_DOCS.md`（7 區段：Instructions / Memory / Commands / Hooks / Settings / Docs / 維護原則）

驗證：JSON × 4 / Python × 24 全 parse 通過；hook smoke-test 5+3 情境符合規格；`archive_reports.py --dry-run` 正常。

> 注意：CLAUDE.md / .claude/ 受 .gitignore 排除（本機 only 模式），上述改動於本機 working tree 生效，commit 範圍僅包含可入 git 部分。

### 7. 🐛 Pending_Issue.md 三項真實 bug 修正（task_plan 階段 9）

來源：code review against merge base `bb777a50`。三項驗證後確認真實，已修。

| # | 位置 | 問題 | 修法 | 影響 |
|---|------|------|------|------|
| 1 | `scripts/dashboard/detail_view.py:1423` | 月營收單位 `/100` 應為 `/1000` | 改 `revenue_m / 1000.0` | 個股詳查月營收顯示與 Markdown 快照從 10× 放大恢復正確億元 |
| 2 | `scripts/fetch_intraday.py:87` | yfinance Volume（股）未轉張，與 daily 不一致 | 落地時 `df["volume"] = df["volume"] / 1000.0`；DB `intraday_price` 既有 531 筆 in-place `UPDATE volume = volume / 1000.0` | intraday 5m / resample 成交量從 1000× 放大恢復張級別 |
| 3 | `README.md:14` | Quick Start 缺 PCB 3 檔 + CPO 周邊 5 檔 | 改三段式 DRAM(2)/CPO(10)/PCB(3) 共 15 檔，對齊 `CLAUDE.md` §11 | 新使用者初始化資料完整覆蓋三大主題 |

驗證：
- 2408 2026-03 `revenue_m=181700.0` → 顯示 `181.7 億`（與 Pending_Issue 預期一致）
- 6488 intraday 5m 加總 vs daily volume 4 個交易日比例 84–93%（yfinance vs TWSE 撮合微差，合理）
- python ast.parse OK（detail_view.py + fetch_intraday.py）

DB 採 in-place UPDATE 而非 DELETE 重抓（可逆、無資料遺失、避免 yfinance 5m 60d 視窗限制）；備份 `data/revenue/revenue.db.bak_pre_intraday_unit_fix`。

## 📦 主要 commit

- `8153656` refactor(sector_flow_dashboard): extract dashboard modules and main data flow
- `fdbdef5` refactor(sector_flow_dashboard): extract dashboard tabs and data modules
- `0b4f4bc` docs(log): move improve plan and record phase d cleanup
- `ac09751` feat(dashboard): add stock detail tab and ohlcv support
- `0714e60` docs(agent): modernize agent docs and consolidate indexes
- `6abb777` docs(readme): refresh structure to match current layout
- `59e62ca` docs(skills-guide): fix stale Type/DRAM paths post-restructure
- `23ca982` chore(agent): share project rules between Claude Code and Codex CLI
- _(pending)_ fix: correct revenue_m unit conversion in detail view
- _(pending)_ fix: align intraday volume units and complete README ticker list

## ⚠️ 已知事項

- bare import 仍會看到 Streamlit bare mode 警告
- 另有一則 Plotly `config` 相關 warning 尚未處理：
  - `The keyword arguments have been deprecated and will be removed in a future release. Use config instead to specify Plotly configuration options.`
- 這屬於後續低風險 cleanup 議題，不影響本次重構完成度

## 🔍 Review 重點

- Phase D 拆模組後，dashboard 行為是否仍與 baseline 一致
- `main()` 是否已只保留 orchestration 責任
- `data.py` / `tabs.py` / `helpers.py` / `panels.py` 的責任邊界是否清楚
- optional cleanup 是否未改變既有 UI 語意
- Agent 文件三層分工是否清楚（全域 / 專案 / 子目錄）
- Pending_Issue 三項修正是否單位邏輯正確（`revenue_m` 百萬 ↔ 億 / yfinance 股 ↔ 張）
- intraday_price in-place UPDATE 後與 daily volume 比例是否在合理區間
