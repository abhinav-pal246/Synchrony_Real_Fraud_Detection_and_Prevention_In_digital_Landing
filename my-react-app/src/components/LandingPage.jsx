import SynchronyLogo from "./SynchronyLogo.jsx";
import SynchronyTopNav from "./SynchronyTopNav.jsx";
import HeroCarousel from "./HeroCarousel.jsx";

const TRUST_STATS = [
  { value: "70M+",   label: "Active accounts protected" },
  { value: "235M+",  label: "Transactions / month" },
  { value: "$180B",  label: "Annual volume monitored" },
  { value: "<6s",    label: "Decision window" },
];

const FEATURES = [
  {
    tag: "STREAMING",
    title: "Real-time detection",
    desc: "Every transaction flows through Kafka and is scored the instant it arrives — no batch delay, no waiting.",
    icon: "M13 2L3 14h9l-1 8 10-12h-9l1-8z",
  },
  {
    tag: "INTELLIGENCE",
    title: "ML + graph analysis",
    desc: "Rule engine, gradient-boosted models, and pgvector graph analysis catch fraud rings that hide in the noise.",
    icon: "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z M23 21v-2a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75",
  },
  {
    tag: "TRANSPARENCY",
    title: "Explainable alerts",
    desc: "AWS Bedrock turns every alert into a plain-language reason an analyst can act on — and audit later.",
    icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];

export default function LandingPage({ onRequestSignIn }) {
  return (
    <div className="min-h-screen bg-white flex flex-col font-sans">

      {/* ── Replicated Synchrony navbar ── */}
      <SynchronyTopNav onRequestSignIn={onRequestSignIn} />

      {/* ── Hero banner carousel ── */}
      <HeroCarousel onRequestSignIn={onRequestSignIn} />

      {/* ── Featured section (white rounded cards) ── */}
      <section className="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 py-16 lg:py-24 w-full">
        <div className="max-w-2xl mb-12">
          <p className="text-sm font-bold uppercase tracking-widest text-synchrony-navy mb-3">
            The platform
          </p>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-synchrony-ink tracking-tight leading-tight">
            Built for the way fraud actually happens
          </h2>
          <p className="mt-4 text-lg text-synchrony-ink/60">
            Four actor types. Eight product lines. Forty-five fraud vectors. One detection pipeline.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="bg-white border border-gray-200 rounded-3xl p-7 hover:shadow-card-hover transition-shadow">
              <div className="w-12 h-12 rounded-2xl bg-synchrony-cream flex items-center justify-center mb-5">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#1E2A45" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d={f.icon} />
                </svg>
              </div>
              <p className="text-[11px] font-bold uppercase tracking-widest text-synchrony-slate mb-2">{f.tag}</p>
              <h3 className="text-xl font-bold text-synchrony-ink">{f.title}</h3>
              <p className="mt-2.5 text-[15px] text-synchrony-ink/60 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Trust stats band ── */}
      <section className="bg-synchrony-navy-dark">
        <div className="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 py-14 grid grid-cols-2 lg:grid-cols-4 gap-8">
          {TRUST_STATS.map((s) => (
            <div key={s.label}>
              <p className="text-3xl lg:text-4xl font-extrabold text-synchrony-gold">{s.value}</p>
              <p className="text-sm text-gray-300 mt-2">{s.label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA band (cream) ── */}
      <section className="bg-synchrony-cream">
        <div className="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 py-16 flex flex-col lg:flex-row items-center justify-between gap-6">
          <div>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-synchrony-ink tracking-tight">
              Ready to investigate?
            </h2>
            <p className="mt-3 text-lg text-synchrony-ink/60">
              Sign in to access the live fraud analytics dashboard.
            </p>
          </div>
          <button
            onClick={onRequestSignIn}
            className="flex items-center gap-2 bg-synchrony-gold hover:bg-synchrony-gold-hover
                       text-synchrony-ink font-bold text-lg px-9 py-4 rounded-full transition-colors shadow-sm whitespace-nowrap"
          >
            Sign in now
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="bg-white border-t border-gray-100 mt-auto">
        <div className="max-w-[1240px] mx-auto px-4 sm:px-6 lg:px-8 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <SynchronyLogo height={24} subLabel="ANALYTICS" />
          <p className="text-xs text-gray-400 text-center">
            © {new Date().getFullYear()} Synchrony Financial · Fraud Analytics Platform · Demo environment
          </p>
          <div className="flex items-center gap-5 text-xs font-medium text-gray-500">
            <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-synchrony-navy">Privacy</a>
            <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-synchrony-navy">Terms</a>
            <a href="#" onClick={(e) => e.preventDefault()} className="hover:text-synchrony-navy">Security</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
