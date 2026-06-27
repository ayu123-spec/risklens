// RiskResult.jsx — a "presentational" component. It takes the API result as a
// prop and just displays it. Splitting this out from App keeps each file small
// and is the standard React way to compose a UI from pieces.

// Map each risk category to a color, so High/Critical look alarming and
// Low/Very Low look safe. This is the kind of visual cue a real risk dashboard
// uses.
const CATEGORY_COLORS = {
  "Very Low Risk": "#16a34a",
  "Low Risk": "#65a30d",
  "Medium Risk": "#ca8a04",
  "High Risk": "#ea580c",
  "Critical Risk": "#dc2626",
};

const APPROVAL_COLORS = {
  Approved: "#16a34a",
  "Approved with Conditions": "#ca8a04",
  "Manual Review": "#ea580c",
  Rejected: "#dc2626",
};

export default function RiskResult({ result }) {
  const color = CATEGORY_COLORS[result.risk_category] || "#64748b";
  const approvalColor = APPROVAL_COLORS[result.approval] || "#64748b";

  return (
    <div className="result">
      {/* The big score, colored by risk level */}
      <div className="score-block">
        <div className="score" style={{ color }}>
          {result.risk_score}
        </div>
        <div className="score-label">Risk Score / 100</div>
      </div>

      {/* A simple bar that fills proportionally to the score */}
      <div className="gauge">
        <div
          className="gauge-fill"
          style={{ width: `${result.risk_score}%`, background: color }}
        />
      </div>

      {/* Category and approval badges */}
      <div className="badges">
        <span className="badge" style={{ background: color }}>
          {result.risk_category}
        </span>
        <span className="badge" style={{ background: approvalColor }}>
          {result.approval}
        </span>
      </div>

      <div className="probability">
        Default probability:{" "}
        <strong>{(result.default_probability * 100).toFixed(1)}%</strong>
      </div>

      {/* The reasons behind the decision */}
      <div className="reasons">
        <h3>Key Factors</h3>
        <ul>
          {result.reasons.map((reason, i) => (
            <li key={i}>{reason}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
