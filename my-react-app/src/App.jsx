import { useState } from "react";
import "./styles.css";
import Navbar      from "./components/Navbar.jsx";
import Sidebar     from "./components/Sidebar.jsx";
import Dashboard   from "./components/Dashboard.jsx";
import Footer      from "./components/Footer.jsx";
import LandingPage from "./components/LandingPage.jsx";
import SignInModal from "./components/SignInModal.jsx";

export default function App() {
  // Auth state — the token comes from the real backend /auth/login (Postgres-backed).
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authToken, setAuthToken] = useState(null);
  const [analystEmail, setAnalystEmail] = useState(null);
  const [signInOpen, setSignInOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const handleSignIn = (token, email) => {
    setAuthToken(token);
    setAnalystEmail(email);
    setIsAuthenticated(true);
    setSignInOpen(false);
  };

  const handleSignOut = () => {
    setAuthToken(null);
    setAnalystEmail(null);
    setIsAuthenticated(false);
    setSidebarCollapsed(false);
  };

  /* ── Logged-out: landing page only, no analytics ── */
  if (!isAuthenticated) {
    return (
      <>
        <LandingPage onRequestSignIn={() => setSignInOpen(true)} />
        <SignInModal
          open={signInOpen}
          onClose={() => setSignInOpen(false)}
          onSignIn={handleSignIn}
        />
      </>
    );
  }

  /* ── Logged-in: full analytics dashboard ── */
  return (
    <div className="min-h-screen bg-synchrony-page-bg font-sans">
      <Navbar
        onMenuToggle={() => setSidebarCollapsed((p) => !p)}
        onSignOut={handleSignOut}
      />

      <div className="flex pt-40">
        <Sidebar collapsed={sidebarCollapsed} />

        <main
          className={`flex-1 flex flex-col min-h-[calc(100vh-10rem)]
                      transition-all duration-300
                      ${sidebarCollapsed ? "ml-16" : "ml-60"}`}
        >
          <div className="flex-1 p-6">
            <Dashboard token={authToken} analyst={analystEmail} />
          </div>
          <Footer />
        </main>
      </div>
    </div>
  );
}
