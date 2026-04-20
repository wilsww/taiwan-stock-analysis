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

## 📦 主要 commit

- `8153656` refactor(sector_flow_dashboard): extract dashboard modules and main data flow
- `fdbdef5` refactor(sector_flow_dashboard): extract dashboard tabs and data modules
- `0b4f4bc` docs(log): move improve plan and record phase d cleanup

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
