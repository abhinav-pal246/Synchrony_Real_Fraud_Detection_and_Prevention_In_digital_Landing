import { useState } from "react";
import SynchronyLogo from "./SynchronyLogo.jsx";

/* Left-hand primary nav items (analytics-relevant, styled like Synchrony's) */
const PRIMARY_LINKS = ["Overview", "Detection", "Investigation", "Reports"];
/* Right-hand utility links */
const UTILITY_LINKS = ["About Us", "Help"];

const Caret = () => (
  <svg width="10" height="10" viewBox="0 0 12 12" fill="none" className="mt-0.5 opacity-70">
    <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default function SynchronyTopNav({ onRequestSignIn }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-100 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <div className="w-full h-[94px] px-4 sm:px-8 lg:px-12 flex items-center justify-between">

        {/* ── Left: logo + primary nav ── */}
        <div className="flex items-center gap-8 xl:gap-12">
          <SynchronyLogo height={35} subLabel="ANALYTICS" />

          <nav className="hidden lg:flex items-center gap-7 xl:gap-9">
            {PRIMARY_LINKS.map((l) => (
              <a
                key={l}
                href="#"
                onClick={(e) => e.preventDefault()}
                className="flex items-center gap-1 text-[15px] font-bold uppercase tracking-wide
                           text-synchrony-ink hover:text-synchrony-navy transition-colors"
              >
                {l}
                <Caret />
              </a>
            ))}
          </nav>
        </div>

        {/* ── Right: utility links + search + sign in ── */}
        <div className="flex items-center gap-5 xl:gap-7">
          <nav className="hidden lg:flex items-center gap-6 xl:gap-7">
            {UTILITY_LINKS.map((l) => (
              <a
                key={l}
                href="#"
                onClick={(e) => e.preventDefault()}
                className="flex items-center gap-1 text-[15px] font-bold uppercase tracking-wide
                           text-synchrony-ink hover:text-synchrony-navy transition-colors"
              >
                {l}
                <Caret />
              </a>
            ))}
          </nav>

          {/* Search */}
          <button
            aria-label="Search"
            className="hidden sm:flex p-1.5 text-synchrony-ink hover:text-synchrony-navy transition-colors"
            onClick={(e) => e.preventDefault()}
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="7" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </button>

          {/* Sign in */}
          <button
            onClick={onRequestSignIn}
            className="flex items-center gap-2 bg-synchrony-gold hover:bg-synchrony-gold-hover
                       text-synchrony-ink text-[15px] font-bold px-6 py-2.5 rounded-full
                       transition-colors shadow-sm"
          >
            Sign in
            <Caret />
          </button>

          {/* Hamburger (mobile) */}
          <button
            onClick={() => setMobileOpen((s) => !s)}
            aria-label="Menu"
            className="lg:hidden p-1.5 rounded-md text-synchrony-ink hover:bg-gray-100 transition"
          >
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
              <path d="M3 6h18M3 12h18M3 18h18" />
            </svg>
          </button>
        </div>
      </div>

      {/* ── Mobile drawer ── */}
      {mobileOpen && (
        <nav className="lg:hidden border-t border-gray-100 bg-white px-4 sm:px-6 py-3 flex flex-col gap-1">
          {[...PRIMARY_LINKS, ...UTILITY_LINKS].map((l) => (
            <a
              key={l}
              href="#"
              onClick={(e) => { e.preventDefault(); setMobileOpen(false); }}
              className="flex items-center justify-between px-3 py-3 rounded-lg text-[15px] font-bold uppercase tracking-wide
                         text-synchrony-ink hover:bg-gray-50"
            >
              {l}
              <Caret />
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}
