import { useState, useEffect } from "react";
import RiskDashboard from "./components/RiskDashboard.jsx";

const THEMES = [
  { id: "midnight", color: "#6366f1" },
  { id: "arctic",   color: "#2563eb" },
  { id: "forest",   color: "#10b981" },
  { id: "plum",     color: "#a855f7" },
];

const INITIAL = {
  age: 26, income: 35000, employment_length: 1, credit_score: 560,
  existing_loans: 3, num_delinquencies: 4, credit_history_length: 2,
  loan_amount: 150000, loan_tenure: 36, interest_rate: 14,
  debt_to_income: 0.45, loan_purpose: "personal",
};

// Each field: label + validation bounds. Bounds match the backend schema so
// impossible values (like a 300-million loan) are caught before sending.
const FIELDS = {
  age: { label: "Age", min: 18, max: 100 },
  income: { label: "Annual income", min: 1, max: 100000000 },
  employment_length: { label: "Employment (years)", min: 0, max: 50 },
  credit_score: { label: "Credit score", min: 300, max: 850 },
  existing_loans: { label: "Existing loans", min: 0, max: 50 },
  num_delinquencies: { label: "Past delinquencies", min: 0, max: 50 },
  credit_history_length: { label: "Credit history (years)", min: 0, max: 80 },
  loan_amount: { label: "Loan amount", min: 1, max: 10000000 },
  loan_tenure: { label: "Loan tenure (months)", min: 1, max: 480 },
  interest_rate: { label: "Interest rate (%)", min: 1, max: 40 },
  debt_to_income: { label: "Debt-to-income", min: 0, max: 3, step: 0.01 },
};

const PURPOSES = ["home", "auto", "personal", "education", "business"];

export default function App() {
  const [theme, setTheme] = useState("midnight");
  const [form, setForm] = useState(INITIAL);
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(null);

  useEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);

  function validateField(field, value) {
    const cfg = FIELDS[field];
    if (!cfg) return null;
    if (value === "" || isNaN(value)) return "Required";
    if (value < cfg.min) return `Min ${cfg.min}`;
    if (value > cfg.max) return `Max ${cfg.max.toLocaleString()}`;
    return null;
  }

  function handleChange(field, raw) {
    const value = field === "loan_purpose" ? raw : Number(raw);
    setForm((p) => ({ ...p, [field]: value }));
    if (field !== "loan_purpose") {
      const err = validateField(field, value);
      setErrors((p) => ({ ...p, [field]: err }));
    }
  }

  async function handleSubmit() {
    // Validate everything first; block submit if anything is off.
    const newErrors = {};
    for (const f of Object.keys(FIELDS)) {
      const err = validateField(f, form[f]);
      if (err) newErrors[f] = err;
    }
    setErrors(newErrors);
    if (Object.keys(newErrors).length > 0) {
      setApiError("Please fix the highlighted fields before assessing.");
      return;
    }
    setApiError(null); setLoading(true); setResult(null);
    try {
      const res = await fetch("/api/credit-risk", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ? JSON.stringify(d.detail) : `Request failed (${res.status})`);
      }
      setResult(await res.json());
    } catch (err) {
      setApiError(
        err.message.includes("Failed to fetch")
          ? "Can't reach the API. Make sure the backend is running on port 8000."
          : err.message
      );
    } finally { setLoading(false); }
  }

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">
          <div className="brand-mark">R</div>
          <div>
            <div className="brand-name">RiskLens</div>
            <div className="brand-sub">Credit Risk Intelligence</div>
          </div>
        </div>
        <div className="themes">
          <span className="theme-label">Theme</span>
          {THEMES.map((t) => (
            <div
              key={t.id}
              className={`swatch ${theme === t.id ? "active" : ""}`}
              style={{ background: t.color }}
              onClick={() => setTheme(t.id)}
              title={t.id}
            />
          ))}
        </div>
      </div>

      {/* KPI row — reflects the current assessment when present */}
      <div className="kpi-row">
        <div className="kpi">
          <div className="kpi-label">Risk score</div>
          <div className="kpi-value">{result ? result.risk_score : "—"}</div>
          <div className={`kpi-trend ${result ? (result.risk_score > 50 ? "up" : "down") : "flat"}`}>
            {result ? (result.risk_score > 50 ? "Above threshold" : "Within tolerance") : "Awaiting input"}
          </div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Default probability</div>
          <div className="kpi-value">{result ? (result.default_probability * 100).toFixed(1) + "%" : "—"}</div>
          <div className="kpi-trend flat">{result ? "Calibrated estimate" : "Awaiting input"}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Decision</div>
          <div className="kpi-value" style={{ fontSize: "1.15rem" }}>{result ? result.approval : "—"}</div>
          <div className="kpi-trend flat">{result ? result.risk_category : "Awaiting input"}</div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Risk factors</div>
          <div className="kpi-value">{result ? result.reasons.length : "—"}</div>
          <div className="kpi-trend flat">{result ? "Flagged" : "Awaiting input"}</div>
        </div>
      </div>

      <div className="grid">
        {/* Form */}
        <div className="card">
          <div className="card-title"><span className="dot" />Applicant details</div>
          <div className="form-grid">
            {Object.keys(FIELDS).map((f) => (
              <div className="field" key={f}>
                <label>{FIELDS[f].label}</label>
                <input
                  type="number"
                  step={FIELDS[f].step || "any"}
                  value={form[f]}
                  className={errors[f] ? "invalid" : ""}
                  onChange={(e) => handleChange(f, e.target.value)}
                />
                <span className="hint">{errors[f] || ""}</span>
              </div>
            ))}
            <div className="field">
              <label>Loan purpose</label>
              <select value={form.loan_purpose} onChange={(e) => handleChange("loan_purpose", e.target.value)}>
                {PURPOSES.map((p) => <option key={p} value={p}>{p[0].toUpperCase() + p.slice(1)}</option>)}
              </select>
              <span className="hint"></span>
            </div>
          </div>
          <button className="btn" onClick={handleSubmit} disabled={loading}>
            {loading ? "Assessing…" : "Assess risk"}
          </button>
          {apiError && <div className="alert">{apiError}</div>}
        </div>

        {/* Result dashboard */}
        <div className="card">
          <div className="card-title"><span className="dot" />Assessment</div>
          {result ? (
            <RiskDashboard result={result} form={form} />
          ) : (
            <div className="result-empty">
              <div className="big-icon">◎</div>
              <div>Enter applicant details and run an assessment<br />to see the risk breakdown.</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
