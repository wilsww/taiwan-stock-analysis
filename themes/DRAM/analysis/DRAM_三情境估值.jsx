import { useState, useCallback } from "react";

/* ================================================================
   台灣記憶體三情境估值儀表板
   Taiwan Memory 3-Scenario Valuation Dashboard
   南亞科 2408 vs 華邦電 2344
   資料基準：2026Q1 法說會後更新 / 2026年4月14日
   ================================================================ */

// ── 顏色常數 ──────────────────────────────────────────────────
const C = {
  bear:    { bg: "rgba(239,68,68,0.08)",   border: "#ef4444", text: "#fca5a5", solid: "#ef4444",   label: "空頭情境", en: "BEAR" },
  base:    { bg: "rgba(245,158,11,0.08)",  border: "#f59e0b", text: "#fcd34d", solid: "#f59e0b",   label: "基本情境", en: "BASE" },
  bull:    { bg: "rgba(16,185,129,0.08)",  border: "#10b981", text: "#6ee7b7", solid: "#10b981",   label: "多頭情境", en: "BULL" },
  nanya:   "#3b82f6",
  winbond: "#a855f7",
  muted:   "#475569",
  dim:     "#334155",
  fg:      "#e2e8f0",
  fg2:     "#94a3b8",
  bg0:     "#020617",
  bg1:     "#0a1628",
  bg2:     "rgba(15,23,42,0.85)",
  bg3:     "rgba(30,41,59,0.7)",
};

// ── 南亞科 2408 估值模型 ──────────────────────────────────────
const NANYA = {
  ticker: "2408",
  name: "南亞科技",
  nameEn: "Nanya Technology",
  shares: 34.5,         // 億股（私募後，2026-04-08 完成）
  bookValue: 62.25,     // 每股淨值 Q1'26 自結
  // 歷史 EPS
  epsHistory: [
    { year: "2019", eps: 0.0,  note: "低迷" },
    { year: "2020", eps: 1.5,  note: "回升" },
    { year: "2021", eps: 12.0, note: "高峰" },
    { year: "2022", eps: 6.5,  note: "下滑" },
    { year: "2023", eps: -2.0, note: "虧損" },
    { year: "2024", eps: -0.5, note: "微虧" },
    { year: "2025", eps: 2.13, note: "確認值" },
    { year: "2026E",eps: null, note: "本儀表板估算（Q1實績8.41）" },
  ],
  // 歷史毛利率
  gmHistory: [
    { period: "2021高峰", gm: 57 },
    { period: "2022", gm: 45 },
    { period: "2023谷底", gm: 0 },
    { period: "2024Q4", gm: 18.5 },
    { period: "2025Q1", gm: 27.1 },
    { period: "2025Q3", gm: 37 },
    { period: "2025Q4", gm: 49.0 },
    { period: "2026Q1", gm: 67.9 },
  ],
  // 三情境估值假設（2026-04-14 法說會後更新；Q1'26 實績 EPS 8.41，毛利率 67.9%，Q2展望優於Q1）
  scenarios: {
    bear: {
      label: "空頭：H2週期提前反轉",
      assumption: "Q2達頂 → H2 DRAM合約價下行，ASP Q3開始跌幅 >10% | 毛利率從67.9%高峰回落至~45% | Q1實績8.41+Q2估9.5，H2合計~8 → 全年約26",
      eps2026: 26,
      eps2027: 15,
      gmPeak: 68,
      peRange: [8, 12],
      pbRange: [1.5, 2.0],
      catalysts: ["H2 DRAM合約價單季跌幅超10%", "Samsung P4或CXMT提前量產", "AI伺服器需求明顯降速"],
      exitSignal: "Q3 ASP跌幅超過8% 或毛利率跌破55% → 立即減碼",
    },
    base: {
      label: "基本：超級週期延續至年底",
      assumption: "供需緊張延續至2026H2 | Q2如期優於Q1，全年ASP正增長 | 毛利率維持60-68%高點 | Q1實績8.41+Q2估10+Q3估10+Q4估6.5 → 全年約35",
      eps2026: 35,
      eps2027: 26,
      gmPeak: 70,
      peRange: [10, 15],
      pbRange: [2.2, 3.0],
      catalysts: ["Q2'26 如期優於Q1（已指引）", "DDR5滲透率突破20%+", "UWIO AI客製化記憶體持續放量"],
      exitSignal: "EPS連兩季低於預估20% 或毛利率跌破60% → 開始分批減碼",
    },
    bull: {
      label: "多頭：UWIO放量 + 新廠超前",
      assumption: "四大客戶私募綁定需求放量 | UWIO AI記憶體快速擴量 | 1C製程/EUV超前 | 新廠Q1'27提前投產 | Q1實績8.41+Q2估11+Q3估13+Q4估11.5 → 全年約44",
      eps2026: 44,
      eps2027: 35,
      gmPeak: 72,
      peRange: [12, 18],
      pbRange: [2.8, 4.5],
      catalysts: ["UWIO訂單快速擴量超過私募比例", "1C製程提前量產", "F廠裝機早於Q1'27目標"],
      exitSignal: "UWIO訂單未如期放量 或新廠裝機延遲一季以上 → 降評至基本情境",
    },
  },
  // 歷史 PE Band（高點）
  peHistoricalPeak: 20,
  peHistoricalTrough: 6,
};

// ── 華邦電 2344 估值模型 ──────────────────────────────────────
const WINBOND = {
  ticker: "2344",
  name: "華邦電子",
  nameEn: "Winbond Electronics",
  shares: 45.0,         // 億股（約）
  bookValue: 21.0,      // 每股淨值估計（2025Q4附近）
  epsHistory: [
    { year: "2019", eps: 0.5,  note: "" },
    { year: "2020", eps: 0.33, note: "" },
    { year: "2021", eps: 3.41, note: "高峰" },
    { year: "2022", eps: 3.23, note: "" },
    { year: "2023", eps: -0.29,note: "虧損" },
    { year: "2024", eps: 0.14, note: "微盈" },
    { year: "2025", eps: 0.88, note: "確認值" },
    { year: "2026E",eps: null, note: "本儀表板估算" },
  ],
  gmHistory: [
    { period: "2021高峰", gm: 40 },
    { period: "2022", gm: 34 },
    { period: "2023谷底", gm: 18 },
    { period: "2024Q2", gm: 15 },
    { period: "2024Q4", gm: 27 },
    { period: "2025Q1", gm: 25.6 },
    { period: "2025Q3", gm: 46.7 },
    { period: "2025Q4", gm: 41.9 },
  ],
  scenarios: {
    bear: {
      label: "空頭：NOR/SLC競爭加劇",
      assumption: "大廠重返SLC市場 → 華邦市佔受壓 | CMS 16nm良率不佳 | Logic IC毛利率下滑",
      eps2026: 3.5,
      eps2027: 2.5,
      gmPeak: 38,
      peRange: [10, 15],
      pbRange: [1.5, 2.0],
      catalysts: ["Samsung重回SLC NAND市場", "16nm CMS良率爬坡延遲", "Logic IC競爭壓縮毛利"],
      exitSignal: "SLC NAND毛利率跌破25% → 減碼",
    },
    base: {
      label: "基本：三引擎齊發",
      assumption: "Flash短缺持續 | CMS 16nm量產順利 | Logic IC穩定35%毛利 | CUBE 2027貢獻",
      eps2026: 5.5,
      eps2027: 7.0,
      gmPeak: 50,
      peRange: [15, 22],
      pbRange: [2.5, 3.5],
      catalysts: ["SLC/NOR短缺持續至2026H2", "16nm CMS量產達標", "汽車/IoT NOR需求持續"],
      exitSignal: "合併毛利率跌破35% → 重新評估",
    },
    bull: {
      label: "多頭：CUBE突破 + Flash定價權",
      assumption: "CUBE獲大廠採用 | Flash 24nm定價溢價 | AI Edge應用起飛 | 汽車NOR加速",
      eps2026: 7.5,
      eps2027: 10.0,
      gmPeak: 58,
      peRange: [20, 30],
      pbRange: [4.0, 6.0],
      catalysts: ["CUBE獲CSP/AI Edge訂單", "24nm Flash定價超預期", "車用NOR認證突破"],
      exitSignal: "CUBE客戶訂單確認後追蹤良率進度",
    },
  },
  peHistoricalPeak: 25,
  peHistoricalTrough: 8,
};

// ── 工具函數 ──────────────────────────────────────────────────
const fmt = (n, d = 1) => n == null ? "-" : Number(n).toFixed(d);
const fmtB = (n) => `NT$${fmt(n)}億`;

// ── 子組件：情境卡 ────────────────────────────────────────────
function ScenarioBadge({ scenario }) {
  const col = C[scenario];
  return (
    <span style={{
      fontSize: 10, fontWeight: 800, letterSpacing: "0.08em",
      color: col.solid,
      background: col.bg,
      border: `1px solid ${col.border}`,
      borderRadius: 4,
      padding: "2px 7px",
    }}>{col.en} {col.label}</span>
  );
}

// ── 子組件：EPS 歷史條形圖 ────────────────────────────────────
function EpsBar({ history, color, scenario2026eps }) {
  const allEps = [...history.filter(h => h.eps != null).map(h => h.eps), scenario2026eps || 0];
  const maxAbs = Math.max(...allEps.map(Math.abs), 1);

  return (
    <div style={{ display: "flex", gap: 4, alignItems: "flex-end", height: 80, marginTop: 8 }}>
      {history.map((h, i) => {
        const eps = h.year === "2026E" ? scenario2026eps : h.eps;
        const isProj = h.year === "2026E";
        const isNeg = eps < 0;
        const heightPct = Math.abs(eps) / maxAbs;
        const barH = Math.max(heightPct * 64, 3);

        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ fontSize: 8, color: "#94a3b8", marginBottom: 2, whiteSpace: "nowrap" }}>
              {eps != null ? (eps >= 0 ? fmt(eps) : fmt(eps)) : "-"}
            </div>
            <div style={{
              width: "100%", height: barH,
              background: isProj
                ? `repeating-linear-gradient(45deg, ${color}40, ${color}40 2px, transparent 2px, transparent 6px)`
                : isNeg ? "#ef444460" : `${color}90`,
              border: isProj ? `1px dashed ${color}` : "none",
              borderRadius: "2px 2px 0 0",
              minHeight: 3,
            }} />
            <div style={{ fontSize: 7, color: i === history.length - 1 ? color : "#475569", marginTop: 3, textAlign: "center" }}>
              {h.year}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 子組件：毛利率時間軸 ─────────────────────────────────────
function GmTimeline({ gmHistory, color }) {
  const max = Math.max(...gmHistory.map(g => g.gm));
  return (
    <div style={{ display: "flex", gap: 3, alignItems: "flex-end", height: 48, marginTop: 6 }}>
      {gmHistory.map((g, i) => {
        const isLast = i === gmHistory.length - 1;
        return (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{ fontSize: 8, color: isLast ? color : "#64748b", marginBottom: 2, whiteSpace: "nowrap" }}>
              {g.gm}%
            </div>
            <div style={{
              width: "100%",
              height: Math.max((g.gm / max) * 36, 3),
              background: isLast ? color : `${color}50`,
              borderRadius: "2px 2px 0 0",
            }} />
            <div style={{ fontSize: 6.5, color: "#334155", marginTop: 2, textAlign: "center", whiteSpace: "nowrap", overflow: "hidden" }}>
              {g.period.replace("高峰", "").replace("谷底", "")}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── 子組件：目標價計算器 ─────────────────────────────────────
function TargetPriceCalc({ company, scenario, scenarioKey, color }) {
  const [peMultiple, setPeMultiple] = useState(
    Math.round((scenario.peRange[0] + scenario.peRange[1]) / 2)
  );
  const [pbMultiple, setPbMultiple] = useState(
    parseFloat(((scenario.pbRange[0] + scenario.pbRange[1]) / 2).toFixed(1))
  );

  const peTarget = (scenario.eps2026 * peMultiple).toFixed(0);
  const pbTarget = (company.bookValue * pbMultiple).toFixed(0);
  const blended = Math.round((parseFloat(peTarget) * 0.6 + parseFloat(pbTarget) * 0.4));

  return (
    <div style={{
      background: C[scenarioKey].bg,
      border: `1px solid ${C[scenarioKey].border}40`,
      borderRadius: 8,
      padding: "14px 16px",
      marginTop: 12,
    }}>
      <div style={{ fontSize: 11, fontWeight: 800, color: C[scenarioKey].text, marginBottom: 10, letterSpacing: "0.06em" }}>
        📐 目標價計算器（互動）
      </div>

      {/* PE 滑桿 */}
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: "#94a3b8" }}>PE 倍數</span>
          <span style={{ fontSize: 13, fontWeight: 900, color: color, fontFamily: "monospace" }}>{peMultiple}x</span>
        </div>
        <input
          type="range"
          min={scenario.peRange[0] - 3}
          max={scenario.peRange[1] + 5}
          step={1}
          value={peMultiple}
          onChange={e => setPeMultiple(Number(e.target.value))}
          style={{ width: "100%", accentColor: C[scenarioKey].solid, cursor: "pointer" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "#475569" }}>
          <span>歷史低 {company.peHistoricalTrough}x</span>
          <span>情境區間 {scenario.peRange[0]}-{scenario.peRange[1]}x</span>
          <span>歷史高 {company.peHistoricalPeak}x</span>
        </div>
      </div>

      {/* PB 滑桿 */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: "#94a3b8" }}>PB 倍數</span>
          <span style={{ fontSize: 13, fontWeight: 900, color: color, fontFamily: "monospace" }}>{pbMultiple}x</span>
        </div>
        <input
          type="range"
          min={scenario.pbRange[0] - 0.5}
          max={scenario.pbRange[1] + 1.0}
          step={0.1}
          value={pbMultiple}
          onChange={e => setPbMultiple(parseFloat(Number(e.target.value).toFixed(1)))}
          style={{ width: "100%", accentColor: C[scenarioKey].solid, cursor: "pointer" }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "#475569" }}>
          <span>每股淨值 NT${company.bookValue}</span>
          <span>情境區間 {scenario.pbRange[0]}-{scenario.pbRange[1]}x</span>
        </div>
      </div>

      {/* 計算結果 */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: 8,
      }}>
        {[
          { label: "PE法目標價", value: `NT$${peTarget}`, sub: `${peMultiple}x × EPS${fmt(scenario.eps2026)}` },
          { label: "PB法目標價", value: `NT$${pbTarget}`, sub: `${pbMultiple}x × BV${company.bookValue}` },
          { label: "加權目標價", value: `NT$${blended}`, sub: "PE×60% + PB×40%", highlight: true },
        ].map(item => (
          <div key={item.label} style={{
            background: item.highlight ? `${C[scenarioKey].solid}20` : "rgba(0,0,0,0.3)",
            border: `1px solid ${item.highlight ? C[scenarioKey].solid : "#1e293b"}`,
            borderRadius: 6,
            padding: "10px 10px",
            textAlign: "center",
          }}>
            <div style={{ fontSize: 9, color: "#64748b", marginBottom: 4 }}>{item.label}</div>
            <div style={{
              fontSize: item.highlight ? 20 : 16,
              fontWeight: 900,
              color: item.highlight ? C[scenarioKey].solid : "#e2e8f0",
              fontFamily: "monospace",
            }}>{item.value}</div>
            <div style={{ fontSize: 9, color: "#475569", marginTop: 3 }}>{item.sub}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── 子組件：公司面板 ─────────────────────────────────────────
function CompanyPanel({ company, color, activeScenario }) {
  const scenario = company.scenarios[activeScenario];
  const col = C[activeScenario];

  return (
    <div style={{
      background: C.bg2,
      border: `1px solid ${color}30`,
      borderTop: `3px solid ${color}`,
      borderRadius: 10,
      padding: "16px 18px",
      flex: 1,
      minWidth: 0,
    }}>
      {/* 公司標題 */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14, paddingBottom: 12, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
        <div style={{
          width: 38, height: 38, borderRadius: 8,
          background: `${color}20`,
          border: `1px solid ${color}50`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 16, fontWeight: 900, color: color, fontFamily: "monospace",
        }}>{company.ticker}</div>
        <div>
          <div style={{ fontSize: 16, fontWeight: 900, color: C.fg }}>{company.name}</div>
          <div style={{ fontSize: 10, color: "#64748b" }}>{company.nameEn} · {company.shares}億股</div>
        </div>
        <div style={{ marginLeft: "auto", textAlign: "right" }}>
          <div style={{ fontSize: 10, color: "#64748b" }}>每股淨值</div>
          <div style={{ fontSize: 16, fontWeight: 800, color: color, fontFamily: "monospace" }}>NT${company.bookValue}</div>
        </div>
      </div>

      {/* 情境假設 */}
      <div style={{
        background: col.bg,
        border: `1px solid ${col.border}40`,
        borderLeft: `3px solid ${col.solid}`,
        borderRadius: 6,
        padding: "10px 12px",
        marginBottom: 14,
      }}>
        <div style={{ fontSize: 11, fontWeight: 800, color: col.text, marginBottom: 4 }}>{scenario.label}</div>
        <div style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.6 }}>{scenario.assumption}</div>
      </div>

      {/* 核心預估數字 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 14 }}>
        {[
          { label: "2026E EPS", value: `NT$${fmt(scenario.eps2026)}`, unit: "元" },
          { label: "2027E EPS", value: `NT$${fmt(scenario.eps2027)}`, unit: "元" },
          { label: "毛利率峰值", value: `${scenario.gmPeak}%`, unit: "" },
          { label: "市值估算", value: `NT$${Math.round(scenario.eps2026 * ((scenario.peRange[0]+scenario.peRange[1])/2) * company.shares / 100)}B`, unit: "" },
        ].map(item => (
          <div key={item.label} style={{
            background: "rgba(0,0,0,0.3)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 6,
            padding: "8px 10px",
            textAlign: "center",
          }}>
            <div style={{ fontSize: 9, color: "#64748b", marginBottom: 4 }}>{item.label}</div>
            <div style={{ fontSize: 15, fontWeight: 900, color: col.solid, fontFamily: "monospace" }}>{item.value}</div>
          </div>
        ))}
      </div>

      {/* EPS歷史圖 */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: "0.08em" }}>EPS 歷史 + 情境預估</div>
        <EpsBar history={company.epsHistory} color={color} scenario2026eps={scenario.eps2026} />
      </div>

      {/* 毛利率歷史圖 */}
      <div style={{ marginBottom: 14 }}>
        <div style={{ fontSize: 10, color: "#475569", fontWeight: 700, letterSpacing: "0.08em" }}>毛利率歷史走勢</div>
        <GmTimeline gmHistory={company.gmHistory} color={color} />
      </div>

      {/* 催化劑與出場訊號 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 14 }}>
        <div style={{
          background: "rgba(0,0,0,0.2)",
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 6,
          padding: "10px 12px",
        }}>
          <div style={{ fontSize: 10, color: "#64748b", fontWeight: 700, marginBottom: 6 }}>📈 情境催化劑</div>
          {scenario.catalysts.map((c, i) => (
            <div key={i} style={{ display: "flex", gap: 6, marginBottom: 4 }}>
              <span style={{ color: col.solid, fontSize: 10, flexShrink: 0 }}>▸</span>
              <span style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.5 }}>{c}</span>
            </div>
          ))}
        </div>
        <div style={{
          background: "rgba(239,68,68,0.05)",
          border: "1px solid rgba(239,68,68,0.2)",
          borderRadius: 6,
          padding: "10px 12px",
        }}>
          <div style={{ fontSize: 10, color: "#ef4444", fontWeight: 700, marginBottom: 6 }}>🔔 出場訊號</div>
          <div style={{ fontSize: 11, color: "#fca5a5", lineHeight: 1.6 }}>{scenario.exitSignal}</div>
        </div>
      </div>

      {/* 互動目標價計算器 */}
      <TargetPriceCalc company={company} scenario={scenario} scenarioKey={activeScenario} color={color} />
    </div>
  );
}

// ── 子組件：比較表格 ─────────────────────────────────────────
function ComparisonTable({ activeScenario }) {
  const rows = [
    { label: "EPS 2026E（元）", nanya: NANYA.scenarios[activeScenario].eps2026, winbond: WINBOND.scenarios[activeScenario].eps2026, higher: "nanya" },
    { label: "EPS 2027E（元）", nanya: NANYA.scenarios[activeScenario].eps2027, winbond: WINBOND.scenarios[activeScenario].eps2027, higher: "nanya" },
    { label: "毛利率峰值（%）", nanya: NANYA.scenarios[activeScenario].gmPeak, winbond: WINBOND.scenarios[activeScenario].gmPeak, higher: "nanya" },
    { label: "PE區間（x）", nanya: `${NANYA.scenarios[activeScenario].peRange[0]}-${NANYA.scenarios[activeScenario].peRange[1]}`, winbond: `${WINBOND.scenarios[activeScenario].peRange[0]}-${WINBOND.scenarios[activeScenario].peRange[1]}`, textOnly: true },
    { label: "PB區間（x）", nanya: `${NANYA.scenarios[activeScenario].pbRange[0]}-${NANYA.scenarios[activeScenario].pbRange[1]}`, winbond: `${WINBOND.scenarios[activeScenario].pbRange[0]}-${WINBOND.scenarios[activeScenario].pbRange[1]}`, textOnly: true },
    { label: "PE法目標價（元）",
      nanya: Math.round(NANYA.scenarios[activeScenario].eps2026 * (NANYA.scenarios[activeScenario].peRange[0]+NANYA.scenarios[activeScenario].peRange[1])/2),
      winbond: Math.round(WINBOND.scenarios[activeScenario].eps2026 * (WINBOND.scenarios[activeScenario].peRange[0]+WINBOND.scenarios[activeScenario].peRange[1])/2),
      higher: "nanya", isMoney: true },
    { label: "每股淨值（元）", nanya: NANYA.bookValue, winbond: WINBOND.bookValue, higher: "nanya" },
    { label: "流通股數（億股）", nanya: NANYA.shares, winbond: WINBOND.shares, higher: "winbond" },
  ];

  const col = C[activeScenario];

  return (
    <div style={{
      background: C.bg2,
      border: `1px solid ${col.border}30`,
      borderRadius: 10,
      overflow: "hidden",
      marginTop: 16,
    }}>
      <div style={{
        background: `${col.solid}15`,
        borderBottom: `1px solid ${col.border}30`,
        padding: "10px 16px",
        display: "flex",
        alignItems: "center",
        gap: 8,
      }}>
        <ScenarioBadge scenario={activeScenario} />
        <span style={{ fontSize: 12, fontWeight: 700, color: "#e2e8f0" }}>南亞科 vs 華邦電 — 關鍵指標對照</span>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "rgba(0,0,0,0.3)" }}>
            <th style={{ padding: "8px 16px", textAlign: "left", fontSize: 11, color: "#64748b", fontWeight: 700 }}>指標</th>
            <th style={{ padding: "8px 16px", textAlign: "center", fontSize: 11, color: C.nanya, fontWeight: 700 }}>南亞科 2408</th>
            <th style={{ padding: "8px 16px", textAlign: "center", fontSize: 11, color: C.winbond, fontWeight: 700 }}>華邦電 2344</th>
            <th style={{ padding: "8px 16px", textAlign: "center", fontSize: 11, color: "#64748b", fontWeight: 700 }}>彈性差異</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const nanyaNum = typeof row.nanya === "number" ? row.nanya : null;
            const winbondNum = typeof row.winbond === "number" ? row.winbond : null;
            let diff = null;
            if (nanyaNum != null && winbondNum != null && winbondNum !== 0) {
              diff = ((nanyaNum - winbondNum) / Math.abs(winbondNum) * 100).toFixed(0);
            }
            return (
              <tr key={i} style={{
                background: i % 2 === 0 ? "transparent" : "rgba(255,255,255,0.02)",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
              }}>
                <td style={{ padding: "9px 16px", fontSize: 12, color: "#94a3b8" }}>{row.label}</td>
                <td style={{ padding: "9px 16px", textAlign: "center", fontSize: 13, fontWeight: 800, color: C.nanya, fontFamily: row.textOnly ? "inherit" : "monospace" }}>
                  {row.isMoney ? `NT$${row.nanya}` : row.nanya}
                </td>
                <td style={{ padding: "9px 16px", textAlign: "center", fontSize: 13, fontWeight: 800, color: C.winbond, fontFamily: row.textOnly ? "inherit" : "monospace" }}>
                  {row.isMoney ? `NT$${row.winbond}` : row.winbond}
                </td>
                <td style={{ padding: "9px 16px", textAlign: "center", fontSize: 11 }}>
                  {diff != null ? (
                    <span style={{ color: Number(diff) > 0 ? C.nanya : C.winbond }}>
                      {Number(diff) > 0 ? "2408+" : "2344+"}{Math.abs(Number(diff))}%
                    </span>
                  ) : "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── 子組件：情境概率儀表盤 ───────────────────────────────────
function ProbabilityDial({ activeScenario, onSelect }) {
  const probs = { bear: 20, base: 55, bull: 25 };
  return (
    <div style={{
      background: C.bg2,
      border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 10,
      padding: "14px 18px",
    }}>
      <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 10 }}>
        情境概率評估（主觀）
      </div>
      <div style={{ display: "flex", gap: 8 }}>
        {Object.entries(probs).map(([key, prob]) => {
          const col = C[key];
          const isActive = activeScenario === key;
          return (
            <button
              key={key}
              onClick={() => onSelect(key)}
              style={{
                flex: 1,
                background: isActive ? col.bg : "transparent",
                border: `2px solid ${isActive ? col.solid : col.border + "50"}`,
                borderRadius: 8,
                padding: "12px 8px",
                cursor: "pointer",
                transition: "all 0.15s",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: 22, fontWeight: 900, color: col.solid, fontFamily: "monospace" }}>{prob}%</div>
              <div style={{ fontSize: 10, color: col.text, marginTop: 2 }}>{col.label}</div>
              {/* 概率條 */}
              <div style={{
                height: 4, background: "rgba(255,255,255,0.05)",
                borderRadius: 2, marginTop: 6, overflow: "hidden",
              }}>
                <div style={{
                  height: "100%",
                  width: `${prob}%`,
                  background: col.solid,
                  borderRadius: 2,
                }} />
              </div>
            </button>
          );
        })}
      </div>
      <div style={{ fontSize: 10, color: "#334155", marginTop: 8, textAlign: "center" }}>
        點選情境卡切換下方所有估值（主觀概率僅供參考，不構成投資建議）
      </div>
    </div>
  );
}

// ── 子組件：週期位置計 ───────────────────────────────────────
function CycleGauge() {
  // 週期位置 0-100，當前估計在65（主升段）
  const position = 68;
  const phases = [
    { label: "谷底", range: [0, 20], color: "#ef4444" },
    { label: "復甦", range: [20, 40], color: "#f97316" },
    { label: "加速", range: [40, 60], color: "#f59e0b" },
    { label: "主升段", range: [60, 80], color: "#10b981" },
    { label: "高峰", range: [80, 100], color: "#06b6d4" },
  ];
  const currentPhase = phases.find(p => position >= p.range[0] && position < p.range[1]);

  return (
    <div style={{
      background: C.bg2,
      border: "1px solid rgba(255,255,255,0.06)",
      borderRadius: 10,
      padding: "14px 18px",
    }}>
      <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 8 }}>
        DRAM 週期位置計（2026年2月）
      </div>
      <div style={{ position: "relative", height: 28 }}>
        <div style={{ display: "flex", height: 16, borderRadius: 4, overflow: "hidden" }}>
          {phases.map((p, i) => (
            <div key={i} style={{
              flex: 1,
              background: position >= p.range[0] && position < p.range[1] ? p.color : `${p.color}30`,
              borderRight: "1px solid rgba(0,0,0,0.3)",
            }} />
          ))}
        </div>
        {/* 指針 */}
        <div style={{
          position: "absolute",
          top: -2,
          left: `calc(${position}% - 8px)`,
          width: 16, height: 20,
          background: currentPhase?.color,
          borderRadius: 3,
          display: "flex", alignItems: "flex-end", justifyContent: "center",
          boxShadow: `0 0 10px ${currentPhase?.color}`,
        }}>
          <div style={{ width: 2, height: 6, background: "white", marginBottom: 2, borderRadius: 1 }} />
        </div>
        <div style={{ display: "flex", marginTop: 4 }}>
          {phases.map((p, i) => (
            <div key={i} style={{
              flex: 1, textAlign: "center",
              fontSize: 9,
              color: position >= p.range[0] && position < p.range[1] ? p.color : "#334155",
              fontWeight: position >= p.range[0] && position < p.range[1] ? 800 : 400,
            }}>{p.label}</div>
          ))}
        </div>
      </div>
      <div style={{ marginTop: 8, display: "flex", gap: 6, alignItems: "center" }}>
        <div style={{
          fontSize: 12, fontWeight: 800,
          color: currentPhase?.color,
          background: `${currentPhase?.color}15`,
          border: `1px solid ${currentPhase?.color}40`,
          borderRadius: 5,
          padding: "3px 10px",
        }}>
          現在：{currentPhase?.label}（{position}/100）
        </div>
        <span style={{ fontSize: 10, color: "#475569" }}>Q3 2025 開始主升 → 預估高峰 2026 Q2-Q3</span>
      </div>
    </div>
  );
}

// ── 主組件 ────────────────────────────────────────────────────
export default function ValuationDashboard() {
  const [activeScenario, setActiveScenario] = useState("base");

  return (
    <div style={{
      minHeight: "100vh",
      background: `linear-gradient(135deg, ${C.bg0} 0%, ${C.bg1} 50%, #060d1f 100%)`,
      color: C.fg,
      fontFamily: "'IBM Plex Mono', 'SF Mono', 'Fira Code', monospace",
    }}>
      {/* ── 標題列 ── */}
      <div style={{
        background: "linear-gradient(90deg, rgba(59,130,246,0.15) 0%, rgba(168,85,247,0.08) 100%)",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        padding: "18px 24px 14px",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ display: "flex", gap: 3 }}>
                {["#3b82f6", "#a855f7"].map((c, i) => (
                  <div key={i} style={{ width: 4, height: 32, background: c, borderRadius: 2 }} />
                ))}
              </div>
              <div>
                <h1 style={{
                  fontSize: 20, fontWeight: 900, margin: 0, letterSpacing: "-0.5px",
                  background: "linear-gradient(90deg, #3b82f6, #a855f7)",
                  WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
                }}>
                  台灣記憶體 三情境估值儀表板
                </h1>
                <p style={{ margin: 0, fontSize: 10, color: "#475569", letterSpacing: "0.08em" }}>
                  TAIWAN MEMORY 3-SCENARIO VALUATION · 2408 NANYA vs 2344 WINBOND · 2026.02
                </p>
              </div>
            </div>
          </div>
          <div style={{
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 6,
            padding: "6px 12px",
            fontSize: 10,
            color: "#fca5a5",
          }}>
            ⚠️ 本儀表板僅供研究參考，不構成投資建議
          </div>
        </div>
      </div>

      <div style={{ padding: "18px 24px" }}>
        {/* ── 頂部：週期位置計 + 概率評估 ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
          <CycleGauge />
          <ProbabilityDial activeScenario={activeScenario} onSelect={setActiveScenario} />
        </div>

        {/* ── 情境選擇 Tab ── */}
        <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
          {["bear", "base", "bull"].map(key => {
            const col = C[key];
            const isActive = activeScenario === key;
            return (
              <button
                key={key}
                onClick={() => setActiveScenario(key)}
                style={{
                  flex: 1,
                  background: isActive ? col.bg : "transparent",
                  border: `2px solid ${isActive ? col.solid : col.border + "40"}`,
                  borderRadius: 8,
                  padding: "10px 14px",
                  cursor: "pointer",
                  transition: "all 0.15s",
                  textAlign: "center",
                  boxShadow: isActive ? `0 0 20px ${col.solid}20` : "none",
                }}
              >
                <div style={{ fontSize: 12, fontWeight: 900, color: isActive ? col.solid : "#64748b", letterSpacing: "0.05em" }}>
                  {col.en}
                </div>
                <div style={{ fontSize: 11, color: isActive ? col.text : "#475569", marginTop: 2 }}>
                  {col.label}
                </div>
              </button>
            );
          })}
        </div>

        {/* ── 雙欄公司面板 ── */}
        <div style={{ display: "flex", gap: 14, marginBottom: 16 }}>
          <CompanyPanel company={NANYA} color={C.nanya} activeScenario={activeScenario} />
          <CompanyPanel company={WINBOND} color={C.winbond} activeScenario={activeScenario} />
        </div>

        {/* ── 比較表格 ── */}
        <ComparisonTable activeScenario={activeScenario} />

        {/* ── 投資組合配置建議 ── */}
        <div style={{
          marginTop: 16,
          background: C.bg2,
          border: "1px solid rgba(255,255,255,0.06)",
          borderRadius: 10,
          padding: "16px 18px",
        }}>
          <div style={{ fontSize: 11, color: "#475569", fontWeight: 700, letterSpacing: "0.1em", marginBottom: 12 }}>
            📊 投資組合配置建議（情境對應）
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
            {[
              {
                scenario: "bear",
                nanyaAlloc: "20-30%",
                winbondAlloc: "15-25%",
                note: "保留高現金，等待更佳買點",
                totalMem: "合計記憶體倉位 35-55%",
              },
              {
                scenario: "base",
                nanyaAlloc: "35-45%",
                winbondAlloc: "25-35%",
                note: "核心持有，季報後動態調整",
                totalMem: "合計記憶體倉位 60-80%",
              },
              {
                scenario: "bull",
                nanyaAlloc: "40-50%",
                winbondAlloc: "30-40%",
                note: "滿倉加槓桿前需確認催化劑",
                totalMem: "合計記憶體倉位 70-90%",
              },
            ].map(item => {
              const col = C[item.scenario];
              return (
                <div key={item.scenario} style={{
                  background: activeScenario === item.scenario ? col.bg : "rgba(0,0,0,0.2)",
                  border: `1px solid ${activeScenario === item.scenario ? col.border : "#1e293b"}`,
                  borderRadius: 8,
                  padding: "12px 14px",
                }}>
                  <ScenarioBadge scenario={item.scenario} />
                  <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 6 }}>
                    {[
                      { label: "南亞科 2408", value: item.nanyaAlloc, color: C.nanya },
                      { label: "華邦電 2344", value: item.winbondAlloc, color: C.winbond },
                    ].map(a => (
                      <div key={a.label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <span style={{ fontSize: 11, color: "#64748b" }}>{a.label}</span>
                        <span style={{ fontSize: 13, fontWeight: 900, color: a.color, fontFamily: "monospace" }}>{a.value}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{
                    marginTop: 8,
                    fontSize: 10,
                    color: col.text,
                    background: col.bg,
                    border: `1px solid ${col.border}30`,
                    borderRadius: 4,
                    padding: "4px 8px",
                  }}>{item.totalMem}</div>
                  <div style={{ marginTop: 6, fontSize: 10, color: "#475569" }}>{item.note}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Footer */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,0.04)",
        padding: "10px 24px",
        display: "flex",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 6,
        fontSize: 9,
        color: "#334155",
      }}>
        <span>資料來源：南亞科 2025Q4 自結財報 · 華邦電 4Q25 法說投影片 · 作者主觀三情境分析</span>
        <span>免責聲明：本儀表板僅為研究工具，不構成任何形式之投資建議。投資人應自行判斷風險。</span>
      </div>
    </div>
  );
}
