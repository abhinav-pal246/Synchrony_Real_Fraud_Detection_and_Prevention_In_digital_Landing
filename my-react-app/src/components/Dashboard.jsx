/* ─────────────────────────────────────────────
   Dashboard.jsx — clean fraud-analytics view that mirrors the real pipeline:
     Classify type → Map fraud vectors → Multi-agent + LLM + vector → Decision
   Includes a LIVE analyzer that calls the backend /investigate.
   ───────────────────────────────────────────── */
import { useState } from "react";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/* ── real numbers from our 40-day dataset + system ── */
const STATS = { txns: "52,260", accounts: "1,000", days: 40, fraud: 250, rate: "0.48%", cases: "2,750", agents: 5 };

const VECTORS = [
  ["CB-2", 77], ["PF-1", 40], ["CB-4", 26], ["APP-2", 25], ["PL-2", 24],
  ["CC-1", 22], ["X-1", 12], ["EC-1", 10], ["DW-1", 6], ["CB-1", 4], ["CB-3", 4],
];
const ACTORS = [
  ["3P", 109, "Third-party criminal", "bg-red-500"],
  ["B", 64, "First-party buyer", "bg-synchrony-gold"],
  ["M", 48, "Merchant / staff", "bg-purple-500"],
  ["S", 29, "Synthetic / ring", "bg-orange-500"],
];
const TYPES = [
  ["Private-label", "PL-1…3 · X-*"], ["Co-branded", "CB-1…4 · X-*"],
  ["Promotional financing", "PF-1…4"], ["POS installment", "IL-1…4"],
  ["CareCredit", "CC-1…5"], ["Real-time application", "APP-1…9"],
  ["Digital wallet", "DW-1…4"], ["E-commerce", "EC-1…6"],
];
const PIPELINE = [
  ["Classify type", "channel · BIN · wallet · promo → one of 8 product lines"],
  ["Map fraud vectors", "activate only the applicable taxonomy vectors"],
  ["Agents + LLM + vector", "5 agents score · pgvector finds precedent · Bedrock explains"],
  ["Decision", "approve · review · step-up · decline"],
];

/* ── preset transactions for the live analyzer ── */
const SCENARIOS = {
  card_testing: {
    label: "Card-testing burst", type: "E-commerce",
    txn: { account_id: "ACC-000123", amount: 0.75, channel: "e_commerce", entry_method: "cnp",
           card_present: false, cvv_result: "no_match", avs_result: "N", status: "declined", mcc: "5411" },
  },
  wallet_ato: {
    label: "Wallet takeover", type: "Digital wallet",
    txn: { account_id: "ACC-000123", amount: 1499, channel: "mobile", entry_method: "token",
           card_present: false, cvv_result: "match", avs_result: "Y", status: "approved", mcc: "5732",
           device_fingerprint: "dev_new_9f2", ip_address: "88.12.9.4" },
  },
  normal: {
    label: "Normal purchase", type: "In-store",
    txn: { account_id: "ACC-000123", amount: 62.4, channel: "in_store", entry_method: "chip",
           card_present: true, cvv_result: "not_provided", avs_result: "", status: "approved", mcc: "5311" },
  },
};

const DECISION_STYLE = {
  decline: "bg-red-100 text-red-700 border-red-200",
  step_up_authentication: "bg-orange-100 text-orange-700 border-orange-200",
  manual_review: "bg-yellow-100 text-yellow-700 border-yellow-200",
  approve: "bg-green-100 text-green-700 border-green-200",
};
const riskColor = (r) => (r >= 0.7 ? "bg-red-500" : r >= 0.4 ? "bg-orange-400" : r >= 0.15 ? "bg-synchrony-gold" : "bg-green-400");

function Card({ className = "", children }) {
  return <div className={`bg-white rounded-3xl shadow-card ${className}`}>{children}</div>;
}

export default function Dashboard({ token, analyst }) {
  const [active, setActive] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async (key) => {
    setActive(key); setLoading(true); setError(""); setResult(null);
    try {
      const res = await fetch(`${API}/investigate`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(SCENARIOS[key].txn),
      });
      if (!res.ok) throw new Error(String(res.status));
      setResult(await res.json());
    } catch {
      setError("Couldn't reach the analyzer. Make sure the backend is running on :8000.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-extrabold text-synchrony-navy tracking-tight">Fraud Detection Overview</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Signed in as <span className="font-semibold text-synchrony-navy">{analyst || "analyst"}</span> · real-time transaction-type-aware pipeline
          </p>
        </div>
        <span className="inline-flex items-center gap-2 bg-white border border-gray-200 rounded-full px-3 py-1.5 shadow-sm text-xs font-semibold text-gray-600 self-start">
          <span className="relative flex h-2 w-2"><span className="animate-ping absolute h-full w-full rounded-full bg-green-400 opacity-75" /><span className="relative rounded-full h-2 w-2 bg-green-400" /></span>
          System Live
        </span>
      </div>

      {/* KPI tiles */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <Card className="p-5 bg-synchrony-gold shadow-none">
          <p className="text-4xl font-extrabold text-synchrony-ink tracking-tight">{STATS.txns}</p>
          <p className="text-sm font-semibold text-synchrony-ink/70 mt-1">Transactions analyzed</p>
          <p className="text-xs text-synchrony-ink/60 mt-2">{STATS.accounts} accounts · {STATS.days} days</p>
        </Card>
        <Card className="p-5">
          <p className="text-4xl font-extrabold text-red-600 tracking-tight">{STATS.fraud}</p>
          <p className="text-sm font-semibold text-gray-500 mt-1">Fraud detected</p>
          <p className="text-xs text-gray-400 mt-2">{STATS.rate} of all transactions</p>
        </Card>
        <Card className="p-5">
          <p className="text-4xl font-extrabold text-synchrony-navy tracking-tight">{STATS.agents}</p>
          <p className="text-sm font-semibold text-gray-500 mt-1">Detection agents</p>
          <p className="text-xs text-gray-400 mt-2">Rule · ML · Velocity · Graph · Vector</p>
        </Card>
        <Card className="p-5">
          <p className="text-4xl font-extrabold text-synchrony-navy tracking-tight">{STATS.cases}</p>
          <p className="text-sm font-semibold text-gray-500 mt-1">Vector case library</p>
          <p className="text-xs text-gray-400 mt-2">pgvector · similarity + RAG</p>
        </Card>
      </div>

      {/* Pipeline */}
      <Card className="p-6">
        <h2 className="text-base font-bold text-synchrony-navy mb-4">How every transaction is analyzed</h2>
        <div className="grid md:grid-cols-4 gap-3">
          {PIPELINE.map(([title, desc], i) => (
            <div key={title} className="relative rounded-2xl border border-gray-100 bg-synchrony-page-bg/60 p-4">
              <div className="w-7 h-7 rounded-full bg-synchrony-navy text-white text-xs font-bold flex items-center justify-center mb-3">{i + 1}</div>
              <p className="font-bold text-sm text-synchrony-navy">{title}</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{desc}</p>
              {i < 3 && <div className="hidden md:block absolute -right-2 top-1/2 text-gray-300 text-lg">→</div>}
            </div>
          ))}
        </div>
      </Card>

      {/* Live analyzer + breakdowns */}
      <div className="grid xl:grid-cols-3 gap-6">
        {/* Live analyzer (2/3) */}
        <Card className="xl:col-span-2 p-6">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-base font-bold text-synchrony-navy">Live Transaction Analyzer</h2>
            <span className="text-[11px] font-semibold text-synchrony-slate uppercase tracking-widest">real backend call</span>
          </div>
          <p className="text-xs text-gray-400 mb-4">Pick a scenario — it runs the full agent + vector + LLM pipeline via <code>/investigate</code>.</p>

          <div className="flex flex-wrap gap-2 mb-5">
            {Object.entries(SCENARIOS).map(([key, s]) => (
              <button key={key} onClick={() => run(key)} disabled={loading}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors border
                  ${active === key ? "bg-synchrony-navy text-white border-synchrony-navy"
                                   : "bg-white text-synchrony-navy border-gray-200 hover:border-synchrony-navy"}
                  disabled:opacity-50`}>
                {s.label}
              </button>
            ))}
          </div>

          {loading && <p className="text-sm text-gray-500 animate-pulse">Running the pipeline…</p>}
          {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{error}</p>}

          {result && !loading && (
            <div className="space-y-5">
              {/* verdict header */}
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <p className="text-[11px] uppercase tracking-widest text-gray-400 font-semibold">Transaction type</p>
                  <p className="font-bold text-synchrony-navy">{SCENARIOS[active].type}</p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-widest text-gray-400 font-semibold">Final risk</p>
                  <p className="font-extrabold text-2xl text-synchrony-navy">{result.final_risk}</p>
                </div>
                <div>
                  <p className="text-[11px] uppercase tracking-widest text-gray-400 font-semibold">Decision</p>
                  <span className={`inline-block mt-0.5 px-3 py-1 rounded-full text-xs font-bold border ${DECISION_STYLE[result.decision] || DECISION_STYLE.approve}`}>
                    {String(result.decision).replace(/_/g, " ")}
                  </span>
                </div>
                <div className="ml-auto text-right">
                  <p className="text-[11px] uppercase tracking-widest text-gray-400 font-semibold">Consensus</p>
                  <p className="font-bold text-synchrony-navy">{result.consensus_agents} / {result.agents.length} agents</p>
                </div>
              </div>

              {/* agents */}
              <div>
                <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wide">Agent verdicts</p>
                <div className="space-y-2.5">
                  {result.agents.map((a) => (
                    <div key={a.agent} className="flex items-center gap-3">
                      <span className="w-44 text-xs font-semibold text-synchrony-navy truncate">{a.agent.replace("Agent", "")}</span>
                      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${riskColor(a.risk)}`} style={{ width: `${Math.round(a.risk * 100)}%` }} />
                      </div>
                      <span className="w-10 text-right text-xs font-bold text-gray-700">{a.risk}</span>
                      <span className="hidden lg:block flex-[1.4] text-[11px] text-gray-400 truncate">{a.rationale}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* similar cases (vector search) */}
              {result.similar_cases?.length > 0 && (
                <div>
                  <p className="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wide">Similar past cases · pgvector</p>
                  <div className="flex flex-wrap gap-2">
                    {result.similar_cases.slice(0, 5).map((c, i) => (
                      <span key={i} className={`text-[11px] font-semibold px-2.5 py-1 rounded-lg ${c.is_fraud ? "bg-red-50 text-red-700" : "bg-gray-100 text-gray-500"}`}>
                        {c.is_fraud ? `FRAUD ${c.fraud_vector}` : "legit"} · d={c.distance}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* LLM investigator */}
              {result.investigation && (
                <div className="rounded-2xl bg-synchrony-navy-dark p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-synchrony-gold">AI investigator</span>
                    <span className="text-[10px] text-synchrony-slate">{result.investigation.model}</span>
                  </div>
                  <p className="text-sm text-gray-200 leading-relaxed whitespace-pre-line">{result.investigation.summary}</p>
                </div>
              )}
            </div>
          )}

          {!result && !loading && !error && (
            <div className="rounded-2xl border border-dashed border-gray-200 p-8 text-center text-sm text-gray-400">
              Select a scenario above to run the live pipeline.
            </div>
          )}
        </Card>

        {/* Right column: breakdowns */}
        <div className="space-y-6">
          <Card className="p-5">
            <h2 className="text-base font-bold text-synchrony-navy mb-1">Fraud by actor</h2>
            <p className="text-xs text-gray-400 mb-4">{STATS.fraud} confirmed cases</p>
            <div className="space-y-3">
              {ACTORS.map(([code, n, label, color]) => (
                <div key={code} className="flex items-center gap-3">
                  <span className="w-7 h-7 rounded-lg bg-gray-100 flex items-center justify-center text-[11px] font-black text-synchrony-navy">{code}</span>
                  <div className="flex-1">
                    <div className="flex justify-between text-xs mb-1"><span className="text-gray-600 truncate">{label}</span><span className="font-bold text-gray-800">{n}</span></div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className={`h-full rounded-full ${color}`} style={{ width: `${(n / 109) * 100}%` }} /></div>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-5">
            <h2 className="text-base font-bold text-synchrony-navy mb-1">Top fraud vectors</h2>
            <p className="text-xs text-gray-400 mb-4">detected across the taxonomy</p>
            <div className="space-y-2">
              {VECTORS.slice(0, 7).map(([v, n]) => (
                <div key={v} className="flex items-center gap-2">
                  <span className="bg-synchrony-navy-dark text-synchrony-gold text-[10px] font-bold px-2 py-0.5 rounded font-mono w-12 text-center">{v}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className="h-full bg-synchrony-navy rounded-full" style={{ width: `${(n / 77) * 100}%` }} /></div>
                  <span className="text-xs font-semibold text-gray-600 w-6 text-right">{n}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* 8 transaction types */}
      <Card className="p-6">
        <h2 className="text-base font-bold text-synchrony-navy mb-1">8 transaction types · each routed to its own fraud vectors</h2>
        <p className="text-xs text-gray-400 mb-4">The classifier picks the product line, then only the relevant taxonomy vectors are evaluated.</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {TYPES.map(([name, vectors]) => (
            <div key={name} className="rounded-2xl border border-gray-100 p-4 hover:shadow-card transition-shadow">
              <p className="font-bold text-sm text-synchrony-navy">{name}</p>
              <p className="text-[11px] text-synchrony-slate font-mono mt-1">{vectors}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
