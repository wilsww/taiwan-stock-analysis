# SanDisk Corporation (SNDK) — Financial Data
> Last Updated: 2026-04-14 | Status: PLACEHOLDER — data pending
> Role: Pure-play NAND Flash benchmark — pricing / supply signal for NAND segment

---

## Company Background

- **Spun off**: from Western Digital Corporation (WDC) in **February 2025**
- **Ticker**: SNDK (Nasdaq)
- **Focus**: NAND Flash memory and SSDs (consumer, enterprise, industrial)
- **WDC retained**: HDD business under Western Digital brand
- **EDGAR coverage**: Limited — first standalone filings as of 2025; SEC EDGAR search may not yet index all filings

---

## Data Status

| Source | Status | Notes |
|--------|--------|-------|
| SEC EDGAR | Not found | Company too new; EDGAR full-text search not indexing SNDK yet |
| Yahoo Finance | Rate limited (2026-04-14) | Retry later: `mcp__yahoo-finance__get_financials("SNDK", "income", quarterly=True)` |
| Press releases | Not yet retrieved | Check investor.sandisk.com |

---

## Income Statement — TO BE POPULATED

| Metric | Q_FY2026 | Q_FY2025 | YoY |
|--------|---------|---------|-----|
| Revenue | — | — | — |
| Gross Profit | — | — | — |
| Gross Margin | — | — | — |
| Operating Income | — | — | — |
| Net Income | — | — | — |
| EPS (Diluted) | — | — | — |

---

## Balance Sheet — TO BE POPULATED

| Item | Latest Quarter | Prior Quarter |
|------|---------------|---------------|
| Cash | — | — |
| Total Assets | — | — |
| Total Debt | — | — |
| Shareholders' Equity | — | — |

---

## How to Update

### Option 1: Yahoo Finance MCP (preferred, once rate limit clears)
```
mcp__yahoo-finance__get_financials(symbol="SNDK", statement="income", quarterly=True)
mcp__yahoo-finance__get_quote(symbol="SNDK")
mcp__yahoo-finance__get_company_info(symbol="SNDK")
```

### Option 2: SEC EDGAR (once indexed)
```
mcp__sec-edgar__search_companies(query="SanDisk Corporation")
mcp__sec-edgar__get_financials(identifier="SNDK", statement_type="all")
```

### Option 3: Manual
- Investor relations: https://investor.sandisk.com
- SEC EDGAR full-text: https://efts.sec.gov/LATEST/search-index?q=%22SanDisk+Corporation%22&dateRange=custom&startdt=2025-01-01

---

## Strategic Context (NAND Flash)

- Post-spinoff, SanDisk is the **pure-play NAND** vehicle (vs. Kioxia which is private/Japan)
- NAND cycle: oversupply in 2023–2024 → recovery in 2025 driven by AI SSD demand (enterprise NVMe)
- Enterprise SSD margins recovering; consumer NAND still pressured by Chinese competition
- Kioxia joint venture fabs still shared with SanDisk post-spinoff (Yokkaichi, Kitakami)

---

## Relevance to Taiwan Portfolio

| Taiwan Stock | SNDK Signal | Watch For |
|-------------|-------------|-----------|
| 華邦電（2344） | Specialty NAND/NOR separate from commodity; indirect signal | NAND pricing floor, WFE spend |
| 欣興（3037）/景碩（3189） | Enterprise SSD demand → server ABF substrate pull | Enterprise SSD shipment growth |

---

## TODO
- [ ] Retry Yahoo Finance MCP for Q1/Q2 FY2025 revenue, GM, EPS
- [ ] Populate balance sheet (total debt from WD spinoff allocation)
- [ ] Add NAND bit shipment and ASP trend data
- [ ] Cross-reference with Kioxia pricing data
