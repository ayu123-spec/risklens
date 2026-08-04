import { Routes, Route, NavLink, Link, useLocation } from "react-router-dom";

import LandingPage from "./pages/LandingPage.jsx";
import AssessPage from "./pages/AssessPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import FraudScorePage from "./pages/FraudScorePage.jsx";
import FraudModelPage from "./pages/FraudModelPage.jsx";

/**
 * The nav adapts to which capability you're inside. Credit pages get the credit
 * links in electric blue; fraud pages get the fraud links in amber. The landing
 * page has no nav at all — it IS the chooser.
 */
function Nav({ capability }) {
  const isFraud = capability === "fraud";
  const links = isFraud
    ? [{ to: "/fraud", label: "Score transactions", end: true },
       { to: "/fraud/model", label: "Model card" }]
    : [{ to: "/credit", label: "Assess", end: true },
       { to: "/credit/analytics", label: "Analytics" },
       { to: "/credit/history", label: "History" }];

  return (
    <nav className="nav">
      <Link to="/" className="nav-brand">
        <div className={`nav-mark ${isFraud ? "amber" : ""}`}>R</div>
        <div>
          <div className="nav-name">RiskLens</div>
          <div className="nav-sub">
            {isFraud ? "Fraud Detection" : "Credit Risk Intelligence"}
          </div>
        </div>
      </Link>
      <div className="nav-links">
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) =>
              `nav-link ${isActive ? "active" : ""} ${isFraud ? "amber" : ""}`
            }
          >
            {l.label}
          </NavLink>
        ))}
        <Link to="/" className="nav-back">← All capabilities</Link>
      </div>
    </nav>
  );
}

function Shell({ capability, children }) {
  return (
    <div className="shell">
      <Nav capability={capability} />
      {children}
    </div>
  );
}

export default function App() {
  const { pathname } = useLocation();

  // The landing page is full-bleed with no nav.
  if (pathname === "/") {
    return (
      <Routes>
        <Route path="/" element={<LandingPage />} />
      </Routes>
    );
  }

  const capability = pathname.startsWith("/fraud") ? "fraud" : "credit";

  return (
    <Shell capability={capability}>
      <Routes>
        <Route path="/credit" element={<AssessPage />} />
        <Route path="/credit/analytics" element={<AnalyticsPage />} />
        <Route path="/credit/history" element={<HistoryPage />} />
        <Route path="/fraud" element={<FraudScorePage />} />
        <Route path="/fraud/model" element={<FraudModelPage />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Shell>
  );
}

function NotFound() {
  return (
    <div className="page">
      <div className="empty-state">
        <div className="big-icon">◌</div>
        <div>That page doesn't exist.</div>
        <div style={{ marginTop: "0.6rem" }}>
          <Link to="/">Back to capabilities →</Link>
        </div>
      </div>
    </div>
  );
}
