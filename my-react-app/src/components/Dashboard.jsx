/* ─────────────────────────────────────────────
   Dashboard.jsx — fraud-investigation workspace.
   Everything here is backed by a real API call over the Postgres history store:
     /overview          KPIs + distributions
     /accounts/fraud    the detected-fraudulent-account list (clickable)
     /accounts/{id}     why an account was flagged + its 39-day context
     /lookup            manual investigation by primary key
   ───────────────────────────────────────────── */
import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const money = (n) => (n == null ? "—" : `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
const when = (s) => (s ? new Date(s).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—");

const SEV = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high: "bg-orange-100 text-orange-700 border-orange-200",
  medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
  low: "bg-green-100 text-green-700 border-green-200",
};
const riskBar = (r) => (r >= 85 ? "bg-red-500" : r >= 60 ? "bg-orange-400" : r >= 40 ? "bg-synchrony-gold" : "bg-green-400");

function Card({ className = "", children, id }) {
  return <div id={id} className={`bg-white rounded-2xl shadow-card ${className}`}>{children}</div>;
}
function Pill({ tone = "gray", children }) {
  const tones = { gray: "bg-gray-100 text-gray-600", navy: "bg-synchrony-navy-dark text-synchrony-gold", red: "bg-red-50 text-red-700", green: "bg-green-50 text-green-700" };
  return <span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${tones[tone]}`}>{children}</span>;
}

async function apiGet(path, token) {
  const res = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || String(res.status));
  return res.json();
}

/* ── auth header used by fetches ── */
export default function Dashboard({ token, analyst }) {
  const [ov, setOv] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);      // account detail modal payload
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [o, a] = await Promise.all([apiGet("/overview", token), apiGet("/accounts/fraud", token)]);
        setOv(o); setAccounts(a.accounts);
      } catch { /* surfaced via empty states */ } finally { setLoading(false); }
    })();
  }, [token]);

  const openAccount = async (id) => {
    setDetailLoading(true); setDetail({ account: { account_id: id } });
    try { setDetail(await apiGet(`/accounts/${id}`, token)); }
    catch (e) { setDetail({ error: String(e.message) }); }
    finally { setDetailLoading(false); }
  };

  return (
    <div className="space-y-6 max-w-[1500px]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-2">
        <div>
          <h1 className="text-2xl font-extrabold text-synchrony-navy tracking-tight">Fraud Investigation Workspace</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Signed in as <span className="font-semibold text-synchrony-navy">{analyst || "analyst"}</span> · detection day <span className="font-mono">2026-09-22</span> · 39-day context in PostgreSQL
          </p>
        </div>
        <span className="inline-flex items-center gap-2 bg-white border border-gray-200 rounded-full px-3 py-1.5 shadow-sm text-xs font-semibold text-gray-600 self-start">
          <span className="relative flex h-2 w-2"><span className="animate-ping absolute h-full w-full rounded-full bg-green-400 opacity-75" /><span className="relative rounded-full h-2 w-2 bg-green-400" /></span>
          Live · Postgres + pgvector + Redis
        </span>
      </div>

      {/* KPI row (real numbers) */}
      <div id="overview" className="grid grid-cols-2 xl:grid-cols-5 gap-4 scroll-mt-44">
        <Kpi value={ov?.transactions?.toLocaleString() ?? "…"} label="Transactions analyzed" sub={`${ov?.accounts?.toLocaleString() ?? "…"} accounts`} gold />
        <Kpi value={ov?.fraud_accounts ?? "…"} label="Fraudulent accounts" sub="flagged by pipeline" red />
        <Kpi value={ov?.alerts ?? "…"} label="Fraud alerts" sub={`${ov?.fraud_rate_pct ?? "…"}% of transactions`} />
        <Kpi value={ov?.by_severity?.critical ?? "…"} label="Critical alerts" sub="risk ≥ 85 / 100" />
        <Kpi value={ov?.by_vector?.length ? ov.by_vector[0].vector : "…"} label="Top fraud vector" sub={ov?.by_vector?.length ? `${ov.by_vector[0].count} cases` : ""} />
      </div>

      <div className="grid xl:grid-cols-3 gap-6">
        {/* Detected fraudulent accounts */}
        <Card className="xl:col-span-2 p-5 scroll-mt-44" id="fraud-accounts">
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-base font-bold text-synchrony-navy">Detected Fraudulent Accounts</h2>
            <span className="text-xs text-gray-400">{accounts.length} accounts · click to investigate</span>
          </div>
          <p className="text-xs text-gray-400 mb-3">Auto-detected on the 40th day — ranked by risk. Each row aggregates that account's alerts.</p>

          <div className="overflow-hidden rounded-xl border border-gray-100">
            <div className="grid grid-cols-12 gap-2 px-3 py-2 bg-synchrony-page-bg/70 text-[11px] font-bold uppercase tracking-wide text-gray-500">
              <div className="col-span-3">Account</div>
              <div className="col-span-2">Product</div>
              <div className="col-span-2">Vector · Actor</div>
              <div className="col-span-1 text-center">Alerts</div>
              <div className="col-span-2">Risk</div>
              <div className="col-span-2 text-right">Flagged $</div>
            </div>
            <div className="max-h-[460px] overflow-y-auto divide-y divide-gray-50">
              {loading && <div className="p-6 text-center text-sm text-gray-400">Loading detected accounts…</div>}
              {!loading && accounts.length === 0 && <div className="p-6 text-center text-sm text-gray-400">No fraudulent accounts found. Is the backend loaded?</div>}
              {accounts.map((a) => (
                <button key={a.account_id} onClick={() => openAccount(a.account_id)}
                  className="w-full grid grid-cols-12 gap-2 px-3 py-2.5 items-center text-left hover:bg-synchrony-page-bg/60 transition-colors">
                  <div className="col-span-3">
                    <p className="font-mono text-xs font-bold text-synchrony-navy">{a.account_id}</p>
                    <p className="font-mono text-[10px] text-gray-400">{a.masked_pan}</p>
                  </div>
                  <div className="col-span-2 text-xs text-gray-600 capitalize">{a.product_type.replace(/_/g, " ")}</div>
                  <div className="col-span-2 flex items-center gap-1">
                    <Pill tone="navy">{a.top_vector}</Pill>
                    <span className="text-[10px] text-gray-500">{a.top_actor}</span>
                  </div>
                  <div className="col-span-1 text-center text-sm font-bold text-gray-700">{a.alerts}</div>
                  <div className="col-span-2 flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className={`h-full rounded-full ${riskBar(a.max_risk)}`} style={{ width: `${a.max_risk}%` }} /></div>
                    <span className="text-xs font-bold text-gray-600 w-7 text-right">{a.max_risk}</span>
                  </div>
                  <div className="col-span-2 text-right text-xs font-semibold text-gray-700">{money(a.flagged_amount)}</div>
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* Right column: lookup + distributions */}
        <div className="space-y-6">
          <div id="lookup" className="scroll-mt-44"><LookupPanel token={token} onOpenAccount={openAccount} /></div>
          {ov && <Distributions ov={ov} />}
        </div>
      </div>

      {detail && (
        <AccountDetailModal detail={detail} loading={detailLoading} onClose={() => setDetail(null)} />
      )}
    </div>
  );
}

function Kpi({ value, label, sub, gold, red }) {
  return (
    <Card className={`p-4 ${gold ? "bg-synchrony-gold shadow-none" : ""}`}>
      <p className={`text-3xl font-extrabold tracking-tight ${gold ? "text-synchrony-ink" : red ? "text-red-600" : "text-synchrony-navy"}`}>{value}</p>
      <p className={`text-xs font-semibold mt-1 ${gold ? "text-synchrony-ink/70" : "text-gray-500"}`}>{label}</p>
      {sub && <p className={`text-[11px] mt-1.5 ${gold ? "text-synchrony-ink/60" : "text-gray-400"}`}>{sub}</p>}
    </Card>
  );
}

function Distributions({ ov }) {
  const maxA = Math.max(...ov.by_actor.map((x) => x.count), 1);
  const maxV = Math.max(...ov.by_vector.map((x) => x.count), 1);
  return (
    <Card className="p-5">
      <h2 className="text-base font-bold text-synchrony-navy mb-3">Alert breakdown</h2>
      <p className="text-[11px] font-bold uppercase tracking-wide text-gray-400 mb-2">By actor</p>
      <div className="space-y-2 mb-4">
        {ov.by_actor.map((a) => (
          <div key={a.code} className="flex items-center gap-2">
            <span className="w-7 text-[11px] font-black text-synchrony-navy">{a.code}</span>
            <div className="flex-1"><div className="flex justify-between text-[11px] mb-0.5"><span className="text-gray-500 truncate">{a.label}</span><span className="font-bold text-gray-700">{a.count}</span></div>
              <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className="h-full rounded-full bg-synchrony-navy" style={{ width: `${(a.count / maxA) * 100}%` }} /></div></div>
          </div>
        ))}
      </div>
      <p className="text-[11px] font-bold uppercase tracking-wide text-gray-400 mb-2">Top vectors</p>
      <div className="space-y-1.5">
        {ov.by_vector.map((v) => (
          <div key={v.vector} className="flex items-center gap-2">
            <span className="bg-synchrony-navy-dark text-synchrony-gold text-[10px] font-bold px-2 py-0.5 rounded font-mono w-12 text-center">{v.vector}</span>
            <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden"><div className="h-full bg-synchrony-gold rounded-full" style={{ width: `${(v.count / maxV) * 100}%` }} /></div>
            <span className="text-xs font-semibold text-gray-600 w-6 text-right">{v.count}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ── Fraud Account Lookup — manual investigation by primary key ── */
function LookupPanel({ token, onOpenAccount }) {
  const [keyType, setKeyType] = useState("account_id");
  const [value, setValue] = useState("");
  const [res, setRes] = useState(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const search = async () => {
    setErr(""); setRes(null);
    const v = value.trim();
    if (!v) { setErr("Enter a primary key."); return; }
    setBusy(true);
    try {
      const data = await apiGet(`/lookup?${keyType}=${encodeURIComponent(v)}`, token);
      if (keyType === "account_id") { onOpenAccount(v); setBusy(false); return; }
      setRes(data);
    } catch (e) { setErr(String(e.message)); }
    finally { setBusy(false); }
  };

  return (
    <Card className="p-5">
      <h2 className="text-base font-bold text-synchrony-navy mb-1">Fraud Account Lookup</h2>
      <p className="text-xs text-gray-400 mb-3">Manual investigation by primary key.</p>
      <div className="flex gap-2 mb-2">
        {[["account_id", "Account ID"], ["transaction_id", "Transaction ID"]].map(([k, lbl]) => (
          <button key={k} onClick={() => { setKeyType(k); setRes(null); setErr(""); }}
            className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${keyType === k ? "bg-synchrony-navy text-white border-synchrony-navy" : "bg-white text-synchrony-navy border-gray-200 hover:border-synchrony-navy"}`}>
            {lbl}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <input value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => e.key === "Enter" && search()}
          placeholder={keyType === "account_id" ? "ACC-000468" : "uuid…"}
          className="flex-1 px-3 py-2 rounded-lg border border-gray-200 text-sm font-mono focus:outline-none focus:border-synchrony-navy" />
        <button onClick={search} disabled={busy} className="px-4 py-2 rounded-lg bg-synchrony-navy text-white text-sm font-semibold disabled:opacity-50">{busy ? "…" : "Search"}</button>
      </div>
      <p className="text-[11px] text-gray-400 mt-2">Primary keys only — <span className="font-mono">accounts.account_id</span> / <span className="font-mono">transactions.transaction_id</span>.</p>
      {err && <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2 mt-3">{err}</p>}

      {res && res.key_type === "transaction_id" && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${res.classification === "fraudulent" ? SEV.critical : SEV.low}`}>
              {res.classification === "fraudulent" ? "FRAUDULENT" : "NON-FRAUDULENT"}
            </span>
            <span className="font-mono text-[10px] text-gray-400">{res.transaction_id.slice(0, 8)}…</span>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <Field k="Account" v={res.account_id} mono />
            <Field k="Amount" v={money(res.transaction.amount)} />
            <Field k="Channel" v={res.transaction.channel} />
            <Field k="MCC" v={res.transaction.mcc} />
            <Field k="CVV" v={res.transaction.cvv_result} />
            <Field k="AVS" v={res.transaction.avs_result} />
            <Field k="When" v={when(res.transaction.event_time)} />
            <Field k="Status" v={res.transaction.status} />
          </div>
          {res.classification === "fraudulent" && (
            <div className="rounded-xl bg-red-50/60 border border-red-100 p-3">
              <p className="text-[11px] font-bold uppercase text-red-500 mb-1">Evidence · {res.evidence.vector} · {res.evidence.actor_label}</p>
              <p className="text-xs text-gray-700 leading-relaxed">{res.evidence.reason}</p>
              {res.evidence.ml?.signals?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">{res.evidence.ml.signals.map((s) => <Pill key={s} tone="red">{s.replace(/_/g, " ")}</Pill>)}</div>
              )}
            </div>
          )}
          {res.classification !== "fraudulent" && (
            <p className="text-xs text-gray-500">No alert on this transaction. Live ML risk: <span className="font-bold">{res.evidence.ml?.risk_score ?? "n/a"}</span>.</p>
          )}
        </div>
      )}
    </Card>
  );
}

function Field({ k, v, mono }) {
  return <div><span className="text-gray-400">{k}: </span><span className={`text-gray-800 font-semibold ${mono ? "font-mono" : ""}`}>{v ?? "—"}</span></div>;
}

/* ── Account detail modal — why the account was flagged + its context ── */
function AccountDetailModal({ detail, loading, onClose }) {
  const d = detail;
  const acct = d.account || {};
  const fraud = d.classification === "fraudulent";
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 sm:p-8 bg-black/40 overflow-y-auto" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl my-4" onClick={(e) => e.stopPropagation()}>
        {/* header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-100 sticky top-0 bg-white rounded-t-2xl z-10">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-extrabold text-synchrony-navy font-mono">{acct.account_id}</h3>
              {d.classification && (
                <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${fraud ? SEV[d.severity] || SEV.critical : SEV.low}`}>
                  {fraud ? `FRAUDULENT · ${d.severity}` : "NON-FRAUDULENT"}
                </span>
              )}
            </div>
            {acct.masked_pan && <p className="text-xs text-gray-400 font-mono mt-0.5">{acct.masked_pan} · {String(acct.product_type || "").replace(/_/g, " ")}</p>}
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-700 text-2xl leading-none">×</button>
        </div>

        <div className="p-5 space-y-5">
          {loading && <p className="text-sm text-gray-400 animate-pulse">Retrieving account, alerts, and 39-day context…</p>}
          {d.error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-3 py-2">{d.error}</p>}

          {!loading && !d.error && (
            <>
              {/* summary strip */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <Stat k="Max risk" v={`${d.max_risk}/100`} />
                <Stat k="Alerts" v={d.alert_count} />
                <Stat k="39-day txns" v={d.history_context?.transactions} />
                <Stat k="Avg amount" v={money(d.history_context?.avg_amount)} />
              </div>

              {/* why flagged: indicators */}
              {d.indicators?.length > 0 && (
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-gray-500 mb-2">Why flagged · fraud indicators</p>
                  <div className="flex flex-wrap gap-1.5">{d.indicators.map((s) => <Pill key={s} tone="red">{s.replace(/_/g, " ")}</Pill>)}</div>
                </div>
              )}

              {/* flagged transactions */}
              {d.flagged_transactions?.length > 0 && (
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-gray-500 mb-2">Transactions that triggered detection ({d.flagged_transactions.length})</p>
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {d.flagged_transactions.map((t) => (
                      <div key={t.transaction_id} className="rounded-xl border border-gray-100 p-3">
                        <div className="flex flex-wrap items-center gap-2 mb-1.5">
                          <Pill tone="navy">{t.vector}</Pill>
                          <span className="text-[11px] text-gray-500">{t.actor_label}</span>
                          <span className="ml-auto text-xs font-bold text-gray-700">{money(t.amount)}</span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${SEV[t.severity] || SEV.medium}`}>risk {t.risk_score}</span>
                        </div>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-0.5 text-[11px] mb-1.5">
                          <Field k="When" v={when(t.event_time)} />
                          <Field k="Channel" v={t.channel} />
                          <Field k="Merchant" v={t.merchant_name} />
                          <Field k="MCC" v={t.mcc} />
                          <Field k="CVV" v={t.cvv_result} />
                          <Field k="AVS" v={t.avs_result} />
                          <Field k="Entry" v={t.entry_method} />
                          <Field k="Device" v={t.device_fingerprint || "—"} />
                        </div>
                        <p className="text-[11px] text-gray-600 leading-relaxed">{t.reason}</p>
                        {t.ml?.signals?.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-1.5">
                            {t.ml.signals.map((s) => <Pill key={s} tone="gray">{s.replace(/_/g, " ")}</Pill>)}
                            {t.ml.risk_score != null && <Pill tone="gray">ML {t.ml.risk_score}</Pill>}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* 39-day context */}
              {d.history_context && (
                <div className="rounded-xl bg-synchrony-page-bg/60 border border-gray-100 p-3">
                  <p className="text-[11px] font-bold uppercase tracking-wide text-gray-500 mb-2">39-day behavioral context (PostgreSQL)</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1 text-[11px]">
                    <Field k="Window" v={d.history_context.window} />
                    <Field k="Txns" v={d.history_context.transactions} />
                    <Field k="Total" v={money(d.history_context.total_amount)} />
                    <Field k="First seen" v={when(d.history_context.first_seen)} />
                  </div>
                  {d.history_context.channel_mix?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {d.history_context.channel_mix.map((c) => <Pill key={c.channel} tone="gray">{c.channel} · {c.count}</Pill>)}
                    </div>
                  )}
                </div>
              )}

              {/* recent transactions */}
              {d.recent_transactions?.length > 0 && (
                <div>
                  <p className="text-[11px] font-bold uppercase tracking-wide text-gray-500 mb-2">Recent transaction history</p>
                  <div className="space-y-1 max-h-56 overflow-y-auto pr-1">
                    {d.recent_transactions.map((t) => (
                      <div key={t.transaction_id} className={`grid grid-cols-12 gap-2 px-2.5 py-1.5 rounded-lg text-[11px] items-center ${t.is_flagged ? "bg-red-50/70" : "bg-gray-50"}`}>
                        <span className="col-span-3 text-gray-500">{when(t.event_time)}</span>
                        <span className="col-span-3 text-gray-700 truncate">{t.merchant_name}</span>
                        <span className="col-span-2 text-gray-500">{t.channel}</span>
                        <span className="col-span-2 text-right font-semibold text-gray-700">{money(t.amount)}</span>
                        <span className="col-span-2 text-right">{t.is_flagged ? <Pill tone="red">flagged</Pill> : <span className="text-gray-400">ok</span>}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function Stat({ k, v }) {
  return (
    <div className="rounded-xl border border-gray-100 p-3">
      <p className="text-lg font-extrabold text-synchrony-navy">{v ?? "—"}</p>
      <p className="text-[11px] text-gray-500 mt-0.5">{k}</p>
    </div>
  );
}
