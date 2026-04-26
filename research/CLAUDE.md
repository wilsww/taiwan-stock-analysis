# research/ 索引

> 跨主題 / 全組合層級檔案。主題專屬檔（基本資料卡、供應鏈圖、財務快照、PDF）已收斂至 `themes/{DRAM,CPO,PCB}/`。
> 通用規則 → `../CLAUDE.md`、全域行為 → `~/.claude/CLAUDE.md`。

---

## 主檔（最高優先）

| 檔 | 用途 |
|----|------|
| `財務數據基準.md` | 所有追蹤標的最新季財務數字。**任何分析前先讀此檔**（或對應主題快照） |
| `archive/` | 超過 2 季的歷史財務數字歸檔 |

> **快照同步規則**：以主檔為準，更新主檔後須同步三個快照（`themes/{DRAM,CPO,PCB}/snapshots/財務快照_*.md`），hook 自動提醒。

---

## 追蹤標的與組合

| 檔 | 用途 |
|----|------|
| `追蹤標的清單.md` | 完整追蹤標的（代碼、定位、催化劑時間軸） |
| `投資組合.md` | 目前持倉與配置 |
| `出場訊號清單.md` | 各標的出場訊號彙整 |
| `法說會重點紀錄.md` | 跨主題法說會紀錄 |
| `stock_universe.json` | 類股分類 JSON（`sector_flow_dashboard.py` 使用） |
| `sector_flow_plan.md` | 資金流分析規劃 |
| `dashboard_presets.json` | 儀表板預設 |

---

## 主題檔速查

| 主題 | PDF 原檔 | 分析（JSX/MD） | 快照 |
|------|---------|---------------|------|
| DRAM | `themes/DRAM/filings/` | `themes/DRAM/analysis/` | `themes/DRAM/snapshots/` |
| CPO | `themes/CPO/filings/` | `themes/CPO/analysis/` | `themes/CPO/snapshots/` |
| PCB | `themes/PCB/filings/` | `themes/PCB/analysis/` | `themes/PCB/snapshots/` |

- DRAM analysis：`DRAM_供應鏈全景圖.jsx`、`DRAM_基本資料卡.md`、`DRAM_三情境估值.jsx`
- CPO analysis：`光通訊CPO供應鏈全景圖.jsx`、`CPO_基本資料卡.md`
- PCB analysis：`PCB載板供應鏈全景圖.jsx`、`PCB_基本資料卡.md`、`PCB載板_研究索引.md`

美股參照：`themes/DRAM/us_peers/{MU_Micron_financials.md, SNDK_SanDisk_financials.md}`

---

## 其他

- `MS_微軟深度分析.txt`：微軟深度分析文章（非台股主題，待整理）
