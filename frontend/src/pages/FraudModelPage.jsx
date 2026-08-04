import { useEffect, useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement,
  LineElement, Tooltip, Legend, Filler,
} from "chart.js";
import { apiGet } from "../api.js";
import { CHART_COLORS } from "../chartTheme.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

function Kpi({ label, value, trend }) {
  return (
    <div className="kpi">
      <div className="kpi-icon amber">◉</div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {trend && <div className="kpi-trend">{trend}</div>}
    </div>
  );
}

export default function FraudModelPage() {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet("/api/fraud/model-info")
      .then((d) => (d.available ? setInfo(d) : setError(d.error || "Model unavailable")))
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="page">
        <div className="empty-state">
          <div className="big-icon">⚠</div>
          <div>Can't load the model card.</div>
          <div style={{ fontSize: ".8rem", marginTop: ".5rem" }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!info) {
    return (
      <div className="page">
        <div className="loading"><div className="spinner amber" />Loading model card…</div>
      </div>
    );
  }

  // Recall vs false alarms across the threshold sweep.
  const t = [...info.thresholds].sort((a, b) => b.threshold - a.threshold);
  const tradeoff = {
    labels: t.map((r) => r.threshold),
    datasets: [
      {
        label: "Recall (fraud caught)",
        data: t.map((r) => r.recall * 100),
        borderColor: CHART_COLORS.amber,
        backgroundColor: "rgba(245,158,11,0.12)",
        fill: true, tension: 0.35, pointRadius: 4, yAxisID: "y",
      },
      {
        label: "False alarms",
        data: t.map((r) => r.false_alarms),
        borderColor: CHART_COLORS.danger,
        backgroundColor: "transparent",
        borderDash: [5, 4], tension: 0.35, pointRadius: 4, yAxisID: "y1",
      },
    ],
  };
  const tradeoffOpts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { legend: { labels: { color: CHART_COLORS.text, font: { size: 11 } } } },
    scales: {
      x: {
        grid: { color: CHART_COLORS.grid },
        ticks: { color: CHART_COLORS.text, font: { size: 11 } },
        title: { display: true, text: "Decision threshold", color: CHART_COLORS.text, font: { size: 11 } },
      },
      y: {
        position: "left", min: 0, max: 100,
        grid: { color: CHART_COLORS.grid },
        ticks: { color: CHART_COLORS.amber, font: { size: 11 }, callback: (v) => v + "%" },
      },
      y1: {
        position: "right", beginAtZero: true,
        grid: { display: false },
        ticks: { color: CHART_COLORS.danger, font: { size: 11 } },
      },
    },
  };

  const maxImp = Math.max(...info.top_features.map((f) => f.importance));

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow"><span className="pulse amber" />Model card</div>
        <h1 className="page-title amber">Fraud model</h1>
        <p className="page-desc">
          How this model actually performs — including where it fails. {info.algorithm},
          trained on {info.dataset}.
        </p>
      </div>

      <div className="kpi-grid">
        <Kpi label="PR-AUC" value={info.pr_auc} trend="the metric that matters here" />
        <Kpi label="ROC-AUC" value={info.roc_auc} trend="less meaningful when imbalanced" />
        <Kpi label="Class imbalance" value={`${info.imbalance_ratio}:1`} trend="legitimate : fraud" />
        <Kpi
          label="Fraud rate"
          value={`${(info.fraud_rate * 100).toFixed(3)}%`}
          trend={`${info.n_fraud} of ${info.n_transactions.toLocaleString()}`}
        />
      </div>

      <div className="card" style={{ marginBottom: "1.25rem" }}>
        <div className="card-title"><span className="dot amber" />Recall vs false alarms</div>
        <div className="chart-box tall"><Line data={tradeoff} options={tradeoffOpts} /></div>
        <div className="note-box">
          Lowering the threshold catches more fraud but raises false alarms. The
          platform runs at <strong>{info.default_threshold}</strong>, chosen because a
          missed fraud costs the full transaction value while a false alarm costs
          only a verification message.
        </div>
      </div>

      <div className="chart-grid-2">
        <div className="card">
          <div className="card-title"><span className="dot amber" />Operating points</div>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Threshold</th><th>Recall</th><th>Precision</th>
                  <th>Caught</th><th>False alarms</th>
                </tr>
              </thead>
              <tbody>
                {t.map((r) => (
                  <tr key={r.threshold} className={r.threshold === info.default_threshold ? "highlight" : ""}>
                    <td style={{ fontFamily: "Space Grotesk", fontWeight: 600 }}>{r.threshold}</td>
                    <td style={{ color: "var(--amber)" }}>{Math.round(r.recall * 100)}%</td>
                    <td style={{ color: "var(--muted)" }}>{Math.round(r.precision * 100)}%</td>
                    <td>{r.caught}/{r.total_fraud}</td>
                    <td style={{ color: "var(--faint)" }}>{r.false_alarms}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="card">
          <div className="card-title"><span className="dot amber" />Top predictors</div>
          {info.top_features.map((f) => (
            <div className="feature-bar-row" key={f.feature}>
              <div className="feature-name">{f.feature}</div>
              <div className="feature-track">
                <div className="feature-fill" style={{ width: `${(f.importance / maxImp) * 100}%` }} />
              </div>
              <div className="feature-val">{f.importance.toFixed(3)}</div>
            </div>
          ))}
          <div className="note-box">
            V1–V28 are PCA components — the original transaction fields were
            anonymised for privacy, so they carry no human-readable meaning.
            <strong> Amount_log</strong> is engineered here: fraud amounts are heavily
            skewed, and the log transform surfaces that signal.
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: "1.25rem" }}>
        <div className="card-title"><span className="dot amber" />Honest limitations</div>
        <div style={{ color: "var(--muted)", fontSize: ".9rem", lineHeight: 1.75 }}>
          <p style={{ marginBottom: ".7rem" }}>
            <strong style={{ color: "var(--ink)" }}>Accuracy is a useless metric here.</strong>{" "}
            Predicting "never fraud" for every transaction scores 99.83% accuracy and
            catches nothing. PR-AUC and recall are what matter.
          </p>
          <p style={{ marginBottom: ".7rem" }}>
            <strong style={{ color: "var(--ink)" }}>The features are anonymised.</strong>{" "}
            Real deployment would use interpretable signals — merchant category,
            velocity, geography, device — which also makes decisions explainable to
            customers and regulators.
          </p>
          <p>
            <strong style={{ color: "var(--ink)" }}>Fraud patterns drift.</strong>{" "}
            This model reflects two days of 2013 European transactions. Production
            systems retrain continuously as tactics change.
          </p>
        </div>
      </div>
    </div>
  );
}
