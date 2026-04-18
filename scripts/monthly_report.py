#!/usr/bin/env python3
"""
台股月報自動分析腳本
用途：讀取月營收資料庫，依照 5 步驟分析框架產出 Markdown 報告
使用：python3 scripts/monthly_report.py --month 2026-02
"""

import argparse
import sqlite3
import json
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
REVENUE_DIR = DATA_DIR / "revenue"
REPORTS_DIR = Path(__file__).parent.parent / "reports" / "monthly"
DB_PATH = REVENUE_DIR / "revenue.db"

COMPANY_NAMES = {
    "2408": "南亞科技",
    "2344": "華邦電子",
    "3363": "上詮光纖",
    "2455": "全新光電",
    "4979": "華星光通",
    "3081": "聯亞光電",
    "3105": "穩懋半導體",
    # CPO 擴充觀察名單
    "6442": "光聖",
    "4977": "眾達-KY",
    "3163": "波若威",
    "2345": "智邦",
    "6223": "旺矽",
    # IC 載板 PCB 標的
    "3037": "欣興電子",
    "8046": "南亞電路板",
    "3189": "景碩科技",
}

# 前瞻性措辭關鍵字（Guidance Tone 判斷用）
BULLISH_KEYWORDS = ["強勁", "超預期", "持續成長", "滿載", "看好", "上修", "創新高"]
BEARISH_KEYWORDS = ["審慎", "觀望", "下修", "庫存調整", "能見度低", "謹慎"]


def get_revenue_data(ticker: str, months: int = 6) -> list:
    """從資料庫取得近 N 個月的月營收數據"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT year, month, revenue_m, mom_pct, yoy_pct
        FROM monthly_revenue
        WHERE ticker = ?
        ORDER BY year DESC, month DESC
        LIMIT ?
    """, (ticker, months))
    rows = c.fetchall()
    conn.close()
    return rows


def assess_revenue_trend(rows: list) -> str:
    """評估營收趨勢"""
    if len(rows) < 2:
        return "資料不足，無法判斷趨勢"
    latest = rows[0]
    prev = rows[1]
    mom = latest[3]
    yoy = latest[4]

    if mom is None or yoy is None:
        return "數據缺失"

    if mom > 10 and yoy > 50:
        return "🟢 強勁加速（MoM+YoY雙正向）"
    elif mom > 0 and yoy > 0:
        return "🟡 溫和成長"
    elif mom < -5 or yoy < -10:
        return "🔴 明顯走弱"
    else:
        return "⚪ 持平震盪"


def generate_risk_section() -> str:
    """產生常駐風險監控區塊（每份報告必含）"""
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""
## ⚠️ 四大風險監控（更新日：{today}）

> **每次分析必須評估以下四項，請在報告中填寫最新狀態。**

### 1. CXMT 競爭風險
- **追蹤指標**：DDR3/DDR4 市場定價壓力、中國廠出貨市占
- **上次狀態**：EUV 受限，進階製程良率落後；傳統 DDR3 已有壓力
- **本月更新**：[ 請填寫 ]

### 2. 三星產能風險（P4 fab HBM4）
- **追蹤指標**：Samsung P4 量產時程確認與否
- **關鍵窗口**：2027H1 供給衝擊視窗
- **本月更新**：[ 請填寫 ]

### 3. AI 需求泡沫風險
- **追蹤指標**：Hyperscaler CapEx 指引 YoY 增速
- **警戒線**：任一大廠 CapEx YoY 降幅 > 10%
- **本月更新**：[ 請填寫 ]

### 4. 地緣政治風險
- **追蹤指標**：台海情勢、美中出口管制、CHIPS Act
- **上次狀態**：InP 基板出口管制已解除（2025Q3）
- **本月更新**：[ 請填寫 ]
"""


def generate_report(month_str: str, tickers: list) -> str:
    """產生完整月報 Markdown"""
    try:
        dt = datetime.strptime(month_str, "%Y-%m")
    except ValueError:
        print(f"❌ 日期格式錯誤，請用 YYYY-MM（如 2026-02）")
        return ""

    year, month = dt.year, dt.month
    report_lines = []

    # ── 報告標頭 ──
    report_lines.append(f"# 台灣科技股月營收分析報告")
    report_lines.append(f"## {year}年{month:02d}月")
    report_lines.append(f"產出時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    report_lines.append("")
    report_lines.append("> 分析規則：5步驟框架（毛利率→產能→DSI→CapEx→Guidance tone）")
    report_lines.append("> 本報告僅供個人研究參考，非正式投資建議")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # ── 月營收總覽表 ──
    report_lines.append("## 📊 月營收總覽")
    report_lines.append("")
    report_lines.append("| 代碼 | 公司 | 當月營收 | MoM% | YoY% | 趨勢判斷 |")
    report_lines.append("|------|------|---------|------|------|---------|")

    has_data = False
    for ticker in tickers:
        rows = get_revenue_data(ticker, months=3)
        company = COMPANY_NAMES.get(ticker, ticker)
        if rows:
            latest = rows[0]
            rev_b = latest[2] / 1000 if latest[2] else 0
            mom_s = f"{latest[3]:+.1f}%" if latest[3] is not None else "N/A"
            yoy_s = f"{latest[4]:+.1f}%" if latest[4] is not None else "N/A"
            trend = assess_revenue_trend(rows)
            report_lines.append(f"| {ticker} | {company} | NT${rev_b:.2f}億 | {mom_s} | {yoy_s} | {trend} |")
            has_data = True
        else:
            report_lines.append(f"| {ticker} | {company} | 無資料 | - | - | ❓ 待更新 |")

    report_lines.append("")

    if not has_data:
        report_lines.append("> ⚠️ 資料庫中無月營收數據，請先執行 `python3 scripts/fetch_revenue.py`")
        report_lines.append("")

    report_lines.append("---")
    report_lines.append("")

    # ── 5 步驟深度分析框架 ──
    report_lines.append("## 🔬 深度分析（5步驟框架）")
    report_lines.append("")
    report_lines.append("> 以下為分析框架模板，請依最新財報數據填入結論。")
    report_lines.append("")

    for ticker in tickers[:2]:  # 主要標的詳細分析
        company = COMPANY_NAMES.get(ticker, ticker)
        rows = get_revenue_data(ticker, months=6)
        report_lines.append(f"### {company}（{ticker}）")
        report_lines.append("")

        # 步驟 1：毛利率趨勢
        report_lines.append("**步驟 1：毛利率趨勢（QoQ / YoY）**")
        report_lines.append("")
        if ticker == "2408":
            report_lines.append("- 2025Q4 毛利率：**49.0%**（QoQ +30.5pp，歷史性跳升）")
            report_lines.append("- 趨勢：加速上行中，2026Q1 預估 55-62%")
        elif ticker == "2344":
            report_lines.append("- 純記憶體段落毛利率：[ 請更新 ]")
            report_lines.append("- 注意：新唐（4919）子公司稀釋合併毛利率約 9pp，務必拆分")
        else:
            report_lines.append("- [ 請填入最新毛利率數據 ]")
        report_lines.append("")

        # 步驟 2：產能利用率與 ASP
        report_lines.append("**步驟 2：產能利用率與 ASP 變化**")
        report_lines.append("")
        report_lines.append("- 產能利用率：[ 請填入 ]%（警戒：80% 以下為疲軟訊號）")
        report_lines.append("- ASP 趨勢：[ 上升 / 持平 / 下滑 ]")
        report_lines.append("- DDR5 佔比：[ 請填入 ]%（升降方向）")
        report_lines.append("")

        # 步驟 3：庫存水位
        report_lines.append("**步驟 3：庫存水位（DSI）**")
        report_lines.append("")
        report_lines.append("- 當前 DSI：[ 請填入 ] 天")
        report_lines.append("- 健康區間：45-60 天；>75 天為警戒")
        report_lines.append("- 客戶庫存狀態：[ 正常 / 偏高 / 去化中 ]")
        report_lines.append("")

        # 步驟 4：資本支出指引
        report_lines.append("**步驟 4：資本支出指引**")
        report_lines.append("")
        if ticker == "2408":
            report_lines.append("- 2026 CapEx 計畫：NT$500 億（歷史最高，待董事會決議）")
            report_lines.append("- F 廠裝機時程：2027 年初（進度是否如期？）")
        elif ticker == "2344":
            report_lines.append("- 2026 CapEx：歷史性跳升（16nm CMS + 24nm Flash 同步轉換）")
            report_lines.append("- 全年產能：已滿載預訂")
        else:
            report_lines.append("- CapEx 方向：[ 擴產 / 維護性 / 縮減 ]")
        report_lines.append("")

        # 步驟 5：Guidance Tone
        report_lines.append("**步驟 5：管理層前瞻性措辭（Guidance Tone）**")
        report_lines.append("")
        report_lines.append("- 措辭評估：[ 🟢 積極 / 🟡 中性 / 🔴 保守 ]")
        report_lines.append("- 關鍵引述：[ 請填入法說會或新聞稿原文 ]")
        report_lines.append("- 下季展望：[ 請填入 ]")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")

    # ── 估值觀察 ──
    report_lines.append("## 💰 估值觀察（加權目標價）")
    report_lines.append("")
    report_lines.append("| 公司 | 情境 | EPS假設 | PE倍數 | PB倍數 | 目標價 | 概率 |")
    report_lines.append("|------|------|--------|--------|--------|--------|------|")
    report_lines.append("| 南亞科 2408 | Bear | NT$12 | 8-12x | 1.2-1.8x | NT$X | 20% |")
    report_lines.append("| 南亞科 2408 | Base | NT$18 | 10-15x | 2.0-2.8x | NT$X | 55% |")
    report_lines.append("| 南亞科 2408 | Bull | NT$25 | 12-18x | 3.0-4.5x | NT$X | 25% |")
    report_lines.append("| 華邦電 2344 | Bear | NT$X | Xx-Xx | Xx-Xx | NT$X | 20% |")
    report_lines.append("| 華邦電 2344 | Base | NT$X | Xx-Xx | Xx-Xx | NT$X | 55% |")
    report_lines.append("| 華邦電 2344 | Bull | NT$X | Xx-Xx | Xx-Xx | NT$X | 25% |")
    report_lines.append("")
    report_lines.append("> 加權目標價 = Bear×20% + Base×55% + Bull×25%")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # ── 催化劑追蹤 ──
    report_lines.append("## 🎯 催化劑追蹤")
    report_lines.append("")
    report_lines.append("### 短線（1-3 個月）")
    report_lines.append("- [ ] 下月月營收公布（~次月 10 日）")
    report_lines.append("- [ ] 法說會日期確認")
    report_lines.append("- [ ] NVIDIA / Microsoft / Google / Amazon 季報 CapEx 數字")
    report_lines.append("")
    report_lines.append("### 中線（3-12 個月）")
    report_lines.append("- [ ] 季毛利率拐點確認（>55% 為主升訊號）")
    report_lines.append("- [ ] 產能利用率回升至 80%+")
    report_lines.append("- [ ] DRAM 合約價 QoQ 變化率")
    report_lines.append("")
    report_lines.append("### 長線（1-3 年）")
    report_lines.append("- [ ] 南亞科 1C 製程量產進度（目標 2027）")
    report_lines.append("- [ ] CPO 滲透率是否突破 10%")
    report_lines.append("- [ ] 上詮 1.6T CPO FAU 量產確認")
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("")

    # ── 四大風險監控 ──
    report_lines.append(generate_risk_section())

    # ── 頁尾 ──
    report_lines.append("")
    report_lines.append("---")
    report_lines.append(f"*報告生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    report_lines.append("*資料來源：月營收資料庫 + Project Files 財報 + 網路搜尋補充*")
    report_lines.append("*所有數字均為研究估算，非正式投資建議*")

    return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(description="台股月報自動分析")
    parser.add_argument("--month", default=datetime.now().strftime("%Y-%m"),
                        help="分析月份 YYYY-MM（預設當月）")
    parser.add_argument("--ticker", nargs="+",
                        default=["2408", "2344", "3363", "2455", "4979", "3081", "3105",
                                 "6442", "4977", "3163", "2345", "6223",
                                 "3037", "8046", "3189"],
                        help="分析標的")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n📝 產出 {args.month} 月報分析...")
    print(f"   標的：{', '.join(args.ticker)}\n")

    report_md = generate_report(args.month, args.ticker)
    if not report_md:
        return

    # 存檔
    filename = f"monthly_report_{args.month.replace('-', '')}.md"
    output_path = REPORTS_DIR / filename
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"✅ 報告已產出：{output_path}")
    print(f"\n📌 下一步：")
    print(f"   1. 開啟 {output_path}")
    print(f"   2. 填入各步驟的最新財報數據")
    print(f"   3. 更新四大風險監控狀態")
    print(f"   4. 執行 python3 scripts/update_db.py 更新估值模型")


if __name__ == "__main__":
    main()
