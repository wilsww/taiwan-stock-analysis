import { useState } from "react";

/* ============================================================
   記憶體超級循環供應鏈全景圖
   Memory Supercycle Supply Chain Panorama Map
   更新日期: 2026年2月 | 資料基準: Q4 2025 / FY2026 Q1
   ============================================================ */

// ── 供應鏈資料 ─────────────────────────────────────────────
const SUPPLY_CHAIN = [
  {
    id: "upstream",
    layer: "上游",
    labelEn: "UPSTREAM",
    color: "#1e3a5f",
    accent: "#3b82f6",
    categories: [
      {
        name: "矽晶圓",
        nameEn: "Silicon Wafer",
        status: "tight",
        icon: "⬡",
        companies: [
          { name: "信越化學", ticker: "4063.T", region: "🇯🇵", note: "全球最大矽晶圓廠", status: "tight" },
          { name: "SUMCO", ticker: "3436.T", region: "🇯🇵", note: "12吋晶圓吃緊", status: "tight" },
          { name: "台塑勝高", ticker: "私", region: "🇹🇼", note: "南亞科關聯企業供應商", status: "tight" },
          { name: "Siltronic", ticker: "WAF.DE", region: "🇩🇪", note: "歐洲最大矽晶圓廠", status: "balanced" },
        ],
      },
      {
        name: "光罩／光阻劑",
        nameEn: "Photomask / Resist",
        status: "balanced",
        icon: "◉",
        companies: [
          { name: "DNP (大日本印刷)", ticker: "7912.T", region: "🇯🇵", note: "EUV光罩領導廠", status: "balanced" },
          { name: "Shin-Etsu", ticker: "4063.T", region: "🇯🇵", note: "光阻劑龍頭", status: "balanced" },
          { name: "TOK", ticker: "4186.T", region: "🇯🇵", note: "EUV光阻劑", status: "balanced" },
        ],
      },
      {
        name: "關鍵設備",
        nameEn: "Key Equipment",
        status: "tight",
        icon: "⚙",
        companies: [
          { name: "ASML", ticker: "ASML.AS", region: "🇳🇱", note: "EUV/DUV壟斷 | 交期18-24月", status: "tight" },
          { name: "東京威力科創", ticker: "8035.T", region: "🇯🇵", note: "蝕刻/CVD主力", status: "tight" },
          { name: "科磊 KLA", ticker: "KLAC", region: "🇺🇸", note: "量測/檢測", status: "tight" },
          { name: "應材 AMAT", ticker: "AMAT", region: "🇺🇸", note: "薄膜沉積", status: "tight" },
          { name: "Lam Research", ticker: "LRCX", region: "🇺🇸", note: "CMP/蝕刻設備", status: "tight" },
        ],
      },
      {
        name: "特殊氣體／化學品",
        nameEn: "Specialty Gas / Chem",
        status: "balanced",
        icon: "⬟",
        companies: [
          { name: "Air Products", ticker: "APD", region: "🇺🇸", note: "半導體特殊氣體", status: "balanced" },
          { name: "昭和電工", ticker: "4004.T", region: "🇯🇵", note: "CVD前驅物", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "midstream_dram",
    layer: "中游DRAM",
    labelEn: "MIDSTREAM — DRAM",
    color: "#1a2f4a",
    accent: "#06b6d4",
    categories: [
      {
        name: "標準型 DRAM",
        nameEn: "Commodity DRAM",
        status: "tight",
        icon: "▣",
        companies: [
          { name: "Samsung", ticker: "005930.KS", region: "🇰🇷", note: "市占42-45% | P4廠HBM4建設中", status: "tight" },
          { name: "SK Hynix", ticker: "000660.KS", region: "🇰🇷", note: "市占28-30% | HBM轉產擠壓DDR", status: "tight" },
          { name: "Micron", ticker: "MU", region: "🇺🇸", note: "市占20-22% | FY26Q1毛利率56%", status: "tight" },
          { name: "南亞科", ticker: "2408.TW", region: "🇹🇼", note: "市占4-5% | 2025Q4毛利率49%", status: "tight" },
          { name: "CXMT 長鑫", ticker: "私", region: "🇨🇳", note: "DDR4擴張 | EUV禁令限制", status: "loose" },
        ],
      },
      {
        name: "Specialty DRAM",
        nameEn: "Specialty / Niche DRAM",
        status: "tight",
        icon: "▤",
        companies: [
          { name: "華邦電 CMS", ticker: "2344.TW", region: "🇹🇼", note: "Mobile RAM / IoT DRAM | 16nm升級中", status: "tight" },
          { name: "ISSI", ticker: "ISSI", region: "🇺🇸", note: "汽車/工業DRAM利基廠", status: "balanced" },
          { name: "Etron", ticker: "5351.TW", region: "🇹🇼", note: "消費型DRAM", status: "balanced" },
        ],
      },
      {
        name: "HBM（高頻寬記憶體）",
        nameEn: "HBM — High Bandwidth Memory",
        status: "critical",
        icon: "★",
        highlight: true,
        companies: [
          { name: "SK Hynix", ticker: "000660.KS", region: "🇰🇷", note: "HBM市占70% | NVIDIA Vera Rubin主力供應", status: "critical" },
          { name: "Samsung", ticker: "005930.KS", region: "🇰🇷", note: "HBM3e品質問題 | HBM4資格認證中", status: "tight" },
          { name: "Micron", ticker: "MU", region: "🇺🇸", note: "HBM市占10-15% | HBM4廣島廠2026底目標", status: "tight" },
        ],
      },
    ],
  },
  {
    id: "midstream_nand",
    layer: "中游NAND",
    labelEn: "MIDSTREAM — NAND",
    color: "#1a2a3a",
    accent: "#8b5cf6",
    categories: [
      {
        name: "3D NAND（TLC/QLC）",
        nameEn: "3D NAND Mainstream",
        status: "tight",
        icon: "▦",
        companies: [
          { name: "Samsung", ticker: "005930.KS", region: "🇰🇷", note: "NAND市占30%+ | V9 BiCS對標", status: "tight" },
          { name: "SK Hynix/Solidigm", ticker: "000660.KS", region: "🇰🇷", note: "NAND市占18-20%", status: "tight" },
          { name: "Micron", ticker: "MU", region: "🇺🇸", note: "232層G8量產 | 276層G9導入", status: "tight" },
          { name: "Kioxia", ticker: "6600.T", region: "🇯🇵", note: "NAND市占16-18% | BiCS8量產", status: "tight" },
          { name: "WD/SanDisk", ticker: "WD", region: "🇺🇸", note: "Kioxia合資廠 | 分拆後獨立", status: "tight" },
          { name: "YMTC 長江存儲", ticker: "私", region: "🇨🇳", note: "232層 | 企業SSD較弱", status: "loose" },
        ],
      },
      {
        name: "SLC NAND / NOR Flash",
        nameEn: "SLC NAND / NOR Flash",
        status: "critical",
        icon: "▩",
        highlight: true,
        companies: [
          { name: "華邦電 Flash", ticker: "2344.TW", region: "🇹🇼", note: "SPI NOR全球第一27% | SLC NAND第三14%", status: "critical" },
          { name: "旺宏 Macronix", ticker: "2337.TW", region: "🇹🇼", note: "NOR Flash #2", status: "critical" },
          { name: "Kioxia", ticker: "6600.T", region: "🇯🇵", note: "SPI NOR #1 35%市占", status: "critical" },
          { name: "GigaDevice", ticker: "603986.SH", region: "🇨🇳", note: "SLC NAND #2 23%", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "packaging",
    layer: "先進封裝",
    labelEn: "ADVANCED PACKAGING",
    color: "#1f1a3a",
    accent: "#a855f7",
    categories: [
      {
        name: "HBM封裝（CoWoS-M / TSV）",
        nameEn: "HBM Packaging",
        status: "critical",
        icon: "◈",
        highlight: true,
        companies: [
          { name: "台積電 TSMC", ticker: "2330.TW", region: "🇹🇼", note: "CoWoS-M | HBM+GPU 2.5D封裝壟斷", status: "critical" },
          { name: "SK Hynix內部", ticker: "000660.KS", region: "🇰🇷", note: "自有TSV封裝 | Hybrid Bonding投資", status: "tight" },
          { name: "Samsung DS", ticker: "005930.KS", region: "🇰🇷", note: "I-Cube自有封裝", status: "tight" },
        ],
      },
      {
        name: "標準模組封裝",
        nameEn: "Standard Module Packaging",
        status: "balanced",
        icon: "◇",
        companies: [
          { name: "南茂 Chipmos", ticker: "8150.TW", region: "🇹🇼", note: "DRAM測試封裝", status: "balanced" },
          { name: "力成 PTI", ticker: "6239.TW", region: "🇹🇼", note: "記憶體封測龍頭", status: "balanced" },
          { name: "ASE / SPIL", ticker: "3711.TW", region: "🇹🇼", note: "模組級封裝", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "downstream",
    layer: "下游應用",
    labelEn: "DOWNSTREAM DEMAND",
    color: "#1a2020",
    accent: "#10b981",
    categories: [
      {
        name: "AI 伺服器 / HPC",
        nameEn: "AI Server / HPC",
        status: "critical",
        icon: "⬛",
        highlight: true,
        companies: [
          { name: "NVIDIA", ticker: "NVDA", region: "🇺🇸", note: "HBM最大採購方 | GB200/Vera Rubin", status: "critical" },
          { name: "超微 AMD", ticker: "AMD", region: "🇺🇸", note: "MI300X系列 | HBM3e需求", status: "tight" },
          { name: "Google / Meta / MS", ticker: "各自CSP", region: "🌐", note: "CSP CapEx 2026 超$6000億", status: "critical" },
        ],
      },
      {
        name: "PC / 筆電",
        nameEn: "PC / Notebook",
        status: "tight",
        icon: "□",
        companies: [
          { name: "DDR5 升級需求", ticker: "-", region: "🌐", note: "AI PC帶動DDR5滲透", status: "tight" },
          { name: "LPDDR5X", ticker: "-", region: "🌐", note: "薄型筆電主力", status: "tight" },
        ],
      },
      {
        name: "智慧手機",
        nameEn: "Smartphone",
        status: "balanced",
        icon: "▭",
        companies: [
          { name: "LPDDR5X / UFS 4.0", ticker: "-", region: "🌐", note: "AI手機帶動高容量需求", status: "balanced" },
          { name: "Apple / Samsung / 小米", ticker: "-", region: "🌐", note: "旗艦機型記憶體翻倍趨勢", status: "balanced" },
        ],
      },
      {
        name: "汽車 / 工業",
        nameEn: "Automotive / Industrial",
        status: "tight",
        icon: "◻",
        companies: [
          { name: "LPDDR4/SLC NAND", ticker: "-", region: "🌐", note: "ADAS / 車用長交期短缺", status: "tight" },
          { name: "NOR Flash（MCU用）", ticker: "-", region: "🌐", note: "汽車安全法規拉動Secure Flash", status: "tight" },
        ],
      },
    ],
  },
];

// ── 關鍵驅動因子 ─────────────────────────────────────────────
const KEY_DRIVERS = [
  {
    id: "die_penalty",
    title: "HBM「晶粒稅」效應",
    titleEn: "Die Penalty",
    icon: "⚡",
    color: "#f59e0b",
    description: "1GB HBM 佔用約 3GB 標準 DRAM 等效產能（TSV 良率 + 晶粒面積）。三大廠合計 18-28% DRAM 產能轉 HBM，是傳統 DRAM 短缺的結構根因。",
    metric: "容量折換比 1:3",
    impact: "極高",
  },
  {
    id: "capex_constraint",
    title: "設備交期瓶頸",
    titleEn: "Equipment Lead Time",
    icon: "🔧",
    color: "#ef4444",
    description: "ASML EUV 光刻機交期 18-24 個月，即使現在下單，最快 2027 年才能貢獻產能。新廠從動工到量產最少 3 年，供給彈性極低。",
    metric: "EUV 交期 18-24月",
    impact: "高",
  },
  {
    id: "ai_demand",
    title: "AI 需求爆發",
    titleEn: "AI Demand Surge",
    icon: "🤖",
    color: "#06b6d4",
    description: "CSP 2026 年資本支出預估超過 $6,000 億美元（年增40%）。Stargate 專案月耗 9 萬片晶圓當量。AI 消耗全球 DRAM 晶圓等效產能逾 20%。",
    metric: "CSP CapEx $6000億+",
    impact: "極高",
  },
  {
    id: "supply_risk",
    title: "2027 供給衝擊風險",
    titleEn: "2027 Supply Risk",
    icon: "⚠",
    color: "#f97316",
    description: "Samsung P4 廠 HBM4 專用生產線若提前量產 → 釋放傳統 DRAM 容量。南亞科 F 廠 2027 年初裝機。需密切追蹤 H2 2026 ASP 走勢。",
    metric: "追蹤 Samsung P4 時程",
    impact: "需監控",
  },
];

// ── 價格訊號面板 ─────────────────────────────────────────────
const PRICE_SIGNALS = [
  { product: "DDR4 8Gb", price: "$13.00", change: "+13.0%", period: "2026年2月", status: "critical", note: "歷史新高" },
  { product: "NAND 128Gb MLC", price: "$12.67", change: "+33.9%", period: "2026年2月", status: "tight", note: "連漲14個月" },
  { product: "DDR5 Server 64GB", price: "估$110+", change: "+20%+", period: "Q1 2026", status: "critical", note: "AI伺服器拉動" },
  { product: "SLC NAND", price: "Q2 +40-50%", change: "+40-50%", period: "Q2 2026預估", status: "critical", note: "最緊張品項" },
  { product: "NOR Flash SPI", price: "短缺持續", change: "+20%+", period: "2026年", status: "tight", note: "汽車/IoT" },
  { product: "HBM3e", price: "溢價3-5倍", change: "N/A", period: "vs DDR5", status: "critical", note: "供不應求" },
];

// ── 狀態顏色設定 ─────────────────────────────────────────────
const STATUS = {
  critical: { bg: "rgba(239,68,68,0.15)", border: "#ef4444", dot: "#ef4444", label: "極度緊張", text: "#fca5a5" },
  tight: { bg: "rgba(245,158,11,0.12)", border: "#f59e0b", dot: "#f59e0b", label: "供給偏緊", text: "#fcd34d" },
  balanced: { bg: "rgba(16,185,129,0.1)", border: "#10b981", dot: "#10b981", label: "供需平衡", text: "#6ee7b7" },
  loose: { bg: "rgba(99,102,241,0.1)", border: "#6366f1", dot: "#6366f1", label: "供給充裕", text: "#a5b4fc" },
};

// ── 子組件 ────────────────────────────────────────────────────
function StatusDot({ status, size = 8 }) {
  return (
    <span style={{
      display: "inline-block",
      width: size,
      height: size,
      borderRadius: "50%",
      backgroundColor: STATUS[status]?.dot || "#888",
      boxShadow: `0 0 ${size}px ${STATUS[status]?.dot || "#888"}`,
      flexShrink: 0,
    }} />
  );
}

function CompanyCard({ company, accent }) {
  const s = STATUS[company.status] || STATUS.balanced;
  return (
    <div style={{
      background: s.bg,
      border: `1px solid ${s.border}`,
      borderRadius: 6,
      padding: "6px 10px",
      display: "flex",
      alignItems: "flex-start",
      gap: 8,
      marginBottom: 4,
    }}>
      <StatusDot status={company.status} size={7} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: "#f1f5f9", fontFamily: "'IBM Plex Sans', sans-serif" }}>
            {company.region} {company.name}
          </span>
          {company.ticker && company.ticker !== "-" && (
            <span style={{
              fontSize: 10,
              color: "#94a3b8",
              background: "rgba(148,163,184,0.1)",
              border: "1px solid rgba(148,163,184,0.2)",
              borderRadius: 3,
              padding: "1px 5px",
              fontFamily: "monospace",
            }}>{company.ticker}</span>
          )}
        </div>
        <div style={{ fontSize: 11, color: s.text, marginTop: 2, lineHeight: 1.4 }}>{company.note}</div>
      </div>
    </div>
  );
}

function CategoryBlock({ cat, accent }) {
  const s = STATUS[cat.status] || STATUS.balanced;
  return (
    <div style={{
      background: "rgba(15,23,42,0.6)",
      border: `1px solid ${s.border}`,
      borderRadius: 8,
      padding: "10px 12px",
      marginBottom: 10,
    }}>
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        marginBottom: 8,
        paddingBottom: 6,
        borderBottom: `1px solid rgba(255,255,255,0.07)`,
      }}>
        <span style={{ fontSize: 16, opacity: 0.8 }}>{cat.icon}</span>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 800, color: "#e2e8f0", fontFamily: "'IBM Plex Sans', sans-serif" }}>
              {cat.name}
            </span>
            {cat.highlight && (
              <span style={{
                fontSize: 10,
                background: "rgba(239,68,68,0.2)",
                border: "1px solid #ef4444",
                color: "#fca5a5",
                padding: "1px 6px",
                borderRadius: 3,
                fontWeight: 700,
              }}>KEY</span>
            )}
          </div>
          <span style={{ fontSize: 10, color: "#64748b" }}>{cat.nameEn}</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
          <StatusDot status={cat.status} />
          <span style={{ fontSize: 10, color: s.text }}>{s.label}</span>
        </div>
      </div>
      {cat.companies.map((c, i) => <CompanyCard key={i} company={c} accent={accent} />)}
    </div>
  );
}

function LayerPanel({ layer, isActive, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: isActive
          ? `linear-gradient(135deg, ${layer.color} 0%, rgba(30,60,100,0.9) 100%)`
          : "rgba(15,23,42,0.5)",
        border: isActive ? `2px solid ${layer.accent}` : "1px solid rgba(255,255,255,0.08)",
        borderRadius: 8,
        padding: "10px 14px",
        cursor: "pointer",
        textAlign: "left",
        width: "100%",
        transition: "all 0.2s",
        boxShadow: isActive ? `0 0 20px ${layer.accent}30` : "none",
      }}
    >
      <div style={{
        fontSize: 11,
        color: layer.accent,
        fontFamily: "monospace",
        letterSpacing: "0.1em",
        marginBottom: 2,
      }}>
        {layer.labelEn}
      </div>
      <div style={{
        fontSize: 14,
        fontWeight: 800,
        color: isActive ? "#f1f5f9" : "#94a3b8",
        fontFamily: "'IBM Plex Sans', sans-serif",
      }}>
        {layer.layer}
      </div>
      <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>
        {layer.categories.length} 品類 · {layer.categories.reduce((a, c) => a + c.companies.length, 0)} 廠商
      </div>
    </button>
  );
}

// ── 主組件 ────────────────────────────────────────────────────
export default function MemorySupercycleMap() {
  const [activeLayer, setActiveLayer] = useState("midstream_dram");
  const [activeTab, setActiveTab] = useState("chain"); // chain | drivers | signals

  const currentLayer = SUPPLY_CHAIN.find(l => l.id === activeLayer);

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #020617 0%, #0a1628 40%, #06111f 100%)",
      color: "#e2e8f0",
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      padding: "0",
    }}>
      {/* ── Header ── */}
      <div style={{
        background: "linear-gradient(90deg, rgba(3,105,161,0.3) 0%, rgba(6,182,212,0.1) 100%)",
        borderBottom: "1px solid rgba(6,182,212,0.2)",
        padding: "20px 24px 16px",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <div style={{
                width: 4,
                height: 32,
                background: "linear-gradient(180deg, #06b6d4, #3b82f6)",
                borderRadius: 2,
              }} />
              <div>
                <h1 style={{
                  fontSize: 22,
                  fontWeight: 900,
                  margin: 0,
                  background: "linear-gradient(90deg, #06b6d4, #3b82f6, #8b5cf6)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: "-0.5px",
                }}>
                  記憶體超級循環 供應鏈全景圖
                </h1>
                <p style={{ margin: 0, fontSize: 11, color: "#64748b", letterSpacing: "0.08em" }}>
                  MEMORY SUPERCYCLE SUPPLY CHAIN PANORAMA · 2026 FEB UPDATE
                </p>
              </div>
            </div>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {Object.entries(STATUS).map(([key, s]) => (
              <div key={key} style={{
                display: "flex",
                alignItems: "center",
                gap: 5,
                background: s.bg,
                border: `1px solid ${s.border}`,
                borderRadius: 5,
                padding: "4px 8px",
                fontSize: 11,
              }}>
                <StatusDot status={key} size={6} />
                <span style={{ color: s.text }}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Tab 切換 */}
        <div style={{ display: "flex", gap: 4, marginTop: 14 }}>
          {[
            { key: "chain", label: "🔗 供應鏈層級" },
            { key: "drivers", label: "⚡ 關鍵驅動因子" },
            { key: "signals", label: "📊 即時價格訊號" },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                background: activeTab === tab.key ? "rgba(6,182,212,0.2)" : "transparent",
                border: `1px solid ${activeTab === tab.key ? "#06b6d4" : "rgba(255,255,255,0.1)"}`,
                borderRadius: 6,
                padding: "6px 14px",
                color: activeTab === tab.key ? "#06b6d4" : "#64748b",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.15s",
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "20px 24px" }}>

        {/* ── TAB: 供應鏈層級 ── */}
        {activeTab === "chain" && (
          <div style={{ display: "flex", gap: 20, alignItems: "flex-start" }}>

            {/* 左側：層級選擇器 */}
            <div style={{ width: 200, flexShrink: 0 }}>
              <div style={{
                fontSize: 10,
                color: "#475569",
                letterSpacing: "0.12em",
                marginBottom: 8,
                fontWeight: 700,
              }}>SELECT LAYER</div>

              {/* 流程箭頭圖 */}
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                {SUPPLY_CHAIN.map((layer, i) => (
                  <div key={layer.id}>
                    <LayerPanel
                      layer={layer}
                      isActive={activeLayer === layer.id}
                      onClick={() => setActiveLayer(layer.id)}
                    />
                    {i < SUPPLY_CHAIN.length - 1 && (
                      <div style={{
                        display: "flex",
                        justifyContent: "center",
                        padding: "2px 0",
                        color: "#334155",
                        fontSize: 18,
                      }}>↓</div>
                    )}
                  </div>
                ))}
              </div>

              {/* 快速統計 */}
              <div style={{
                marginTop: 16,
                background: "rgba(15,23,42,0.6)",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: 8,
                padding: "12px",
              }}>
                <div style={{ fontSize: 10, color: "#475569", letterSpacing: "0.1em", marginBottom: 8 }}>SUPPLY CHAIN STATS</div>
                {[
                  { label: "總層級", value: SUPPLY_CHAIN.length },
                  { label: "追蹤品類", value: SUPPLY_CHAIN.reduce((a, l) => a + l.categories.length, 0) },
                  { label: "追蹤廠商", value: SUPPLY_CHAIN.reduce((a, l) => a + l.categories.reduce((b, c) => b + c.companies.length, 0), 0) },
                ].map(stat => (
                  <div key={stat.label} style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                    fontSize: 11,
                  }}>
                    <span style={{ color: "#64748b" }}>{stat.label}</span>
                    <span style={{ color: "#06b6d4", fontWeight: 700, fontFamily: "monospace" }}>{stat.value}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* 右側：品類詳情 */}
            <div style={{ flex: 1, minWidth: 0 }}>
              {currentLayer && (
                <>
                  <div style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    marginBottom: 16,
                    padding: "12px 16px",
                    background: `linear-gradient(135deg, ${currentLayer.color}80, rgba(15,23,42,0.9))`,
                    border: `1px solid ${currentLayer.accent}40`,
                    borderRadius: 10,
                    boxShadow: `0 0 30px ${currentLayer.accent}15`,
                  }}>
                    <div>
                      <div style={{ fontSize: 11, color: currentLayer.accent, fontFamily: "monospace", letterSpacing: "0.1em" }}>
                        {currentLayer.labelEn}
                      </div>
                      <div style={{ fontSize: 20, fontWeight: 900, color: "#f1f5f9" }}>
                        {currentLayer.layer}
                      </div>
                    </div>
                    <div style={{ marginLeft: "auto", fontSize: 11, color: "#64748b" }}>
                      {currentLayer.categories.length} 品類 ·&nbsp;
                      {currentLayer.categories.reduce((a, c) => a + c.companies.length, 0)} 廠商追蹤
                    </div>
                  </div>

                  <div style={{
                    display: "grid",
                    gridTemplateColumns: currentLayer.categories.length >= 3 ? "1fr 1fr" : "1fr",
                    gap: 12,
                  }}>
                    {currentLayer.categories.map((cat, i) => (
                      <CategoryBlock key={i} cat={cat} accent={currentLayer.accent} />
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* ── TAB: 關鍵驅動因子 ── */}
        {activeTab === "drivers" && (
          <div>
            <div style={{
              fontSize: 10,
              color: "#475569",
              letterSpacing: "0.12em",
              fontWeight: 700,
              marginBottom: 16,
            }}>KEY STRUCTURAL DRIVERS — 2026年超級週期核心成因分析</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
              {KEY_DRIVERS.map(driver => (
                <div
                  key={driver.id}
                  style={{
                    background: "rgba(15,23,42,0.8)",
                    border: `1px solid ${driver.color}50`,
                    borderLeft: `4px solid ${driver.color}`,
                    borderRadius: 10,
                    padding: "18px 20px",
                    boxShadow: `0 4px 24px ${driver.color}10`,
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                    <span style={{ fontSize: 24 }}>{driver.icon}</span>
                    <div>
                      <div style={{ fontSize: 15, fontWeight: 800, color: "#f1f5f9" }}>{driver.title}</div>
                      <div style={{ fontSize: 10, color: "#64748b", letterSpacing: "0.05em" }}>{driver.titleEn}</div>
                    </div>
                  </div>
                  <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.7, margin: "0 0 14px" }}>
                    {driver.description}
                  </p>
                  <div style={{ display: "flex", gap: 8 }}>
                    <div style={{
                      background: `${driver.color}20`,
                      border: `1px solid ${driver.color}50`,
                      borderRadius: 5,
                      padding: "4px 10px",
                      fontSize: 11,
                      color: driver.color,
                      fontWeight: 700,
                    }}>
                      {driver.metric}
                    </div>
                    <div style={{
                      background: driver.impact === "極高" ? "rgba(239,68,68,0.15)" : "rgba(245,158,11,0.15)",
                      border: `1px solid ${driver.impact === "極高" ? "#ef4444" : "#f59e0b"}50`,
                      borderRadius: 5,
                      padding: "4px 10px",
                      fontSize: 11,
                      color: driver.impact === "極高" ? "#fca5a5" : "#fcd34d",
                      fontWeight: 700,
                    }}>
                      影響力：{driver.impact}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* HBM Die Penalty 視覺化 */}
            <div style={{
              marginTop: 20,
              background: "rgba(15,23,42,0.8)",
              border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 10,
              padding: "20px",
            }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#fca5a5", marginBottom: 12 }}>
                ⚡ HBM 晶粒稅效應 — 容量換算示意
              </div>
              <div style={{ display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  {[
                    { label: "1 GB HBM3e", equiv: "3 GB DDR5 等效產能", ratio: 100, color: "#ef4444" },
                    { label: "HBM 佔三大廠產能", equiv: "18-28% DRAM 產能轉用", ratio: 28, color: "#f59e0b" },
                    { label: "傳統 DRAM 等效損失", equiv: "全球 ~15-20% 供給縮減", ratio: 20, color: "#f97316" },
                  ].map(item => (
                    <div key={item.label} style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: 12, color: "#94a3b8" }}>{item.label}</span>
                        <span style={{ fontSize: 12, color: item.color, fontWeight: 700 }}>{item.equiv}</span>
                      </div>
                      <div style={{
                        height: 6,
                        background: "rgba(255,255,255,0.05)",
                        borderRadius: 3,
                        overflow: "hidden",
                      }}>
                        <div style={{
                          height: "100%",
                          width: `${item.ratio}%`,
                          background: `linear-gradient(90deg, ${item.color}80, ${item.color})`,
                          borderRadius: 3,
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.3)",
                  borderRadius: 8,
                  padding: "16px 20px",
                  textAlign: "center",
                  minWidth: 160,
                }}>
                  <div style={{ fontSize: 36, fontWeight: 900, color: "#ef4444", fontFamily: "monospace" }}>1:3</div>
                  <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 4 }}>HBM : Standard DRAM</div>
                  <div style={{ fontSize: 10, color: "#64748b", marginTop: 2 }}>容量等效產能比</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── TAB: 即時價格訊號 ── */}
        {activeTab === "signals" && (
          <div>
            <div style={{
              fontSize: 10,
              color: "#475569",
              letterSpacing: "0.12em",
              fontWeight: 700,
              marginBottom: 16,
            }}>REAL-TIME PRICE SIGNALS — DRAMeXchange / TrendForce 數據</div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 12 }}>
              {PRICE_SIGNALS.map((sig, i) => {
                const s = STATUS[sig.status];
                return (
                  <div key={i} style={{
                    background: s.bg,
                    border: `1px solid ${s.border}`,
                    borderRadius: 10,
                    padding: "16px 18px",
                    boxShadow: `0 0 20px ${s.dot}10`,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                      <div>
                        <div style={{ fontSize: 14, fontWeight: 800, color: "#f1f5f9" }}>{sig.product}</div>
                        <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>{sig.period}</div>
                      </div>
                      <StatusDot status={sig.status} size={10} />
                    </div>
                    <div style={{ display: "flex", gap: 10, alignItems: "baseline" }}>
                      <span style={{ fontSize: 22, fontWeight: 900, color: "#f1f5f9", fontFamily: "monospace" }}>
                        {sig.price}
                      </span>
                      <span style={{
                        fontSize: 14,
                        fontWeight: 700,
                        color: s.text,
                        fontFamily: "monospace",
                      }}>
                        {sig.change}
                      </span>
                    </div>
                    <div style={{
                      marginTop: 8,
                      fontSize: 11,
                      color: s.text,
                      background: `${s.dot}15`,
                      border: `1px solid ${s.border}40`,
                      borderRadius: 4,
                      padding: "3px 8px",
                      display: "inline-block",
                    }}>
                      {sig.note}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 價格回顧：DDR4 688% 上漲路徑 */}
            <div style={{
              marginTop: 20,
              background: "rgba(15,23,42,0.8)",
              border: "1px solid rgba(6,182,212,0.2)",
              borderRadius: 10,
              padding: "20px",
            }}>
              <div style={{ fontSize: 14, fontWeight: 800, color: "#06b6d4", marginBottom: 14 }}>
                📈 DDR4 8Gb 價格重建 — 史上最猛烈的記憶體反彈（+688%）
              </div>
              <div style={{ overflowX: "auto" }}>
                <div style={{ display: "flex", gap: 4, minWidth: 600, alignItems: "flex-end", height: 80 }}>
                  {[
                    { month: "Apr 2025", price: 1.65, label: "谷底 $1.65" },
                    { month: "Jun 2025", price: 2.8 },
                    { month: "Aug 2025", price: 4.8 },
                    { month: "Sep 2025", price: 6.3, label: "+10.5%" },
                    { month: "Oct 2025", price: 7.0 },
                    { month: "Nov 2025", price: 9.5 },
                    { month: "Dec 2025", price: 11.5 },
                    { month: "Jan 2026", price: 11.5 },
                    { month: "Feb 2026", price: 13.0, label: "新高 $13.00" },
                  ].map((point, i, arr) => {
                    const maxPrice = Math.max(...arr.map(p => p.price));
                    const heightPct = (point.price / maxPrice) * 100;
                    const isFirst = i === 0;
                    const isLast = i === arr.length - 1;
                    return (
                      <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
                        {point.label && (
                          <div style={{
                            fontSize: 9,
                            color: isLast ? "#ef4444" : "#6ee7b7",
                            fontWeight: 700,
                            marginBottom: 2,
                            whiteSpace: "nowrap",
                          }}>
                            {point.label}
                          </div>
                        )}
                        <div style={{ flex: 1, display: "flex", alignItems: "flex-end", width: "100%" }}>
                          <div style={{
                            width: "100%",
                            height: `${heightPct}%`,
                            background: isLast
                              ? "linear-gradient(180deg, #ef4444, #dc2626)"
                              : isFirst
                              ? "linear-gradient(180deg, #10b981, #059669)"
                              : "linear-gradient(180deg, #06b6d4, #0284c7)",
                            borderRadius: "3px 3px 0 0",
                            minHeight: 4,
                          }} />
                        </div>
                        <div style={{ fontSize: 8, color: "#475569", marginTop: 3, whiteSpace: "nowrap" }}>
                          {point.month.replace(" 2025", "").replace(" 2026", "")}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div style={{
                marginTop: 10,
                display: "flex",
                gap: 16,
                fontSize: 11,
                color: "#64748b",
                flexWrap: "wrap",
              }}>
                <span>🟢 谷底 Apr 2025: <strong style={{ color: "#6ee7b7" }}>$1.65</strong></span>
                <span>🔴 新高 Feb 2026: <strong style={{ color: "#fca5a5" }}>$13.00</strong></span>
                <span>📈 累計漲幅: <strong style={{ color: "#f59e0b" }}>+688%</strong>（10個月）</span>
                <span style={{ marginLeft: "auto", color: "#334155" }}>Source: DRAMeXchange / TrendForce</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,0.05)",
        padding: "12px 24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 8,
      }}>
        <span style={{ fontSize: 10, color: "#334155" }}>
          資料來源：TrendForce DRAMeXchange · Micron 10-K/10-Q · 南亞科 Q4 新聞稿 · 華邦電法說會 · Kioxia Result Sheet
        </span>
        <span style={{ fontSize: 10, color: "#334155" }}>更新：2026年2月 · 下次更新：Q1 法說會後</span>
      </div>
    </div>
  );
}
