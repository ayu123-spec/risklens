import { Doughnut, Bar } from "react-chartjs-2";
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement);

// Risk category -> color, used consistently across gauge, badges, and charts.
const CAT_COLOR = {
  "Very Low Risk": "#10b981",
  "Low Risk": "#84cc16",
  "Medium Risk": "#f59e0b",
  "High Risk": "#f97316",
  "Critical Risk": "#ef4444",
};
const APPROVAL_COLOR = {
  "Approved": "#10b981",
  "Approved with Conditions": "#f59e0b",
  "Manual Review": "#f97316",
  "Rejected": "#ef4444",
};

// A radial gauge: a doughnut filled proportionally to the score, colored by risk.
function Gauge({ score, color }) {
  const data = {
    datasets: [{
      data: [score, 100 - score],
      backgroundColor: [color, "rgba(128,128,128,0.15)"],
      borderWidth: 0,
      borderRadius: score > 2 ? 6 : 0,
      circumference: 270,
      rotation: 225,
      cutout: "78%",
    }],
  };
  const opts = { responsive: true, maintainAspectRatio: false, plugins: { tooltip: { enabled: false }, legend: { display: false } } };
  return (
    <div className="gauge-wrap">
      <div style={{ width: 200, height: 150 }}>
        <Doughnut data={data} options={opts} />
      </div>
      <div className="gauge-score" style={{ color }}>{score}</div>
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
          </div>
          <div className="summary-line">
            Estimated default probability of <strong>{(result.default_probability * 100).toFixed(1)}%</strong>,
            placing this applicant in the <strong>{result.risk_category.replace(" Risk", "")}</strong> band.
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
