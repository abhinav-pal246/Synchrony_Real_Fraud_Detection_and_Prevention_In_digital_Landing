import { useState } from "react";
import SynchronyLogo from "./SynchronyLogo.jsx";

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

/* Real sign-in — authenticates against FastAPI /auth/login (credential in Postgres). */
export default function SignInModal({ open, onClose, onSignIn }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        const data = await res.json();
        onSignIn(data.access_token, email); // proceed with the real JWT
      } else {
        setError("Invalid email or password.");
      }
    } catch {
      setError("Cannot reach the server. Is the backend running on :8000?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-synchrony-navy-dark/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Card */}
      <div className="relative w-full max-w-md bg-white rounded-3xl shadow-2xl p-8 animate-[fadeIn_0.2s_ease-out]">
        {/* Close */}
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute top-5 right-5 p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Logo */}
        <div className="flex justify-center mb-6">
          <SynchronyLogo height={34} subLabel="ANALYTICS" />
        </div>

        <h2 className="text-xl font-bold text-synchrony-navy text-center">
          Sign in to your account
        </h2>
        <p className="text-sm text-gray-500 text-center mt-1 mb-6">
          Fraud Operations · Analyst access only
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Email */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
              Work email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="analyst@synchrony.com"
              className="w-full px-4 py-2.5 rounded-xl border border-gray-200 text-sm
                         focus:outline-none focus:ring-2 focus:ring-synchrony-yellow focus:border-transparent
                         transition"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5">
              Password
            </label>
            <div className="relative">
              <input
                type={showPw ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 pr-11 rounded-xl border border-gray-200 text-sm
                           focus:outline-none focus:ring-2 focus:ring-synchrony-yellow focus:border-transparent
                           transition"
              />
              <button
                type="button"
                onClick={() => setShowPw((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                aria-label="Toggle password visibility"
              >
                {showPw ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24M1 1l22 22" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Row */}
          <div className="flex items-center justify-between text-xs">
            <label className="flex items-center gap-2 text-gray-500 cursor-pointer">
              <input type="checkbox" className="rounded border-gray-300 text-synchrony-yellow focus:ring-synchrony-yellow" />
              Remember me
            </label>
            <a href="#" onClick={(e) => e.preventDefault()} className="text-synchrony-navy font-semibold hover:underline">
              Forgot password?
            </a>
          </div>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-synchrony-gold hover:bg-synchrony-gold-hover text-synchrony-ink
                       font-bold py-3 rounded-full transition-colors shadow-sm flex items-center justify-center gap-2
                       disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading ? "Signing in…" : "Sign In"}
            {!loading && (
              <svg width="16" height="16" viewBox="0 0 14 14" fill="none">
                <path d="M7 1L13 7M13 7L7 13M13 7H1" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )}
          </button>
        </form>

        <p className="text-[11px] text-gray-400 text-center mt-5">
          Protected by Synchrony IAM · Demo environment
        </p>
      </div>
    </div>
  );
}
