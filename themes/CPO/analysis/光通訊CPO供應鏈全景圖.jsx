import { useState } from "react";

/* ============================================================
   光通訊 CPO 供應鏈全景圖
   CPO Optical Communications Supply Chain Panorama Map
   更新日期: 2026年3月 | 資料基準: 2026年2月月營收 / 2025Q4法說
   ============================================================ */

// ── 供應鏈資料 ─────────────────────────────────────────────
const SUPPLY_CHAIN = [
  {
    id: "demand",
    layer: "需求端",
    labelEn: "DEMAND — US HYPERSCALER & CHIP",
    color: "#1a1040",
    accent: "#a855f7",
    categories: [
      {
        name: "AI 晶片 / ASIC 設計",
        nameEn: "AI Chip / CPO ASIC Design",
        status: "critical",
        icon: "⬛",
        highlight: true,
        companies: [
          { name: "NVIDIA", ticker: "NVDA", region: "🇺🇸", note: "$20億投資LITE + $20億投資COHR | Spectrum-X CPO 架構定義者", status: "critical" },
          { name: "Broadcom", ticker: "AVGO", region: "🇺🇸", note: "CPO ASIC + SiPh | 眾達-KY (4977) ELS 直接客戶", status: "critical" },
          { name: "Marvell (MRVL)", ticker: "MRVL", region: "🇺🇸", note: "SiPh 光引擎 IC | 華星光通 (4979) 客戶佔比 85-95%", status: "critical" },
          { name: "MACOM (MTSI)", ticker: "MTSI", region: "🇺🇸", note: "類比光子前端 IC | 1.6T 驅動晶片 | FQ1 2026 YoY +24.5%", status: "tight" },
        ],
      },
      {
        name: "雷射晶片廠（台灣 L1 直接客戶）",
        nameEn: "Laser Chip Manufacturer — Direct Buyer of TW L1",
        status: "critical",
        icon: "◈",
        highlight: true,
        companies: [
          { name: "Lumentum (LITE)", ticker: "LITE", region: "🇺🇸", note: "CW Laser 晶片龍頭 | EML 全球市佔 50-60% | 直接採購 3081/2455 InP 磊晶 | NVIDIA $20億投資 | 北卡第5座 InP fab 2028量產（UHP）", status: "critical" },
          { name: "Coherent (COHR)", ticker: "COHR", region: "🇺🇸", note: "垂直整合全鏈廠 | FY25 $58.1億 | 收發器市佔~25% | 有自有材料部門，較少外購台灣InP | NVIDIA $20億投資", status: "tight" },
        ],
      },
      {
        name: "全鏈組裝代工",
        nameEn: "Full-Chain Assembly EMS",
        status: "tight",
        icon: "◇",
        companies: [
          { name: "Fabrinet (FN)", ticker: "FN", region: "🇺🇸", note: "光通訊全鏈最終組裝 | 新廠200萬sq ft (+50%產能) | 2026年增28.5%預估", status: "tight" },
          { name: "AAOI", ticker: "AAOI", region: "🇺🇸", note: "LPO 垂直整合收發器 | Microsoft 主要供應商 | CPO vs LPO 路線對沖標的", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "l1_epitaxy",
    layer: "L1 磊晶層",
    labelEn: "L1 — InP / GaAs EPITAXY",
    color: "#0f2a3f",
    accent: "#06b6d4",
    categories: [
      {
        name: "InP CW Laser 磊晶",
        nameEn: "InP CW Laser Epitaxy — Highest Barrier",
        status: "critical",
        icon: "⬡",
        highlight: true,
        companies: [
          { name: "聯亞光電", ticker: "3081.TWO", region: "🇹🇼", note: "台灣最大InP CW Laser磊晶 | 2月YoY +91.4% | 2026新增美系CSP客戶 | LITE直接供應商 | MOCVD技術壁壘", status: "critical" },
          { name: "全新光電", ticker: "2455.TW", region: "🇹🇼", note: "台灣唯一InP+GaAs雙平台 | 2025EPS估NT$3.0-3.5 | 2026EPS估NT$5.5-6.5 | InP基板已多元化（住友/Freiberger）", status: "critical" },
          { name: "IntelliEPI (iET)", ticker: "私", region: "🇹🇼", note: "LITE外包磊晶接單廠（TrendForce確認）| 產業under-shipping 25-30%帶動外包需求", status: "tight" },
        ],
      },
      {
        name: "InP 基板供應（上游材料）",
        nameEn: "InP Substrate — Upstream Material",
        status: "tight",
        icon: "⬟",
        companies: [
          { name: "住友電工", ticker: "5802.T", region: "🇯🇵", note: "InP基板主要供應商 | 全新光電雙供應商策略之一", status: "tight" },
          { name: "Freiberger", ticker: "私", region: "🇩🇪", note: "InP基板 | 全新光電第二供應商 | 出口管制2025Q3解除", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "l2_wafer",
    layer: "L2 晶圓代工",
    labelEn: "L2 — WAFER FOUNDRY / MODULE",
    color: "#0f2030",
    accent: "#0ea5e9",
    categories: [
      {
        name: "GaAs 晶圓代工",
        nameEn: "GaAs Wafer Foundry",
        status: "tight",
        icon: "⬢",
        companies: [
          { name: "穩懋半導體", ticker: "3105.TWO", region: "🇹🇼", note: "全球最大GaAs純代工 | 2月YoY +25.9% | LITE一階客戶（GaAs部分）| 手機PA佔~70%，光電CPO約15-20% | 二階受益定位", status: "tight" },
          { name: "宏捷科", ticker: "8086.TWO", region: "🇹🇼", note: "GaAs晶圓代工 #2 | 光電元件晶圓補位廠", status: "balanced" },
        ],
      },
      {
        name: "光收發器模組",
        nameEn: "Optical Transceiver Module",
        status: "tight",
        icon: "▤",
        companies: [
          { name: "波若威", ticker: "3163.TWO", region: "🇹🇼", note: "光收發器模組 | 2月YoY +5.3% | 2025全年NT$22.26億 | CPO+傳統插拔並行觀察 | 觀察名單", status: "tight" },
        ],
      },
      {
        name: "矽光子 SiPh 晶圓代工",
        nameEn: "Silicon Photonics Wafer",
        status: "critical",
        icon: "★",
        highlight: true,
        companies: [
          { name: "台積電 TSMC", ticker: "2330.TW", region: "🇹🇼", note: "COUPE 平台 SiPh 製造 | 上詮 (3363) 唯一認證 FAU 供應商 | CPO 最重要的代工方", status: "critical" },
        ],
      },
    ],
  },
  {
    id: "l3_packaging",
    layer: "L3 封裝／連接",
    labelEn: "L3 — PACKAGING / CONNECTIVITY",
    color: "#0d1f35",
    accent: "#3b82f6",
    categories: [
      {
        name: "FAU 光纖陣列（TSMC 認證）",
        nameEn: "FAU — Fiber Array Unit (COUPE Certified)",
        status: "critical",
        icon: "◉",
        highlight: true,
        companies: [
          { name: "上詮光纖", ticker: "3363.TWO", region: "🇹🇼", note: "TSMC COUPE 唯一認證 | 2025全年NT$18.9億 | 1.6T FAU系統廠驗證進行中（2026 Q2 結果）| 轉換成本2-3年護城河", status: "critical" },
        ],
      },
      {
        name: "CW Laser 後段封裝",
        nameEn: "CW Laser Back-End Packaging",
        status: "tight",
        icon: "◐",
        companies: [
          { name: "華星光通", ticker: "4979.TWO", region: "🇹🇼", note: "CW Laser後段封裝 | Marvell客戶85-95% ⚠️ | 2月YoY -10.0% MoM -20.1% | 族群唯一負成長 | 追蹤Marvell外包策略", status: "tight" },
        ],
      },
      {
        name: "高芯數光纖連接器",
        nameEn: "High-Density Fiber Connector",
        status: "tight",
        icon: "◎",
        companies: [
          { name: "光聖", ticker: "6442.TW", region: "🇹🇼", note: "高芯數光纖跳接線（1000芯+）| 2月YoY +44.1% | 2025全年NT$105億 | IDC大規模佈線直接受益", status: "tight" },
        ],
      },
      {
        name: "ELS 雷射光源組裝",
        nameEn: "ELS — External Light Source Assembly",
        status: "balanced",
        icon: "◑",
        companies: [
          { name: "眾達-KY", ticker: "4977.TW", region: "🇹🇼", note: "Broadcom CPO ELS唯一供應 ⚠️ | 2月YoY -17.4% MoM +169% | 2025全年NT$10.75億 | 轉正關鍵：2026H2 Broadcom放量確認", status: "balanced" },
        ],
      },
    ],
  },
  {
    id: "l4_system",
    layer: "L4 系統層",
    labelEn: "L4 — SYSTEM INTEGRATION",
    color: "#0a1a28",
    accent: "#10b981",
    categories: [
      {
        name: "CPO 交換器系統",
        nameEn: "CPO Switch System",
        status: "critical",
        icon: "▣",
        highlight: true,
        companies: [
          { name: "智邦", ticker: "2345.TW", region: "🇹🇼", note: "800G CPO交換器量產 | 2月YoY +82.7% MoM +9.6% | 月營收NT$235.83億 | 市值NT$9,250億 | Hyperscaler直採ODM", status: "critical" },
          { name: "Arista Networks", ticker: "ANET", region: "🇺🇸", note: "企業級AI網路 | 智邦ODM競爭對手（高端）", status: "tight" },
        ],
      },
    ],
  },
  {
    id: "test",
    layer: "測試層",
    labelEn: "TEST — CROSS-LAYER PROBE CARD",
    color: "#1a1a10",
    accent: "#eab308",
    categories: [
      {
        name: "CPO 量產測試（Probe Card）",
        nameEn: "CPO Mass Production Test",
        status: "tight",
        icon: "⚙",
        companies: [
          { name: "旺矽", ticker: "6223.TWO", region: "🇹🇼", note: "MEMS Probe Card龍頭 | 2月YoY +45.5% | 2025 EPS NT$33.49 | 2026目標+40% | 橫跨L1/L2/L3每層晶片測試受益", status: "tight" },
          { name: "FormFactor", ticker: "FORM", region: "🇺🇸", note: "全球Probe Card #1 | 旺矽主要競爭對手", status: "balanced" },
        ],
      },
    ],
  },
];

// ── 關鍵驅動因子 ─────────────────────────────────────────────
const KEY_DRIVERS = [
  {
    id: "nvidia_investment",
    title: "NVIDIA $40億光通訊押注",
    titleEn: "NVIDIA $4B Photonics Investment",
    icon: "⚡",
    color: "#a855f7",
    description: "2026年3月NVIDIA宣布：$20億投資Lumentum + $20億投資Coherent，並附帶多年採購承諾。史上最大規模光通訊戰略鎖定，直接確保LITE/COHR供應鏈優先權，上詮認證、3081/2455磊晶需求同步受益。",
    metric: "NVIDIA $40億鎖倉",
    impact: "極高",
  },
  {
    id: "cpo_penetration",
    title: "CPO 滲透率從 <1% 突破 10%",
    titleEn: "CPO Penetration 10% Inflection",
    icon: "📈",
    color: "#06b6d4",
    description: "2026年為CPO商業量產元年。TSMC COUPE平台Q1-Q2量產導入，800G+ 收發器全球出貨從24M飆升至63M（YoY +163%）。CPO滲透率突破10%是結構性訊號，全鏈估值重評觸發點。",
    metric: "800G出貨 +163% YoY",
    impact: "極高",
  },
  {
    id: "lite_fab_expansion",
    title: "LITE InP 自建擴產時程",
    titleEn: "LITE InP Fab Self-Build Risk",
    icon: "🏭",
    color: "#f59e0b",
    description: "LITE 2025-2026年透過現有4座fab追加+50% InP產能，但仍under-shipping 25-30%，近中期外購需求持續。北卡第5座fab（UHP專用）2028年才量產，CW Laser外購不受影響。2028年後需追蹤是否擴展至CW Laser品項。",
    metric: "2028年前外購需求安全",
    impact: "中（2028後追蹤）",
  },
  {
    id: "marvell_strategy",
    title: "Marvell SiPh 外包策略",
    titleEn: "Marvell SiPh Outsourcing Risk",
    icon: "⚠",
    color: "#ef4444",
    description: "華星光通（4979）客戶高度集中Marvell（85-95%）。若Marvell自研SiPh光引擎比例提升或改變封裝外包安排，4979業務能見度直接下滑。2月YoY -10%為警示訊號，需法說確認原因。",
    metric: "4979 2月YoY -10% ⚠️",
    impact: "高（4979個股）",
  },
  {
    id: "hyperscaler_capex",
    title: "Hyperscaler AI CapEx 能見度",
    titleEn: "Hyperscaler AI CapEx Visibility",
    icon: "🤖",
    color: "#10b981",
    description: "AWS/Azure/GCP 2026年合計AI CapEx預估超$6,000億，年增40%+。CPO全鏈需求直接由Hyperscaler決定。任一大廠CapEx指引YoY降幅>10%為全鏈警戒訊號。DeepSeek類效率突破為尾部風險。",
    metric: "CSP CapEx $6000億+",
    impact: "極高（系統性）",
  },
  {
    id: "lpo_competition",
    title: "LPO vs CPO 路線競爭",
    titleEn: "LPO vs CPO Technology Race",
    icon: "🔀",
    color: "#8b5cf6",
    description: "LPO（Linear-drive Pluggable Optics）以低功耗、低成本的可插拔方案競爭CPO市場。AAOI為LPO代表廠（Microsoft供應商）。若LPO滲透率超預期，將侵蝕CPO供應鏈市佔。短期兩路線並行，2027年後見分曉。",
    metric: "觀察AAOI vs CPO份額",
    impact: "中（結構性對沖）",
  },
];

// ── 關鍵指標面板 ─────────────────────────────────────────────
const PRICE_SIGNALS = [
  { product: "3081 聯亞光電", price: "NT$1,720", change: "+91.4% YoY", period: "2026年2月月營收", status: "critical", note: "族群最強成長" },
  { product: "2345 智邦", price: "NT$1,655", change: "+82.7% YoY", period: "2026年2月月營收", status: "critical", note: "系統層龍頭" },
  { product: "6442 光聖", price: "NT$2,115", change: "+44.1% YoY", period: "2026年2月月營收", status: "tight", note: "連接材料強勁" },
  { product: "6223 旺矽", price: "NT$3,665", change: "+45.5% YoY", period: "2026年2月月營收", status: "tight", note: "測試層超預期" },
  { product: "3363 上詮光纖", price: "NT$642", change: "+27.7% YoY", period: "2026年2月月營收", status: "tight", note: "等待Q2驗證結果" },
  { product: "4979 華星光通", price: "NT$396.5", change: "-10.0% YoY ⚠️", period: "2026年2月月營收", status: "balanced", note: "族群唯一負成長" },
  { product: "LITE Q2目標", price: "$600M+", change: "+季營收目標", period: "2026 Q2", status: "critical", note: "3081/2455訂單確認" },
  { product: "800G收發器出貨", price: "63M units", change: "+163% YoY", period: "2026全年預估", status: "critical", note: "全鏈需求驗證" },
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
export default function CPOSupplyChainMap() {
  const [activeLayer, setActiveLayer] = useState("l1_epitaxy");
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
        background: "linear-gradient(90deg, rgba(6,182,212,0.25) 0%, rgba(168,85,247,0.1) 100%)",
        borderBottom: "1px solid rgba(6,182,212,0.2)",
        padding: "20px 24px 16px",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <div style={{ width: 4, height: 32, background: "linear-gradient(180deg, #06b6d4, #a855f7)", borderRadius: 2 }} />
              <div>
                <h1 style={{
                  fontSize: 22,
                  fontWeight: 900,
                  margin: 0,
                  background: "linear-gradient(90deg, #06b6d4, #3b82f6, #a855f7)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  letterSpacing: "-0.5px",
                }}>
                  光通訊 CPO 供應鏈全景圖
                </h1>
                <p style={{ margin: 0, fontSize: 11, color: "#64748b", letterSpacing: "0.08em" }}>
                  CPO OPTICAL COMMUNICATIONS SUPPLY CHAIN · 2026 MAR UPDATE
                </p>
              </div>
            </div>
            {/* 關鍵數字摘要 */}
            <div style={{ display: "flex", gap: 16, marginTop: 10, flexWrap: "wrap" }}>
              {[
                { label: "NVIDIA 投資", value: "$40億", color: "#a855f7" },
                { label: "800G出貨增長", value: "+163%", color: "#ef4444" },
                { label: "聯亞 YoY", value: "+91.4%", color: "#06b6d4" },
                { label: "智邦 YoY", value: "+82.7%", color: "#10b981" },
                { label: "CPO元年", value: "2026", color: "#f59e0b" },
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
            { key: "signals", label: "📊 月營收快照" },
          ].map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
              background: activeTab === tab.key ? "rgba(6,182,212,0.2)" : "transparent",
              border: activeTab === tab.key ? "1px solid rgba(6,182,212,0.5)" : "1px solid transparent",
              borderRadius: 6, padding: "6px 14px", cursor: "pointer",
              color: activeTab === tab.key ? "#06b6d4" : "#64748b",
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
                background: "rgba(6,182,212,0.05)",
                border: "1px solid rgba(6,182,212,0.15)",
                borderRadius: 8,
                padding: "10px 12px",
              }}>
                <div style={{ fontSize: 11, color: "#06b6d4", fontWeight: 700, marginBottom: 6 }}>訂單流向</div>
                {[
                  { arrow: "LITE → 3081/2455", note: "InP磊晶採購（直接）" },
                  { arrow: "MRVL → 4979", note: "SiPh封裝（85-95%集中）" },
                  { arrow: "TSMC → 3363", note: "COUPE FAU（唯一認證）" },
                  { arrow: "Broadcom → 4977", note: "ELS組裝（2026H2）" },
                  { arrow: "Hyperscaler → 2345", note: "CPO交換器系統" },
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
              影響 CPO 供應鏈投資邏輯的關鍵結構性因子
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

        {/* ── Tab: 月營收快照 ── */}
        {activeTab === "signals" && (
          <div>
            <div style={{ fontSize: 13, color: "#64748b", marginBottom: 16 }}>
              2026年2月月營收 + 關鍵產業指標（資料來源：winvest.tw / revenue.db）
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
                  { time: "2026 Q1–Q2", event: "TSMC COUPE 平台量產導入", ticker: "3363 結構性訂單鎖定", color: "#06b6d4" },
                  { time: "2026 Q2", event: "上詮 1.6T FAU 系統廠驗證結果", ticker: "3363 最重要催化劑", color: "#ef4444" },
                  { time: "2026 Q2", event: "LITE 季營收目標 $600M+", ticker: "3081/2455 外購需求確認", color: "#a855f7" },
                  { time: "2026 夏季", event: "LITE 1.6T 模組出貨（含自有雷射）", ticker: "觀察 CW Laser 外購比例", color: "#f59e0b" },
                  { time: "2026 H2", event: "眾達-KY Broadcom ELS 正式放量", ticker: "4977 轉正關鍵", color: "#10b981" },
                  { time: "2026 H2", event: "800G+ 收發器出貨 24M → 63M", ticker: "全鏈需求量化驗證", color: "#06b6d4" },
                  { time: "2027", event: "CPO 滲透率突破 10%", ticker: "全鏈估值重評觸發點", color: "#f59e0b" },
                  { time: "2028 年中", event: "LITE 北卡第 5 座 InP fab 量產（UHP 專用）", ticker: "追蹤是否擴展至 CW Laser", color: "#ef4444" },
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
          光通訊 CPO 供應鏈全景圖 · 資料截止 2026年3月29日 · 僅供個人投資研究參考
        </span>
        <span style={{ fontSize: 11, color: "#334155", fontFamily: "monospace" }}>
          資料來源：winvest.tw · yfinance · LITE/COHR法說會 · TrendForce
        </span>
      </div>
    </div>
  );
}
