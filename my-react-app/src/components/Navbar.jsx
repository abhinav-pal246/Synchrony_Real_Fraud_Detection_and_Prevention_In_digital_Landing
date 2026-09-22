import { useState } from "react";
import SynchronyLogo from "./SynchronyLogo.jsx";

const NAV_LINKS = [
  { label: "Overview",      href: "#" },
  { label: "Transactions",  href: "#" },
  { label: "Fraud Alerts",  href: "#" },
  { label: "Investigation", href: "#" },
  { label: "Reports",       href: "#" },
];

export default function Navbar({ onMenuToggle, onSignOut }) {
  const [activeLink, setActiveLink] = useState("Overview");
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleMenuToggle = () => {
    setMobileOpen((prev) => !prev);
    if (onMenuToggle) onMenuToggle();
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-white border-b border-gray-200 shadow-sm">
      <div className="flex items-center justify-between h-40 px-4 sm:px-8 lg:px-12">

        {/* ── LEFT: hamburger (mobile) + nav links (desktop) ── */}
        <div className="flex items-center gap-6">
          {/* Hamburger — mobile only */}
          <button
            onClick={handleMenuToggle}
            aria-label="Toggle menu"
            className="md:hidden p-2 rounded-lg hover:bg-gray-100 text-gray-500 transition"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <rect y="3"  width="20" height="2" rx="1" />
              <rect y="9"  width="20" height="2" rx="1" />
              <rect y="15" width="20" height="2" rx="1" />
            </svg>
          </button>

          {/* Desktop nav links */}
          <nav className="hidden md:flex items-center gap-1">
            {NAV_LINKS.map((link) => (
              <a
                key={link.label}
                href={link.href}
                onClick={(e) => { e.preventDefault(); setActiveLink(link.label); }}
                className={`nav-link px-3 py-1.5 rounded-md transition-all duration-150 ${
                  activeLink === link.label
                    ? "text-synchrony-navy font-semibold bg-gray-100"
                    : "text-gray-500 hover:text-synchrony-navy hover:bg-gray-50"
                }`}
              >
                {link.label}
              </a>
            ))}
          </nav>
        </div>

        {/* ── RIGHT: Logo + brand name + Sign Out ── */}
        <div className="flex items-center gap-4">
          {/* Brand cluster */}
          <SynchronyLogo height={44} subLabel="ANALYTICS" />

          {/* Divider */}
          <div className="hidden sm:block w-px h-7 bg-gray-200" />

          {/* Sign Out */}
          <button
            onClick={onSignOut}
            className="flex items-center gap-2 bg-gray-100 hover:bg-gray-200
                       text-synchrony-navy text-sm font-semibold px-4 py-2 rounded-full
                       transition-colors duration-150"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" />
            </svg>
            Sign Out
          </button>
        </div>
      </div>

      {/* ── MOBILE nav dropdown ── */}
      {mobileOpen && (
        <nav className="md:hidden border-t border-gray-100 bg-white px-4 py-3 flex flex-col gap-1">
          {NAV_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              onClick={(e) => { e.preventDefault(); setActiveLink(link.label); setMobileOpen(false); }}
              className={`block px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150 ${
                activeLink === link.label
                  ? "bg-synchrony-yellow text-synchrony-navy-dark font-semibold"
                  : "text-gray-600 hover:bg-gray-50"
              }`}
            >
              {link.label}
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}
