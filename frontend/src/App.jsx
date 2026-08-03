import { Routes, Route, NavLink, Link } from "react-router-dom";
import AssessPage from "./pages/AssessPage.jsx";
import AnalyticsPage from "./pages/AnalyticsPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";

function Nav() {
  return (
    <nav className="nav">
      <Link to="/" className="nav-brand">
        <div className="nav-mark">R</div>
        <div>
          <div className="nav-name">RiskLens</div>
          <div className="nav-sub">Credit Risk Intelligence</div>
        </div>
      </Link>
      <div className="nav-links">
        <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          Assess
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          Analytics
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
          History
        </NavLink>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <div className="shell">
      <Nav />
      <Routes>
        <Route path="/" element={<AssessPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Routes>
    </div>
  );
}
