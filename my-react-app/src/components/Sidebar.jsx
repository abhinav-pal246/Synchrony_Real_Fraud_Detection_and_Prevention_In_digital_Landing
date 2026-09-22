import { useState } from "react";

/* ---------- icon primitives (inline SVG, no external deps) ---------- */
const Icon = ({ path, size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
       stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d={path} />
  </svg>
);

const ICONS = {
  dashboard:     "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z M9 22V12h6v10",
  transactions:  "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  alerts:        "M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z M12 9v4 M12 17h.01",
  investigation: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  fraudRing:     "M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2 M9 11a4 4 0 100-8 4 4 0 000 8z M23 21v-2a4 4 0 00-3-3.87 M16 3.13a4 4 0 010 7.75",
  model:         "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  reports:       "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8",
  settings:      "M12 15a3 3 0 100-6 3 3 0 000 6z M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z",
};

const NAV_SECTIONS = [
  {
    label: "Main",
    items: [
      { id: "dashboard",    label: "Dashboard",          icon: "dashboard",    badge: null },
      { id: "transactions", label: "Live Transactions",  icon: "transactions", badge: "12.8k" },
      { id: "alerts",       label: "Fraud Alerts",       icon: "alerts",       badge: "23", badgeType: "critical" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { id: "investigation", label: "Account Investigation", icon: "investigation", badge: null },
      { id: "fraudRing",     label: "Fraud Ring Graph",      icon: "fraudRing",     badge: "5",  badgeType: "warning" },
      { id: "model",         label: "Model Metrics",         icon: "model",         badge: null },
    ],
  },
  {
    label: "System",
    items: [
      { id: "reports",  label: "Reports",  icon: "reports",  badge: null },
      { id: "settings", label: "Settings", icon: "settings", badge: null },
    ],
  },
];

const BADGE_STYLES = {
  critical: "bg-red-500 text-white",
  warning:  "bg-synchrony-yellow text-synchrony-navy-dark",
  default:  "bg-synchrony-navy-light text-gray-300",
};

export default function Sidebar({ collapsed = false }) {
  const [active, setActive] = useState("dashboard");

  return (
    <aside
      className={`fixed left-0 top-40 bottom-0 z-40 flex flex-col
                  bg-synchrony-navy-dark border-r border-synchrony-navy
                  transition-all duration-300 ease-in-out
                  ${collapsed ? "w-16" : "w-60"}`}
    >
      {/* Status pill */}
      {!collapsed && (
        <div className="px-4 pt-5 pb-3">
          <div className="flex items-center gap-2 bg-synchrony-navy rounded-lg px-3 py-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400" />
            </span>
            <span className="text-green-400 text-xs font-semibold">System Live</span>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-6">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-synchrony-slate px-2 mb-2">
                {section.label}
              </p>
            )}
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const isActive = active === item.id;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => setActive(item.id)}
                      title={collapsed ? item.label : undefined}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl
                                  text-sm font-medium transition-all duration-150
                                  ${isActive
                                    ? "bg-synchrony-yellow text-synchrony-navy-dark shadow-sm"
                                    : "text-synchrony-slate hover:bg-synchrony-navy hover:text-white"
                                  }
                                  ${collapsed ? "justify-center" : ""}`}
                    >
                      <Icon path={ICONS[item.icon]} size={18} />

                      {!collapsed && (
                        <>
                          <span className="flex-1 text-left">{item.label}</span>
                          {item.badge && (
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full leading-none
                                             ${BADGE_STYLES[item.badgeType ?? "default"]}`}>
                              {item.badge}
                            </span>
                          )}
                        </>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* Bottom user card */}
      {!collapsed && (
        <div className="p-3 border-t border-synchrony-navy">
          <div className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-synchrony-navy cursor-pointer transition">
            <div className="w-8 h-8 rounded-full bg-synchrony-yellow flex items-center justify-center
                            text-synchrony-navy-dark text-sm font-bold flex-shrink-0">
              A
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-semibold truncate">Analyst</p>
              <p className="text-synchrony-slate text-xs truncate">Fraud Operations</p>
            </div>
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="text-synchrony-slate flex-shrink-0">
              <path d="M2 5l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
      )}
    </aside>
  );
}
