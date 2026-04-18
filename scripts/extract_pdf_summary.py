#!/usr/bin/env python3
"""
extract_pdf_summary.py — PDF 財報預萃取工具

用途：將 themes/{DRAM,CPO,PCB}/filings/ 下的 PDF 前 15 頁文字萃取為 Markdown 摘要，
      存入 research/pdf_summaries/{ticker}_{stem}.md，
      供 deep-analysis STEP 0 優先讀取，避免主 context 直接讀取大型 PDF。

依賴安裝：
    pip3 install pdfplumber

使用範例：
    python3 scripts/extract_pdf_summary.py                     # 處理所有 PDF
    python3 scripts/extract_pdf_summary.py --theme DRAM        # 只處理 DRAM
    python3 scripts/extract_pdf_summary.py --ticker 南亞科      # 只處理含此關鍵字的 PDF
    python3 scripts/extract_pdf_summary.py --force             # 強制重新萃取
    python3 scripts/extract_pdf_summary.py --dry-run           # 只列出，不執行
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# ── 依賴檢查 ──────────────────────────────────────────────────────────────────
try:
    import pdfplumber
except ImportError:
    print("ERROR: pdfplumber 未安裝")
    print("請執行：pip3 install pdfplumber")
    sys.exit(1)

# ── 設定 ──────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent.parent
THEMES_DIR  = BASE_DIR / "themes"
SUMMARY_DIR = BASE_DIR / "research" / "pdf_summaries"

MAX_PAGES    = 15    # 萃取前 N 頁
MAX_CHARS    = 8000  # 每頁最多保留字元數
MIN_TEXT_LEN = 100   # 低於此字元數視為掃描圖片頁

THEMES = ["DRAM", "CPO", "PCB"]

# 檔名關鍵字 → 標的代碼
TICKER_KEYWORDS = {
    "南亞科": "2408",
    "華邦電": "2344",
    "聯亞光": "3081",
    "全新":   "2455",
    "上詮":   "3363",
    "華星光": "4979",
    "穩懋":   "3105",
    "欣興":   "3037",
    "南電":   "8046",
    "景碩":   "3189",
    "Micron": "MU",
    "Kioxia": "Kioxia",
    "力成":   "6239",
}

# 財務關鍵字（評分用）
FINANCIAL_KEYWORDS = [
    "毛利", "毛利率", "EPS", "每股盈餘", "營收", "revenue",
    "gross margin", "CapEx", "資本支出", "產能利用率",
    "guidance", "指引", "展望", "outlook",
    "DSI", "inventory", "庫存", "ASP",
    "EBITDA", "淨利", "net income",
]


def detect_ticker(filename: str) -> str:
    """從檔名關鍵字推斷標的代碼，無法對應則回傳 'unknown'。"""
    for keyword, ticker in TICKER_KEYWORDS.items():
        if keyword in filename:
            return ticker
    return "unknown"


def extract_pages(pdf_path: Path, max_pages: int = MAX_PAGES) -> list[dict]:
    """萃取 PDF 前 max_pages 頁的文字與表格。"""
    results = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_to_read = min(max_pages, len(pdf.pages))
            for i in range(pages_to_read):
                page = pdf.pages[i]
                # 嘗試萃取表格（財報數字多在表格中）
                table_text = ""
                for table in page.extract_tables() or []:
                    for row in table:
                        if row:
                            table_text += " | ".join(
                                str(c).strip() if c else "" for c in row
                            ) + "\n"
                raw_text = page.extract_text() or ""
                combined = raw_text if not table_text else f"{raw_text}\n\n[表格]\n{table_text}"
                if len(combined) > MAX_CHARS:
                    combined = combined[:MAX_CHARS] + "\n...[截斷]"
                results.append({
                    "page": i + 1,
                    "text": combined,
                    "is_scan": len(raw_text) < MIN_TEXT_LEN,
                })
    except Exception as e:
        results.append({"page": 0, "text": f"[萃取失敗：{e}]", "is_scan": True})
    return results


def filter_pages(pages: list[dict]) -> list[dict]:
    """保留財務關鍵字密度高的頁面，最多 10 頁；第 1 頁與最後萃取頁必留。"""
    scored = sorted(
        pages,
        key=lambda p: sum(1 for kw in FINANCIAL_KEYWORDS if kw.lower() in p["text"].lower()),
        reverse=True,
    )
    keep = {p["page"] for p in scored[:10]}
    keep.add(pages[0]["page"])
    if len(pages) > 1:
        keep.add(pages[-1]["page"])
    return sorted([p for p in pages if p["page"] in keep], key=lambda p: p["page"])


def build_markdown(pdf_path: Path, ticker: str, theme: str, pages: list[dict]) -> str:
    """將萃取頁面組合為 Markdown 摘要，格式與現有 research/ MD 一致。"""
    now = datetime.now().strftime("%Y年%m月%d日")
    scan_pages = [str(p["page"]) for p in pages if p["is_scan"]]
    scan_note = f"\n> ⚠️ 掃描圖片頁（文字無法萃取）：第 {', '.join(scan_pages)} 頁" if scan_pages else ""

    header = (
        f"# PDF 摘要：{pdf_path.name}\n\n"
        f"> **來源**：`themes/{theme}/filings/{pdf_path.name}`\n"
        f"> **標的代碼**：{ticker}\n"
        f"> **主題**：{theme}\n"
        f"> **萃取頁數**：前 {pages[-1]['page'] if pages else 0} 頁"
        f"（共萃取 {len(pages)} 頁有效內容）\n"
        f"> **萃取時間**：{now}\n"
        f"> **用途**：供 deep-analysis STEP 0 讀取，避免主 context 直接讀取原始 PDF"
        f"{scan_note}\n\n---\n\n"
    )
    sections = []
    for p in pages:
        label = f"## 第 {p['page']} 頁" + (" ⚠️ 掃描頁" if p["is_scan"] else "")
        sections.append(f"{label}\n\n{p['text']}")
    return header + "\n\n---\n\n".join(sections) + "\n"


def process_pdf(pdf_path: Path, theme: str, force: bool = False) -> dict:
    """處理單一 PDF。回傳 status（ok/skip/error）、output_path、message。"""
    ticker = detect_ticker(pdf_path.name)
    output_path = SUMMARY_DIR / f"{ticker}_{pdf_path.stem}.md"

    if output_path.exists() and not force:
        return {"status": "skip", "output_path": output_path,
                "message": "已存在，略過（--force 可強制重建）"}
    try:
        pages = extract_pages(pdf_path)
        filtered = filter_pages(pages)
        content = build_markdown(pdf_path, ticker, theme, filtered)
        SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")
        return {"status": "ok", "output_path": output_path,
                "message": f"萃取 {len(filtered)} 頁，{len(content):,} 字元"}
    except Exception as e:
        return {"status": "error", "output_path": output_path, "message": str(e)}


def main():
    parser = argparse.ArgumentParser(description="PDF 財報預萃取工具")
    parser.add_argument("--theme", choices=THEMES, help="只處理指定主題")
    parser.add_argument("--ticker", help="只處理檔名含此關鍵字的 PDF（如 南亞科 或 2408）")
    parser.add_argument("--force", action="store_true", help="強制重新萃取")
    parser.add_argument("--dry-run", action="store_true", help="只列出，不執行")
    args = parser.parse_args()

    themes = [args.theme] if args.theme else THEMES
    counts = {"ok": 0, "skip": 0, "error": 0}

    for theme in themes:
        theme_dir = THEMES_DIR / theme / "filings"
        if not theme_dir.exists():
            print(f"[WARN] 目錄不存在：{theme_dir}")
            continue

        pdfs = sorted(theme_dir.glob("*.pdf"))
        if args.ticker:
            pdfs = [f for f in pdfs if args.ticker in f.name]

        print(f"\n=== {theme}（{len(pdfs)} 個 PDF）===")

        for pdf_path in pdfs:
            if args.dry_run:
                ticker = detect_ticker(pdf_path.name)
                print(f"  [DRY-RUN] {pdf_path.name}  →  {ticker}_{pdf_path.stem}.md")
                continue

            result = process_pdf(pdf_path, theme, force=args.force)
            icon = {"ok": "✅", "skip": "⏭", "error": "❌"}.get(result["status"], "?")
            print(f"  {icon} {pdf_path.name}")
            print(f"       → {result['output_path'].name}：{result['message']}")
            counts[result["status"]] += 1

    if not args.dry_run:
        print(f"\n=== 完成 ===")
        print(f"  成功：{counts['ok']} | 略過：{counts['skip']} | 失敗：{counts['error']}")
        if counts["ok"] > 0:
            print(f"  摘要目錄：{SUMMARY_DIR}")


if __name__ == "__main__":
    main()
