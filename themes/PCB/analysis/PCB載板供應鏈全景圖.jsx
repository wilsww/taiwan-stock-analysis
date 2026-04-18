import { useState } from "react";

/* ============================================================
   PCB 載板（IC 基板）供應鏈全景圖
   ABF Substrate Supply Chain Panorama Map
   更新日期: 2026年3月 | 資料基準: 2025全年法說 / 2026Q4法說會
   ============================================================ */

// ── 供應鏈資料 ─────────────────────────────────────────────
const SUPPLY_CHAIN = [
  {
    id: "demand",
    layer: "L0 需求端",
    labelEn: "L0 DEMAND — AI GPU DRIVER",
    color: "#1a1040",
    accent: "#a855f7",
    categories: [
      {
        name: "AI GPU / ASIC 需求驅動",
        nameEn: "AI GPU / ASIC Demand Driver",
        status: "critical",
        icon: "⬛",
        highlight: true,
        companies: [
          { name: "NVIDIA", ticker: "NVDA", region: "🇺🇸", note: "GB200/B300/GB300系列 | 每顆AI GPU所需ABF面積 vs CPU大 8-12x | Spectrum-X CoWoS ABF載板最大需求端", status: "critical" },
          { name: "AMD", ticker: "AMD", region: "🇺🇸", note: "MI300X/MI400 GPU | ABF載板高成長需求 | HPC市場NVIDIA主要競爭者", status: "critical" },
          { name: "Intel", ticker: "INTC", region: "🇺🇸", note: "Gaudi AI加速器 + CPU CPU/GPU ABF採購 | Ibiden(JP)主要客戶 | 台灣ABF需求貢獻相對低", status: "balanced" },
          { name: "Broadcom", ticker: "AVGO", region: "🇺🇸", note: "Google TPU / Meta MTIA ASIC定製 | CoWoS ABF需求間接驅動 | 自家ASIC出貨量大", status: "tight" },
        ],
      },
      {
        name: "Hyperscaler AI 資本支出",
        nameEn: "Hyperscaler AI CapEx — Ultimate Demand",
        status: "critical",
        icon: "🌩",
        highlight: true,
        companies: [
          { name: "AWS / Amazon", ticker: "AMZN", region: "🇺🇸", note: "2026 AI CapEx $1,000億+ | Trainium3 / Inferentia AI晶片 ABF需求", status: "critical" },
          { name: "Microsoft Azure", ticker: "MSFT", region: "🇺🇸", note: "2026 CapEx $800億 | GB300/NVIDIA GPU ABF載板最大買家之一", status: "critical" },
          { name: "Google Cloud", ticker: "GOOGL", region: "🇺🇸", note: "2026 CapEx $750億 | Broadcom TPU ASIC採購 | ABF間接需求", status: "critical" },
          { name: "Meta", ticker: "META", region: "🇺🇸", note: "2026 CapEx $600-650億 | MTIA自研ASIC + NVIDIA GPU雙軌", status: "critical" },
        ],
      },
    ],
  },
  {
    id: "l1_materials",
    layer: "L1 關鍵材料",
    labelEn: "L1 — CRITICAL MATERIALS (SUPPLY BOTTLENECK)",
    color: "#1a2f1a",
    accent: "#22c55e",
    categories: [
      {
        name: "ABF 樹脂膜（全球獨家壟斷）",
        nameEn: "ABF Film — Global Monopoly Supplier",
        status: "critical",
        icon: "◈",
        highlight: true,
        companies: [
          { name: "味之素 Ajinomoto", ticker: "2802.T", region: "🇯🇵", note: "ABF Film全球唯一供應商 | 壟斷性定價能力 | 擴產週期3-4年 | 供應彈性低，超循環ABF Price Power極強 | 台灣三雄議價能力受限", status: "critical" },
        ],
      },
      {
        name: "T-Glass / 玻璃基板（2026瓶頸）",
        nameEn: "T-Glass Substrate — 2026 Supply Bottleneck",
        status: "critical",
        icon: "◉",
        highlight: true,
        companies: [
          { name: "AGC", ticker: "5201.T", region: "🇯🇵", note: "T-Glass玻璃基板主要供應商 | 2026產能緊缺 | 擴產時程2027H1見分曉 | 欣興(3037)產能瓶頸主因", status: "critical" },
          { name: "Corning", ticker: "GLW", region: "🇺🇸", note: "T-Glass備選供應商 | 擴產時程同樣落在2027H1 | 短期無法緩解欣興2026瓶頸", status: "tight" },
        ],
      },
      {
        name: "銅箔 / 玻纖布（輔助材料）",
        nameEn: "Copper Foil / Glass Cloth — Supporting Materials",
        status: "balanced",
        icon: "⬡",
        companies: [
          { name: "台光電子", ticker: "2383.TW", region: "🇹🇼", note: "高階銅箔基板（CCL）| ABF載板用特殊材料供應商 | 台灣本土供應鏈", status: "balanced" },
          { name: "南亞塑膠", ticker: "1303.TW", region: "🇹🇼", note: "玻纖布 + CCL | 南電(8046)母集團垂直整合 | 內部採購具成本優勢", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "l2_substrate",
    layer: "L2 ABF 載板製造",
    labelEn: "L2 — ABF SUBSTRATE MANUFACTURING",
    color: "#0f1f3a",
    accent: "#3b82f6",
    categories: [
      {
        name: "台灣三雄（全球 ~70% 市佔）",
        nameEn: "Taiwan Big Three — ~70% Global Market Share",
        status: "critical",
        icon: "★",
        highlight: true,
        companies: [
          { name: "欣興電子", ticker: "3037.TW", region: "🇹🇼", note: "全球最大ABF廠 ~35%市佔 | 2025 EPS NT$4.38 | AI營收30-40% | T-Glass瓶頸制約2026產能 | 廣福廠先進ABF利用率>80% | 泰國廠擴張中", status: "critical" },
          { name: "南亞電路板（南電）", ticker: "8046.TW", region: "🇹🇼", note: "ABF載板 #2 ~20%市佔 | 2025 EPS NT$3.0 | 產能利用率>90% | IC載板佔收入~85%（ABF 50-55%）| 台塑集團 | 2026E EPS NT$6-8（估）", status: "critical" },
          { name: "景碩科技", ticker: "3189.TW", region: "🇹🇼", note: "ABF+BT載板 ~15%市佔 | 2025 EPS NT$3.5 | 毛利率21.1% | 2026E EPS NT$6.3-8.0（YoY +80-130%）| 2026 CapEx NT$235億 | CoWoS基板特殊定位 | PEGATRON集團", status: "critical" },
        ],
      },
      {
        name: "日韓競爭廠商（全球 ~30% 市佔）",
        nameEn: "Japan / Korea Competitors — ~30% Share",
        status: "tight",
        icon: "⬢",
        companies: [
          { name: "Ibiden", ticker: "4062.T", region: "🇯🇵", note: "日本ABF載板龍頭 | Intel主要供應商 | 台灣三雄直接競爭者 | 日圓貶值增加競爭壓力", status: "tight" },
          { name: "Shinko Electric", ticker: "6967.T", region: "🇯🇵", note: "日本ABF #2 | 富士通集團 | CPU/GPU封裝載板 | 2025已被Ibiden超越", status: "tight" },
          { name: "Samsung Electro-Mech", ticker: "009150.KS", region: "🇰🇷", note: "韓國最大IC基板廠 | Samsung生態系封閉度高 | 對台灣三雄競爭相對有限", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "l3_packaging",
    layer: "L3 先進封裝",
    labelEn: "L3 — ADVANCED PACKAGING (CoWoS / SoIC)",
    color: "#0f1f35",
    accent: "#0ea5e9",
    categories: [
      {
        name: "CoWoS 先進封裝（ABF需求乘數）",
        nameEn: "CoWoS / SoIC Advanced Packaging — ABF Demand Multiplier",
        status: "critical",
        icon: "▣",
        highlight: true,
        companies: [
          { name: "台積電 TSMC", ticker: "2330.TW", region: "🇹🇼", note: "CoWoS-S/L/R量產 | GB300每顆CoWoS需2塊ABF載板（需求乘數 ×2）| SoIC 3D封裝 | HBM4整合 | 欣興/景碩ABF認證採購端", status: "critical" },
        ],
      },
      {
        name: "OSAT 封裝測試",
        nameEn: "OSAT — Outsourced Semiconductor Assembly & Test",
        status: "tight",
        icon: "◐",
        companies: [
          { name: "日月光 ASE", ticker: "3711.TW", region: "🇹🇼", note: "先進封裝測試代工 | TSMC CoWoS補位廠 | 2026產能擴張中 | ABF載板需求間接受益", status: "tight" },
          { name: "Amkor", ticker: "AMKR", region: "🇺🇸", note: "全球OSAT #3 | 先進封裝代工 | ABF載板需求間接受益 | 日韓廠補位", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "l4_cloud",
    layer: "L4 AI 基礎設施",
    labelEn: "L4 — AI INFRASTRUCTURE / SERVER OEM",
    color: "#0a1a20",
    accent: "#10b981",
    categories: [
      {
        name: "AI 伺服器 ODM / OEM",
        nameEn: "AI Server ODM / OEM",
        status: "critical",
        icon: "◇",
        highlight: true,
        companies: [
          { name: "廣達電腦", ticker: "2382.TW", region: "🇹🇼", note: "AI伺服器ODM龍頭 | NVIDIA GB200 NVL72 主要組裝廠 | ABF載板間接需求終端", status: "critical" },
          { name: "緯穎科技", ticker: "6669.TW", region: "🇹🇼", note: "AI伺服器ODM #2 | Meta/AWS主要供應商 | GB300系列量產 ABF需求傳導", status: "tight" },
          { name: "Super Micro (SMCI)", ticker: "SMCI", region: "🇺🇸", note: "AI伺服器品牌廠 | NVIDIA GB200直接客戶 | US本地端AI Infra受益", status: "tight" },
        ],
      },
      {
        name: "HBM / 記憶體封裝（載板共需求）",
        nameEn: "HBM Memory — Co-Located ABF Demand",
        status: "tight",
        icon: "⬟",
        companies: [
          { name: "SK Hynix", ticker: "000660.KS", region: "🇰🇷", note: "HBM4 全球龍頭 | CoWoS HBM整合需DRAM封裝載板 | 南電BT載板潛在客戶", status: "tight" },
          { name: "Micron", ticker: "MU", region: "🇺🇸", note: "HBM3E量產中 | 2026 HBM4目標 | CoWoS整合 ABF需求間接受益", status: "balanced" },
        ],
      },
    ],
  },
];

// ── 關鍵驅動因子 ─────────────────────────────────────────────
const KEY_DRIVERS = [
  {
    id: "ai_area_expansion",
    title: "AI GPU ABF 面積需求 8-12x 超循環",
    titleEn: "AI GPU ABF Area Demand 8-12x Super-Cycle",
    icon: "⚡",
    color: "#3b82f6",
    description: "NVIDIA GB200/B300 每顆GPU所需ABF載板面積是傳統CPU的8-12倍。台灣三雄（欣興+南電+景碩）合計全球市佔~70%，且AI GPU認證壁壘高（18-24個月），新進者難以搶單。超循環核心受益者。",
    metric: "ABF面積需求 8-12x vs CPU",
    impact: "極高（系統性）",
  },
  {
    id: "tglass_bottleneck",
    title: "T-Glass 玻璃基板供應瓶頸",
    titleEn: "T-Glass Supply Bottleneck — Upside Cap Risk",
    icon: "⚠",
    color: "#ef4444",
    description: "欣興（3037）廣福廠先進ABF所需T-Glass由AGC/Corning供應，2026年產能緊缺，制約欣興產能上限。AGC擴產時程2027H1才見分曉。T-Glass是欣興個股最核心的風險與催化劑觀察點。",
    metric: "2027H1 AGC擴產見分曉",
    impact: "高（欣興個股）",
  },
  {
    id: "abf_film_monopoly",
    title: "ABF Film 味之素全球壟斷",
    titleEn: "Ajinomoto ABF Film Global Monopoly",
    icon: "🏭",
    color: "#f59e0b",
    description: "味之素是ABF Film全球唯一供應商，替代品2030年前不可能出現。超循環中ABF Film議價能力極強，對台灣三雄成本端有壓縮效果，但下游AI GPU強勁需求可讓載板廠轉嫁漲價——最終毛利率改善仍取決於需求強度。",
    metric: "全球獨家，替代品2030+",
    impact: "中（成本端結構性）",
  },
  {
    id: "taiwan_trio_moat",
    title: "台灣三雄 ~70% 全球市佔護城河",
    titleEn: "Taiwan Big Three — ~70% Global Market Share Moat",
    icon: "🛡",
    color: "#22c55e",
    description: "欣興~35%、南電~20%、景碩~15%，合計~70%全球ABF市佔。AI GPU客戶認證週期18-24個月，切換成本極高。日本Ibiden等競爭者無法在短期內搶佔台灣三雄AI GPU訂單份額。台灣三雄護城河在超循環中持續加寬。",
    metric: "台灣三雄全球市佔 ~70%",
    impact: "極高（結構性）",
  },
  {
    id: "cowos_demand_multiplier",
    title: "CoWoS 擴產傳導 ABF 需求乘數",
    titleEn: "CoWoS Expansion — ABF Demand Multiplier x2",
    icon: "📈",
    color: "#10b981",
    description: "TSMC CoWoS-L放量，GB300每顆先進封裝需2塊ABF載板（×2乘數效應）。TSMC CoWoS產能從2024到2026翻倍，直接傳導欣興/南電/景碩的ABF訂單。CoWoS擴產速度即ABF需求速度的代理指標。",
    metric: "GB300 CoWoS每顆 ×2 ABF",
    impact: "極高（直接需求）",
  },
  {
    id: "hyperscaler_capex",
    title: "Hyperscaler AI CapEx $3,000 億超循環",
    titleEn: "Hyperscaler AI CapEx $300B Super-Cycle",
    icon: "🤖",
    color: "#a855f7",
    description: "AWS/Azure/GCP/Meta 2026年合計AI CapEx超$3,000億，YoY +40%+。AI GPU採購直接拉動ABF載板需求。任一大廠CapEx指引YoY降幅>10%為ABF全鏈警戒訊號。DeepSeek類AI效率突破為尾部風險（Bear情境必測）。",
    metric: "CSP CapEx $3,000億+",
    impact: "極高（系統性）",
  },
];

// ── 法說快照資料 ─────────────────────────────────────────────
const PRICE_SIGNALS = [
  { product: "欣興 3037", price: "EPS NT$4.38", change: "+13.8% YoY營收", period: "2025全年", status: "critical", note: "AI相關30-40%，T-Glass瓶頸制約2026" },
  { product: "南電 8046", price: "EPS NT$3.0",  change: "+24.4% YoY營收", period: "2025全年", status: "critical", note: "產能>90%，IC載板佔85%，ABF 50-55%" },
  { product: "景碩 3189", price: "EPS NT$3.5",  change: "+28.8% YoY營收", period: "2025全年", status: "critical", note: "毛利率21.1%，2026E EPS NT$6.3-8.0" },
  { product: "景碩 2026E EPS", price: "NT$6.3-8.0", change: "YoY +80-130%", period: "法人共識", status: "critical", note: "2026 CapEx NT$235億，ABF擴廠" },
  { product: "ABF面積需求", price: "8-12x",     change: "vs 傳統 CPU",   period: "AI GPU世代", status: "critical", note: "超循環核心驅動因子" },
  { product: "台灣三雄市佔", price: "~70%",     change: "全球ABF市場",   period: "2025",      status: "critical", note: "欣興35% / 南電20% / 景碩15%" },
];

// ── 狀態顏色設定 ─────────────────────────────────────────────
const STATUS = {
  critical: { bg: "rgba(239,68,68,0.15)", border: "#ef4444", dot: "#ef4444", label: "極度緊張", text: "#fca5a5" },
  tight:    { bg: "rgba(245,158,11,0.12)", border: "#f59e0b", dot: "#f59e0b", label: "供給偏緊", text: "#fcd34d" },
  balanced: { bg: "rgba(16,185,129,0.1)",  border: "#10b981", dot: "#10b981", label: "供需平衡", text: "#6ee7b7" },
  loose:    { bg: "rgba(99,102,241,0.1)",  border: "#6366f1", dot: "#6366f1", label: "供給充裕", text: "#a5b4fc" },
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

function CompanyCard({ company }) {
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

function CategoryBlock({ cat }) {
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
        borderBottom: "1px solid rgba(255,255,255,0.07)",
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
      {cat.companies.map((c, i) => <CompanyCard key={i} company={c} />)}
    </div>
  );
}

function LayerPanel({ layer, isActive, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        background: isActive
          ? `linear-gradient(135deg, ${layer.color} 0%, rgba(10,30,60,0.9) 100%)`
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
      <div style={{ fontSize: 11, color: layer.accent, fontFamily: "monospace", letterSpacing: "0.1em", marginBottom: 2 }}>
        {layer.labelEn}
      </div>
      <div style={{ fontSize: 14, fontWeight: 800, color: isActive ? "#f1f5f9" : "#94a3b8", fontFamily: "'IBM Plex Sans', sans-serif" }}>
        {layer.layer}
      </div>
      <div style={{ fontSize: 10, color: "#475569", marginTop: 2 }}>
        {layer.categories.length} 品類 · {layer.categories.reduce((a, c) => a + c.companies.length, 0)} 廠商
      </div>
    </button>
  );
}

// ── 主組件 ────────────────────────────────────────────────────
export default function PCBSubstrateSupplyChainMap() {
  const [activeLayer, setActiveLayer] = useState("l2_substrate");
  const [activeTab, setActiveTab] = useState("chain");

  const currentLayer = SUPPLY_CHAIN.find(l => l.id === activeLayer);

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #020617 0%, #080d1f 40%, #04101a 100%)",
      color: "#e2e8f0",
      fontFamily: "'IBM Plex Sans', system-ui, sans-serif",
      padding: "0",
    }}>
      {/* ── Header ── */}
      <div style={{
        background: "linear-gradient(90deg, rgba(59,130,246,0.25) 0%, rgba(16,185,129,0.1) 100%)",
        borderBottom: "1px solid rgba(59,130,246,0.2)",
        padding: "20px 24px 16px",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <div style={{ width: 4, height: 32, background: "linear-gradient(180deg, #3b82f6, #10b981)", borderRadius: 2 }} />
              <div>
                <h1 style={{
                  fontSize: 22,
                  fontWeight: 900,
                  margin: 0,
                  background: "linear-gradient(90deg, #3b82f6, #0ea5e9, #10b981)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: "-0.5px",
                }}>
                  PCB 載板（IC 基板）供應鏈全景圖
                </h1>
                <p style={{ margin: 0, fontSize: 11, color: "#64748b", letterSpacing: "0.08em" }}>
                  ABF SUBSTRATE SUPPLY CHAIN · 2026 MAR UPDATE
                </p>
              </div>
            </div>
            {/* 關鍵數字摘要 */}
            <div style={{ display: "flex", gap: 16, marginTop: 10, flexWrap: "wrap" }}>
              {[
                { label: "ABF面積需求", value: "8-12x",     color: "#3b82f6" },
                { label: "台灣三雄市佔", value: "~70%",     color: "#ef4444" },
                { label: "景碩 2026E EPS", value: "+80-130%", color: "#10b981" },
                { label: "南電產能",      value: ">90%",    color: "#0ea5e9" },
                { label: "ABF Film",     value: "全球壟斷", color: "#f59e0b" },
              ].map(m => (
                <div key={m.label} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: 16, fontWeight: 900, color: m.color, fontFamily: "monospace" }}>{m.value}</div>
                  <div style={{ fontSize: 10, color: "#64748b" }}>{m.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
            {Object.entries(STATUS).map(([key, s]) => (
              <div key={key} style={{
                display: "flex", alignItems: "center", gap: 5,
                background: s.bg, border: `1px solid ${s.border}`,
                borderRadius: 5, padding: "4px 8px", fontSize: 11,
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
            { key: "chain",   label: "🔗 供應鏈層級" },
            { key: "drivers", label: "⚡ 關鍵驅動因子" },
            { key: "signals", label: "📊 法說快照" },
          ].map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
              background: activeTab === tab.key ? "rgba(59,130,246,0.2)" : "transparent",
              border: activeTab === tab.key ? "1px solid rgba(59,130,246,0.5)" : "1px solid transparent",
              borderRadius: 6, padding: "6px 14px", cursor: "pointer",
              color: activeTab === tab.key ? "#3b82f6" : "#64748b",
              fontSize: 12, fontWeight: activeTab === tab.key ? 700 : 400,
              transition: "all 0.15s",
            }}>{tab.label}</button>
          ))}
        </div>
      </div>

      {/* ── 主內容區 ── */}
      <div style={{ padding: "20px 24px" }}>

        {/* ── Tab: 供應鏈層級 ── */}
        {activeTab === "chain" && (
          <div style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 16 }}>
            {/* 左側層級導航 */}
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontSize: 11, color: "#475569", fontFamily: "monospace", letterSpacing: "0.1em", marginBottom: 4, paddingLeft: 4 }}>
                SUPPLY CHAIN LAYERS
              </div>
              {SUPPLY_CHAIN.map(layer => (
                <LayerPanel key={layer.id} layer={layer} isActive={activeLayer === layer.id} onClick={() => setActiveLayer(layer.id)} />
              ))}
              {/* 訂單流向說明 */}
              <div style={{
                marginTop: 12,
                background: "rgba(59,130,246,0.05)",
                border: "1px solid rgba(59,130,246,0.15)",
                borderRadius: 8,
                padding: "10px 12px",
              }}>
                <div style={{ fontSize: 11, color: "#3b82f6", fontWeight: 700, marginBottom: 6 }}>訂單流向</div>
                {[
                  { arrow: "NVIDIA/AMD → 3037/8046/3189", note: "ABF載板直接採購（TSMC CoWoS）" },
                  { arrow: "TSMC CoWoS → ABF三雄",        note: "先進封裝基板（GB300 ×2塊）" },
                  { arrow: "Ajinomoto → ABF三雄",         note: "ABF Film原料（壟斷供應）" },
                  { arrow: "AGC/Corning → 3037",          note: "T-Glass玻璃基板（瓶頸）" },
                  { arrow: "Hyperscaler CapEx → 全鏈",    note: "AI伺服器CapEx需求傳導" },
                ].map((r, i) => (
                  <div key={i} style={{ marginBottom: 4 }}>
                    <div style={{ fontSize: 11, color: "#e2e8f0", fontFamily: "monospace" }}>{r.arrow}</div>
                    <div style={{ fontSize: 10, color: "#64748b", paddingLeft: 4 }}>{r.note}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 右側品類展示 */}
            <div>
              {currentLayer && (
                <>
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ fontSize: 11, color: currentLayer.accent, fontFamily: "monospace", letterSpacing: "0.1em" }}>
                      {currentLayer.labelEn}
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 900, color: "#f1f5f9", marginTop: 2 }}>
                      {currentLayer.layer}
                    </div>
                  </div>
                  <div style={{ columns: currentLayer.categories.length > 2 ? 2 : 1, gap: 12 }}>
                    {currentLayer.categories.map((cat, i) => (
                      <div key={i} style={{ breakInside: "avoid" }}>
                        <CategoryBlock cat={cat} />
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {/* ── Tab: 關鍵驅動因子 ── */}
        {activeTab === "drivers" && (
          <div>
            <div style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
              影響 ABF 載板供應鏈投資邏輯的關鍵結構性因子
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: 14 }}>
              {KEY_DRIVERS.map(d => (
                <div key={d.id} style={{
                  background: "rgba(15,23,42,0.7)",
                  border: `1px solid ${d.color}40`,
                  borderLeft: `3px solid ${d.color}`,
                  borderRadius: 8,
                  padding: "14px 16px",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
                    <span style={{ fontSize: 20 }}>{d.icon}</span>
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 800, color: "#f1f5f9" }}>{d.title}</div>
                      <div style={{ fontSize: 10, color: "#64748b" }}>{d.titleEn}</div>
                    </div>
                  </div>
                  <p style={{ fontSize: 12, color: "#94a3b8", lineHeight: 1.6, margin: "0 0 10px" }}>{d.description}</p>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{
                      fontSize: 11, fontWeight: 700, fontFamily: "monospace",
                      color: d.color, background: `${d.color}15`,
                      border: `1px solid ${d.color}40`,
                      padding: "3px 8px", borderRadius: 4,
                    }}>{d.metric}</span>
                    <span style={{ fontSize: 11, color: "#64748b" }}>衝擊：{d.impact}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Tab: 法說快照 ── */}
        {activeTab === "signals" && (
          <div>
            <div style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
              2025全年財務數據 + 關鍵產業指標（資料來源：法說會公開資訊 / CLAUDE.md 基準）
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
              {PRICE_SIGNALS.map((s, i) => {
                const st = STATUS[s.status] || STATUS.balanced;
                const isNeg = s.change.includes("⚠️") || s.change.startsWith("-");
                return (
                  <div key={i} style={{
                    background: st.bg,
                    border: `1px solid ${st.border}`,
                    borderRadius: 8,
                    padding: "12px 14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 6,
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <div style={{ fontSize: 14, fontWeight: 800, color: "#f1f5f9" }}>{s.product}</div>
                      <StatusDot status={s.status} size={8} />
                    </div>
                    <div style={{ fontSize: 20, fontWeight: 900, color: st.dot, fontFamily: "monospace" }}>
                      {s.price}
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{
                        fontSize: 13, fontWeight: 700, fontFamily: "monospace",
                        color: isNeg ? "#fca5a5" : "#6ee7b7",
                      }}>{s.change}</span>
                      <span style={{ fontSize: 10, color: "#64748b" }}>{s.period}</span>
                    </div>
                    <div style={{ fontSize: 11, color: st.text, marginTop: 2 }}>{s.note}</div>
                  </div>
                );
              })}
            </div>

            {/* 里程碑時間軸 */}
            <div style={{ marginTop: 24 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#94a3b8", marginBottom: 12 }}>
                2026–2028 關鍵里程碑
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  { time: "2026 Q1–Q2", event: "GB300/B300 量產出貨，ABF訂單能見度確認",    ticker: "欣興/南電/景碩 季報確認",       color: "#3b82f6" },
                  { time: "2026 Q2",    event: "景碩 Q1 法說：HPC 佔比能否突破 30%",       ticker: "3189 關鍵財報觀察點",            color: "#10b981" },
                  { time: "2026 H1",    event: "南電 高層數 ABF（30層+）客戶驗收",          ticker: "8046 毛利率改善訊號",            color: "#0ea5e9" },
                  { time: "2026 H2",    event: "欣興 泰國廠新產能貢獻度確認",               ticker: "3037 產能擴張進度",              color: "#3b82f6" },
                  { time: "2026 H2",    event: "景碩 ABF 擴廠（NT$235億）新產能開出",       ticker: "3189 折舊攤提 vs 毛利率觀察",    color: "#10b981" },
                  { time: "2027 H1",    event: "AGC/Corning T-Glass 擴產見分曉",           ticker: "3037 T-Glass瓶頸能否解除",       color: "#ef4444" },
                  { time: "2027",       event: "Glass Substrate 技術成熟度確認",            ticker: "欣興/南電研發進展",              color: "#f59e0b" },
                  { time: "2027–2028",  event: "HBM4 大量出貨，CoWoS ABF需求再乘數",       ticker: "全鏈第二波超循環確認點",          color: "#a855f7" },
                ].map((m, i) => (
                  <div key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <div style={{
                      minWidth: 80, fontSize: 11, fontFamily: "monospace",
                      color: m.color, fontWeight: 700, paddingTop: 2,
                    }}>{m.time}</div>
                    <div style={{ width: 2, minHeight: 32, background: `${m.color}40`, borderRadius: 1, flexShrink: 0, marginTop: 4 }} />
                    <div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>{m.event}</div>
                      <div style={{ fontSize: 11, color: "#64748b" }}>{m.ticker}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Footer ── */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,0.06)",
        padding: "12px 24px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 8,
      }}>
        <span style={{ fontSize: 11, color: "#334155" }}>
          PCB 載板供應鏈全景圖 · 資料截止 2026年3月29日 · 僅供個人投資研究參考
        </span>
        <span style={{ fontSize: 11, color: "#334155", fontFamily: "monospace" }}>
          資料來源：法說會公開資訊（2026Q4）· winvest.tw · CLAUDE.md 基準
        </span>
      </div>
    </div>
  );
}
