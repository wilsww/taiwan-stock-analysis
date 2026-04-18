# research/ 目錄索引

跨主題 / 全組合層級檔案。主題檔（基本資料卡、供應鏈圖、財務快照、PDF）已移至 `themes/{DRAM,CPO,PCB}/`。

## 財務數據（優先參照）

| 檔案 | 用途 |
|------|------|
| `財務數據基準.md` | **主檔**：所有追蹤標的最新季財務數字，分析前先讀此檔 |
| `archive/` | 超過 2 季的歷史財務數字歸檔處 |

> 主題快照檔位置：
> - `themes/DRAM/snapshots/財務快照_DRAM.md`
> - `themes/CPO/snapshots/財務快照_CPO.md`
> - `themes/PCB/snapshots/財務快照_PCB.md`
>
> 快照以主檔為準；更新主檔後須同步三個快照。

## 追蹤標的與組合

| 檔案 | 用途 |
|------|------|
| `追蹤標的清單.md` | 完整追蹤標的（代碼、定位、催化劑時間軸） |
| `投資組合.md` | 目前持倉與配置 |
| `出場訊號清單.md` | 各標的出場訊號彙整 |
| `法說會重點紀錄.md` | 跨主題法說會重點紀錄 |
| `stock_universe.json` | 類股分類 JSON（sector_flow 使用） |
| `sector_flow_plan.md` | 資金流分析規劃 |
| `dashboard_presets.json` | 儀表板預設 |

## 主題檔速查

| 主題 | PDF 原檔 | 分析（JSX/MD） | 快照 |
|------|---------|---------------|------|
| DRAM | `themes/DRAM/filings/` | `themes/DRAM/analysis/`（供應鏈全景圖、基本資料卡、三情境估值） | `themes/DRAM/snapshots/` |
| CPO | `themes/CPO/filings/` | `themes/CPO/analysis/`（供應鏈全景圖、基本資料卡） | `themes/CPO/snapshots/` |
| PCB | `themes/PCB/filings/` | `themes/PCB/analysis/`（供應鏈全景圖、基本資料卡、研究索引） | `themes/PCB/snapshots/` |

美股參照：`themes/DRAM/us_peers/{MU_Micron_financials.md, SNDK_SanDisk_financials.md}`

## 其他

- `MS_微軟深度分析.txt`：微軟深度分析文章（非台股主題，待整理）
