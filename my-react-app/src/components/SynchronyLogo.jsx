/* ─────────────────────────────────────────────
   SynchronyLogo.jsx
   Official Synchrony logo (supplied brand asset, served from /public)
   + optional "ANALYTICS" sub-label to keep the "Synchrony Analytics" branding.
   ───────────────────────────────────────────── */

export default function SynchronyLogo({
  height = 30,               // pixel height of the logo image
  subLabel = null,           // optional label beside the wordmark, e.g. "ANALYTICS"
  subLabelColor = "#6B7A99",
}) {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <img
        src="/synchrony-logo.png"
        alt="Synchrony"
        style={{ height }}
        className="w-auto block"
        draggable="false"
      />
      {subLabel && (
        <>
          <span
            className="w-px bg-gray-300 self-center"
            style={{ height: Math.round(height * 0.7) }}
          />
          <span
            className="text-[11px] font-bold uppercase tracking-[0.18em]"
            style={{ color: subLabelColor }}
          >
            {subLabel}
          </span>
        </>
      )}
    </div>
  );
}
