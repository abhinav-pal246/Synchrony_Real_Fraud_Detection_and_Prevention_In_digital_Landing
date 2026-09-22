import { useState, useEffect, useCallback } from "react";

/* Free-license Unsplash photos (hotlinked from Unsplash CDN, not bundled).
   Themes: technology / data, analytics, financial markets, fintech security, finance. */
const U = (id) => `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=1920&q=80`;

const SLIDES = [
  {
    img: U("1518186285589-2f7649de83e0"),
    eyebrow: "Real-time streaming",
    title: "Detecting fraud before it moves",
    text: "Every transaction across the digital lending ecosystem, scored the instant it arrives.",
  },
  {
    img: U("1460925895917-afdab827c52f"),
    eyebrow: "Analytics intelligence",
    title: "Intelligence that never sleeps",
    text: "Rule engines, machine learning, and graph analysis working together — 24 / 7.",
  },
  {
    img: U("1611974789855-9c2a0a7236a3"),
    eyebrow: "Scale & coverage",
    title: "Protecting 70M+ accounts",
    text: "235 million transactions a month, $180 billion in volume, one detection pipeline.",
  },
  {
    img: U("1642790106117-e829e14a795f"),
    eyebrow: "Network defense",
    title: "Stop fraud rings before they scale",
    text: "Uncover synthetic identities and collusive merchants hiding across accounts.",
  },
  {
    img: U("1554260570-9140fd3b7614"),
    eyebrow: "Explainable AI",
    title: "Insight your analysts can trust",
    text: "Every alert comes with a plain-language reason — transparent, auditable, actionable.",
  },
];

const INTERVAL = 2500;

export default function HeroCarousel({ onRequestSignIn }) {
  const [current, setCurrent] = useState(0);
  const [paused, setPaused] = useState(false);

  const go = useCallback((i) => setCurrent(((i % SLIDES.length) + SLIDES.length) % SLIDES.length), []);
  const next = useCallback(() => setCurrent((c) => (c + 1) % SLIDES.length), []);
  const prev = useCallback(() => setCurrent((c) => (c - 1 + SLIDES.length) % SLIDES.length), []);

  useEffect(() => {
    if (paused) return;
    const t = setInterval(next, INTERVAL);
    return () => clearInterval(t);
  }, [paused, next]);

  return (
    <section
      className="relative w-full h-[64vh] min-h-[460px] max-h-[720px] overflow-hidden bg-synchrony-navy-dark"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-roledescription="carousel"
    >
      {/* ── Slides (cross-fade) ── */}
      {SLIDES.map((s, i) => {
        const active = i === current;
        return (
          <div
            key={i}
            className={`absolute inset-0 transition-opacity duration-700 ease-in-out
                        ${active ? "opacity-100 z-10" : "opacity-0 z-0"}`}
            aria-hidden={!active}
          >
            {/* image */}
            <img
              src={s.img}
              alt=""
              draggable="false"
              className={`absolute inset-0 w-full h-full object-cover select-none ${active ? "animate-kenburns" : ""}`}
            />
            {/* dark gradient overlay for legibility */}
            <div className="absolute inset-0 bg-gradient-to-r from-synchrony-navy-dark/90 via-synchrony-navy-dark/60 to-synchrony-navy-dark/20" />
            <div className="absolute inset-0 bg-gradient-to-t from-synchrony-navy-dark/70 via-transparent to-transparent" />
          </div>
        );
      })}

      {/* ── Foreground content ── */}
      <div className="relative z-20 h-full w-full px-4 sm:px-8 lg:px-12 flex items-center">
        <div key={current} className="max-w-xl animate-hero-up">
          <span className="inline-flex items-center gap-2 text-synchrony-gold text-xs sm:text-sm font-bold uppercase tracking-[0.2em] mb-4">
            <span className="w-8 h-px bg-synchrony-gold" />
            {SLIDES[current].eyebrow}
          </span>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-white leading-[1.02] tracking-tight">
            {SLIDES[current].title}
          </h1>
          <p className="mt-5 text-base sm:text-lg text-gray-200 max-w-lg leading-relaxed">
            {SLIDES[current].text}
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-3">
            <button
              onClick={onRequestSignIn}
              className="flex items-center justify-center gap-2 bg-synchrony-gold hover:bg-synchrony-gold-hover
                         text-synchrony-ink font-bold text-base px-7 py-3.5 rounded-full transition-colors shadow-lg"
            >
              Sign in to Dashboard
            </button>
            <button
              onClick={(e) => e.preventDefault()}
              className="flex items-center justify-center gap-2 bg-white/10 backdrop-blur border border-white/30
                         text-white font-semibold text-base px-7 py-3.5 rounded-full hover:bg-white/20 transition-colors"
            >
              Explore the platform
            </button>
          </div>
        </div>
      </div>

      {/* ── Prev / Next arrows ── */}
      <button
        onClick={prev}
        aria-label="Previous slide"
        className="absolute left-3 sm:left-5 top-1/2 -translate-y-1/2 z-30 w-11 h-11 rounded-full
                   bg-white/15 hover:bg-white/30 backdrop-blur text-white flex items-center justify-center transition"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 18l-6-6 6-6" />
        </svg>
      </button>
      <button
        onClick={next}
        aria-label="Next slide"
        className="absolute right-3 sm:right-5 top-1/2 -translate-y-1/2 z-30 w-11 h-11 rounded-full
                   bg-white/15 hover:bg-white/30 backdrop-blur text-white flex items-center justify-center transition"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 18l6-6-6-6" />
        </svg>
      </button>

      {/* ── Pill indicators (Synchrony-style) ── */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30
                      flex items-center gap-2 bg-black/35 backdrop-blur rounded-full px-4 py-2.5">
        {SLIDES.map((_, i) => (
          <button
            key={i}
            onClick={() => go(i)}
            aria-label={`Go to slide ${i + 1}`}
            className={`h-2 rounded-full transition-all duration-300
                        ${i === current ? "w-7 bg-synchrony-gold" : "w-2 bg-white/50 hover:bg-white/80"}`}
          />
        ))}
      </div>
    </section>
  );
}
