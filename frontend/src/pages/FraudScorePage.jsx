import { useEffect, useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip } from "chart.js";
import { Link } from "react-router-dom";
import { apiGet, apiPost } from "../api.js";
import { fraudBandColor } from "../chartTheme.js";

ChartJS.register(ArcElement, Tooltip);

/** Ring showing the fraud probability. Deliberately non-linear near zero so a
 *  0.0001 result still reads as "essentially nothing" rather than an empty ring. */
function ProbRing({ probability, color }) {
  const pct = probability * 100;
  const shown = Math.max(pct, 0.4);
  const data = {
    datasets: [{
      data: [shown, 100 - shown],
      backgroundColor: [color, "rgba(128,128,128,0.14)"],
      borderWidth: 0, cutout: "76%", circumference: 360, rotation: 0,
    }],
  };
  const opts = {
    responsive: true, maintainAspectRatio: false,
    plugins: { tooltip: { enabled: false }, legend: { display: false } },
  };
  return (
    <div className="prob-ring">
      <Doughnut data={data} options={opts} />
      <div className="prob-ring-inner">
        <div className="prob-val" style={{ color }}>
          {pct >= 1 ? pct.toFixed(1) : pct.toFixed(2)}%
        </div>
        <div className="prob-lbl">fraud risk</div>
      </div>
    </div>
  );
}

export default function FraudScorePage() {
  const [samples, setSamples] = useState(null);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [threshold, setThreshold] = useState(0.10);
  const [scoring, setScoring] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet("/api/fraud/samples")
      .then((d) => setSamples(d.samples))
      .catch((e) => setError(e.message));
  }, []);

  // Re-score whenever the selection OR the threshold changes — moving the slider
  // re-evaluates the same transaction at a new operating point.
  useEffect(() => {
    if (selected === null) return;
    setScoring(true);
    apiPost(`/api/fraud/score/${selected}?threshold=${threshold}`)
      .then(setResult)
      .catch((e) => setError(e.message))
      .finally(() => setScoring(false));
  }, [selected, threshold]);

  if (error) {
    return (
      <div className="page">
        <div className="empty-state">
          <div className="big-icon">⚠</div>
          <div>Can't reach the fraud service.</div>
          <div style={{ fontSize: ".8rem", marginTop: ".5rem" }}>{error}</div>
        </div>
      </div>
    );
  }

  if (!samples) {
    return (
      <div className="page">
        <div className="loading"><div className="spinner amber" />Loading transactions…</div>
      </div>
    );
  }

  const color = result ? fraudBandColor(result.risk_band) : "#9a9aa8";
  const gt = result?.ground_truth;

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow"><span className="pulse amber" />Live transaction scoring</div>
        <h1 className="page-title amber">Fraud Detection</h1>
        <p className="page-desc">
          Nine real transactions from the held-out test set — the model has never
          seen them. Pick one to score it live, then move the decision threshold
          and watch the verdict change. The ground truth is revealed only after
          the model has committed.
        </p>
      </div>

      <div className="txn-grid">
        {/* ---- transaction list + threshold ---- */}
        <div>
          <div className="card">
            <div className="card-title"><span className="dot amber" />Transactions</div>
            <div className="txn-list">
              {samples.map((s) => (
                <button
                  key={s.id}
                  className={`txn ${selected === s.id ? "selected" : ""}`}
                  onClick={() => setSelected(s.id)}
                >
                  <div className="txn-num">{s.id}</div>
                  <div className="txn-body">
                    <div className="txn-amount">€{s.amount.toFixed(2)}</div>
                    <div className="txn-meta">{s.hour.toFixed(1)}h into the period</div>
                  </div>
                </button>
              ))}
            </div>

            <div className="threshold-box">
              <div className="threshold-head">
                <span className="threshold-label">Decision threshold</span>
                <span className="threshold-value">{threshold.toFixed(3)}</span>
              </div>
              <input
                type="range" min="0.005" max="0.9" step="0.005"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
              <div className="threshold-note">
                Lower the threshold to catch more fraud at the cost of more false
                alarms. Transaction 4 is the one to watch — it flips from missed
                to caught somewhere below 0.15.
              </div>
            </div>
          </div>
        </div>

        {/* ---- verdict ---- */}
        <div className="card">
          <div className="card-title"><span className="dot amber" />Model verdict</div>

          {selected === null ? (
            <div className="result-empty">
              <div className="big-icon">◉</div>
              <div>Select a transaction to score it.</div>
            </div>
          ) : scoring && !result ? (
            <div className="loading"><div className="spinner amber" />Scoring…</div>
          ) : result ? (
            <div className="verdict">
              <div className="verdict-top">
                <ProbRing probability={result.fraud_probability} color={color} />
                <div className="verdict-body">
                  <span className="badge" style={{ background: color }}>
                    {result.risk_band} risk
                  </span>
                  <div className="verdict-action">{result.recommended_action}</div>
                  <div className="verdict-sub">
                    €{result.amount.toFixed(2)} · {result.hour_of_day}h ·{" "}
                    {result.is_flagged ? "flagged for review" : "allowed through"} at
                    threshold {result.threshold_used}
                  </div>
                </div>
              </div>

              {gt && (
                <div className={`truth ${gt.model_was_right ? "correct" : "wrong"}`}>
                  <span className="truth-icon">{gt.model_was_right ? "✓" : "✕"}</span>
                  <div>
                    <div className="truth-label">
                      {gt.outcome === "true_positive" && "Correctly caught — this was fraud"}
                      {gt.outcome === "true_negative" && "Correctly allowed — this was legitimate"}
                      {gt.outcome === "false_negative" && "Missed — this was fraud"}
                      {gt.outcome === "false_positive" && "False alarm — this was legitimate"}
                    </div>
                    <div className="truth-detail">
                      {gt.outcome === "false_negative" &&
                        "Lower the threshold and the model catches it — at the cost of more false alarms."}
                      {gt.outcome === "false_positive" &&
                        "The price of high recall: some legitimate transactions get verified."}
                      {gt.outcome === "true_positive" &&
                        "Fraud identified before it settled."}
                      {gt.outcome === "true_negative" &&
                        "No friction for the customer."}
                    </div>
                  </div>
                </div>
              )}

              <div className="note-box">
                Scores come from the model running live — not stored predictions.
                See the <Link to="/fraud/model" style={{ color: "var(--amber)" }}>model card</Link>{" "}
                for how it performs across the whole test set.
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
