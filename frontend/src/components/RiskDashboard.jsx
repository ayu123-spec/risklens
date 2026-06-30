import { Doughnut, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement,
} from "chart.js";
import { useCountUp } from "../useCountUp.js";

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

// Risk category -> color, used consistently across gauge, badges, and charts.
const CAT_COLOR = {
  "Very Low Risk": "#10b981",
  "Low Risk": "#84cc16",
  "Moderate Risk": "#eab308",
  "High Risk": "#f97316",
  "Very High Risk": "#ef4444",
  "Extreme Risk": "#b91c1c",
};
const APPROVAL_COLOR = {
  "Auto Approve": "#10b981",
  "Approve": "#65a30d",
  "Approve with Conditions": "#eab308",
  "Manual Review": "#f97316",
  "Reject or Require Collateral": "#ef4444",
  "Reject": "#b91c1c",
};

// A radial gauge: a doughnut filled proportionally to the score, colored by risk.
// The fill sweeps up and the number counts up for a premium feel.
function Gauge({ score, color }) {
  const animated = useCountUp(score, 1000);
  const data = {
    datasets: [{
      data: [animated, 100 - animated],
      backgroundColor: [color, "rgba(128,128,128,0.15)"],
      borderWidth: 0,
      borderRadius: animated > 2 ? 6 : 0,
      circumference: 270,
      rotation: 225,
      cutout: "78%",
    }],
  };
  const opts = {
    responsive: true, maintainAspectRatio: false,
    animation: false, // we drive the sweep ourselves via the count-up value
    plugins: { tooltip: { enabled: false }, legend: { display: false } },
  };
  return (
    <div className="gauge-wrap">
      <div style={{ width: 200, height: 150 }}>
        <Doughnut data={data} options={opts} />
      </div>
      <div className="gauge-score" style={{ color }}>{animated}</div>
      <div className="gauge-cat" style={{ color }}>Risk score / 100</div>
    </div>
  );
}

export default function RiskDashboard({ result, form }) {
  const color = CAT_COLOR[result.risk_category] || "#6366f1";
  const approvalColor = APPROVAL_COLOR[result.approval] || "#6366f1";

  // Factor strength chart: shows the applicant's flagged factors. Bar length is
  // a simple severity heuristic per factor so the chart conveys relative weight.
  const factorWeights = {
    "High debt-to-income ratio": Math.min((form.debt_to_income / 0.5) * 100, 100),
    "Low credit score": Math.min(((650 - form.credit_score) / 350) * 100, 100),
    "Multiple past delinquencies": Math.min((form.num_delinquencies / 6) * 100, 100),
    "Short credit history": Math.min(((5 - form.credit_history_length) / 5) * 100, 100),
    "Loan priced at high interest rate": Math.min(((form.interest_rate - 12) / 16) * 100, 100),
    "No major risk factors detected": 5,
  };
  const factorLabels = result.reasons;
  const factorData = {
    labels: factorLabels,
    datasets: [{
      data: factorLabels.map((r) => Math.max(factorWeights[r] || 30, 8)),
      backgroundColor: color,
      borderRadius: 6,
      barThickness: 18,
    }],
  };
  const factorOpts = {
    indexAxis: "y", responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `severity ${Math.round(c.raw)}/100` } } },
    scales: {
      x: { min: 0, max: 100, grid: { color: "rgba(128,128,128,0.12)" }, ticks: { display: false } },
      y: { grid: { display: false }, ticks: { color: getComputedStyle(document.documentElement).getPropertyValue("--muted"), font: { size: 11 } } },
    },
  };

  // Probability split: a clear repaid-vs-default doughnut.
  const probPct = Math.round(result.default_probability * 100);
  const splitData = {
    labels: ["Default risk", "Repayment likelihood"],
    datasets: [{
      data: [probPct, 100 - probPct],
      backgroundColor: [color, "rgba(128,128,128,0.18)"],
      borderWidth: 0,
      cutout: "68%",
    }],
  };
  const splitOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: (c) => `${c.label}: ${c.raw}%` } } },
  };

  return (
    <div className="result-stack">
      <div className="result-top">
        <Gauge score={result.risk_score} color={color} />
        <div>
          <div className="badges">
            <span className="badge" style={{ background: color }}>{result.risk_category}</span>
            <span className="badge" style={{ background: approvalColor }}>{result.approval}</span>
            <span className="badge" style={{ background: "var(--surface-2)", color: "var(--ink)", border: "1px solid var(--border)" }}>
              Grade {result.risk_grade}
            </span>
          </div>
          <div className="summary-line">{result.summary}</div>
          <div className="decision-metrics">
            <div className="metric">
              <span className="metric-label">Suggested rate</span>
              <span className="metric-val">{result.suggested_interest_rate > 0 ? result.suggested_interest_rate + "%" : "—"}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Max eligible</span>
              <span className="metric-val">{result.max_eligible_loan > 0 ? "₹" + result.max_eligible_loan.toLocaleString() : "—"}</span>
            </div>
            <div className="metric">
              <span className="metric-label">Confidence</span>
              <span className="metric-val">{result.confidence}%</span>
            </div>
          </div>
        </div>
      </div>

      <div className="chart-grid">
        <div>
          <div className="factor-head">Contributing factors</div>
          <div className="chart-box">
            <Bar data={factorData} options={factorOpts} />
          </div>
        </div>
        <div>
          <div className="factor-head">Probability split</div>
          <div className="chart-box" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ width: 180, height: 180, position: "relative" }}>
              <Doughnut data={splitData} options={splitOpts} />
              <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
                <div style={{ fontFamily: "Space Grotesk", fontWeight: 700, fontSize: "1.5rem", color }}>{probPct}%</div>
                <div style={{ fontSize: "0.7rem", color: "var(--muted)" }}>default</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
