import { useState } from "react";
import { apiPost } from "../api.js";
import RiskDashboard from "../components/RiskDashboard.jsx";

const INITIAL = {
  age: 30, income: 35000, employment_length: 5, credit_score: 701,
  existing_loans: 1, num_delinquencies: 2, credit_history_length: 2,
  loan_amount: 150000, loan_tenure: 36, interest_rate: 10,
  debt_to_income: 0.45, loan_purpose: "personal",
};
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

export default function AssessPage() {
  const [form, setForm] = useState(INITIAL);
  const [errors, setErrors] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState(null);

  function validate(f, v) {
    const c = FIELDS[f]; if (!c) return null;
    if (v === "" || isNaN(v)) return "Required";
    if (v < c.min) return `Min ${c.min}`;
    if (v > c.max) return `Max ${c.max.toLocaleString()}`;
    return null;
  }
  function handleChange(f, raw) {
    const v = f === "loan_purpose" ? raw : Number(raw);
    setForm((p) => ({ ...p, [f]: v }));
    if (f !== "loan_purpose") setErrors((p) => ({ ...p, [f]: validate(f, v) }));
  }
  async function handleSubmit() {
    const errs = {};
    for (const f of Object.keys(FIELDS)) { const e = validate(f, form[f]); if (e) errs[f] = e; }
    setErrors(errs);
    if (Object.keys(errs).length) { setApiError("Fix the highlighted fields before assessing."); return; }
    setApiError(null); setLoading(true); setResult(null);
    try { setResult(await apiPost("/api/credit-risk", form)); }
    catch (err) {
      setApiError(err.message.includes("Failed to fetch")
        ? "Can't reach the API. Make sure the backend is running." : err.message);
    } finally { setLoading(false); }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow"><span className="pulse" />Single applicant</div>
        <h1 className="page-title">Assess risk</h1>
        <p className="page-desc">
          Enter an applicant's details for an instant credit-risk assessment —
          score, grade, recommendation, and the factors behind it. Every
          assessment is stored and feeds the analytics.
        </p>
      </div>
      <div className="assess-grid">
        <div className="card">
          <div className="card-title"><span className="dot" />Applicant details</div>
          <div className="form-grid">
            {Object.keys(FIELDS).map((f) => (
              <div className="field" key={f}>
                <label>{FIELDS[f].label}</label>
                <input type="number" step={FIELDS[f].step || "any"} value={form[f]}
                  className={errors[f] ? "invalid" : ""}
                  onChange={(e) => handleChange(f, e.target.value)} />
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
        <div className="card">
          <div className="card-title"><span className="dot" />Assessment</div>
          {result ? <RiskDashboard result={result} form={form} /> : (
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
