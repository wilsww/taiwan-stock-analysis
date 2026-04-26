# 任務計畫：Agent 文件全面優化

## 目標
盤點並優化整個專案的 agent 文件體系（CLAUDE.md / memory / commands / hooks / settings / prompts / docs），統一以現代化 Claude Code 規範重寫，消除冗餘、補齊 frontmatter、修正硬碼路徑，並重新分類管理。

## 範圍
**14 份指令/設定 + 8 份 memory + 10 份 slash commands + 2 個 hooks + 2 份 settings + 1 份 prompts + 3 份 docs = 共 ~36 份檔案**

詳見 findings.md「盤點清單」段。

## 目前階段
階段 8

## 各階段

### 階段 1：盤點與問題識別
- [x] 列出所有 agent 文件（位置、行數、用途）
- [x] 識別重複、孤兒、硬碼、缺 frontmatter 等問題
- [x] 取得使用者同意進入優化階段
- **狀態：** complete

### 階段 2：優化原則與分層設計
- [x] 確定現代化 frontmatter 規範（slash command + sub-agent）
- [x] 確定全域 vs 專案 CLAUDE.md 的職責切分原則
- [x] 確定 memory 的硬碼路徑改寫規則
- [x] 確定孤兒檔處理（保留/合併/歸檔/刪除）
- [x] 將決策寫入 findings.md
- **狀態：** complete

### 階段 3：CLAUDE.md 三層重構
- [x] 全域 `~/.claude/CLAUDE.md`：已是 version 1.3，本次不動（避免越界）
- [x] 專案 `taiwan-stock-analysis/CLAUDE.md`：移除路由表（改引用全域）、改用編號小節、補 `docs/AGENT_DOCS.md` 入口、加 `streamlit run` 指令、版本升 4.4
- [x] 子目錄 `research/CLAUDE.md`：純索引化，去除快照三項列表細節（合併進同步規則段）
- **狀態：** complete

### 階段 4：Slash Commands 現代化
- [x] 全 10 個 commands 加 frontmatter（description / argument-hint / allowed-tools / model）
- [x] STEP 0 載入邏輯保留各 command 內（重複度可接受，抽出反而增加跳轉成本）
- [x] `prompts/earnings_analysis.md` 與 `/deep-analysis` 重複度高 → 直接刪 prompts/ 目錄；README.md 同步移除引用
- **狀態：** complete

### 階段 5：Memory 體系重寫
- [x] 4 個 reference 改相對路徑，去歷史「原 XXX」命名痕跡，補 **Why** 段
- [x] feedback 兩檔已含 Why/How，不動
- [x] MEMORY.md 補 Project / User 區塊佔位（規範四類齊全）
- [x] 確認 reference_sector_flow_dashboard 已是相對路徑，不動
- **狀態：** complete

### 階段 6：Hooks 與 Settings 整理
- [x] hooks 兩個 .py docstring 補強（trigger / behavior / 引用 CLAUDE.md 章節）
- [x] **修 bug**：`finance_sync_reminder.py` SNAPS 路徑由 `research/財務快照_*.md` 改 `themes/{DRAM,CPO,PCB}/snapshots/財務快照_*.md`（與 CLAUDE.md §9.2 一致）
- [x] `settings.json` 移除與 .local 完全重複的 Bash 寬域許可、移除無條件 `Edit`/`Write`、WebFetch 改 domain-list（含補 3 個實際使用 domain）
- [x] `settings.local.json` 屬個人 permissions，不動
- **狀態：** complete

### 階段 7：Docs 歸檔與索引
- [x] `docs/文件結構改善計畫.md` 移至 `docs/archive/`，無外部斷鏈
- [x] CLAUDE.md §5 已含 DB_FETCH_GUIDE、Claude_Financial_Skills_Guide、AGENT_DOCS 入口
- [x] 新建 `docs/AGENT_DOCS.md`（7 區段：Instructions/Memory/Commands/Hooks/Settings/Docs/維護原則）
- **狀態：** complete

### 階段 8：驗證與交付
- [ ] grep 全專案，確認所有路徑引用正確（無斷鏈）
- [ ] 跑 `python3 scripts/run_report.py` 與 `streamlit run scripts/sector_flow_dashboard.py` 確認 hooks/commands 無破壞
- [ ] 將總改動清單寫入 progress.md
- [ ] 提交 git commit（feature-improve-plan 分支內）
- **狀態：** pending

## 關鍵問題
1. 是否將 `prompts/earnings_analysis.md` 內容合併進 `/deep-analysis` 後刪除 prompts/ 目錄？（傾向：是，孤兒目錄收掉）
2. 全域 `~/.claude/CLAUDE.md` 是否在本次範圍？（用戶說「整個專案」，傾向：是，但只調 frontmatter/version，不改邏輯）
3. settings.local.json 的個人 permissions 是否要動？（傾向：不動，僅整理 settings.json）

## 已做決策
| 決策 | 理由 |
|------|------|
| 採「全域=通用行為、專案=投資 specifics、子目錄=索引」三層分工 | 消除目前路由表雙寫的重複 |
| Memory reference 全改相對路徑 | 易於跨機器遷移、避免絕對路徑漂移 |
| Slash command 一律補 frontmatter | 對齊 Claude Code 現代規範（description/argument-hint/allowed-tools/model） |
| 範圍排除 `~/.claude/CLAUDE.md` 的內容變更 | 全域檔影響所有專案，本次僅聚焦本專案；只在補 version 等 metadata |

## 遇到的錯誤
| 錯誤 | 嘗試次數 | 解決方案 |
|------|---------|---------|
|      | 1       |         |

## 備註
- 每個階段完成立即更新狀態
- CLAUDE.md / settings.json 改動屬高風險（影響後續 session），動前先 diff 確認
- 不刪檔前先確認 grep 無外部引用
