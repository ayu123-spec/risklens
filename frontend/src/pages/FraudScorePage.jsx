import { useEffect, useState } from "react";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip } from "chart.js";
import { Link } from "react-router-dom";
import { apiGet, apiPost } from "../api.js";
import { fraudBandColor } from "../chartTheme.js";

ChartJS.register(ArcElement, Tooltip);

function StepLabel({ n, title, done }) {
  return (
    <div className="step-label">
      <span className={`step-num ${done ? "done" : ""}`}>{done ? "✓" : n}</span>
      <span className="step-title">{title}</span>
    </div>
  );
}

/** Expandable detail, so the page stays readable but the depth is available. */
function Detail({ label, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="detail">
      <button className="detail-toggle" onClick={() => setOpen(!open)}>
        {open ? "▾" : "▸"} {label}
      </button>
      {open && <div className="detail-body">{children}</div>}
    </div>
  );
}

function ProbRing({ probability, color }) {
  const pct = probability * 100;
  const shown = Math.max(pct, 0.6);
  return (
    <div className="prob-ring">
      <Doughnut
        data={{ datasets: [{ data: [shown, 100 - shown],
          backgroundColor: [color, "rgba(128,128,128,0.14)"], borderWidth: 0, cutout: "76%" }] }}
        options={{ responsive: true, maintainAspectRatio: false,
          plugins: { tooltip: { enabled: false }, legend: { display: false } } }}
      />
      <div className="prob-ring-inner">
        <div className="prob-val" style={{ color }}>
          {pct >= 1 ? pct.toFixed(1) : pct.toFixed(2)}%
        </div>
        <div className="prob-lbl">chance of fraud</div>
      </div>
    </div>
  );
}

export default function FraudScorePage() {
  const [samples, setSamples] = useState(null);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [threshold, setThreshold] = useState(0.10);
  const [touchedSlider, setTouchedSlider] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet("/api/fraud/samples").then((d) => setSamples(d.samples)).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (selected === null) return;
    apiPost(`/api/fraud/score/${selected}?threshold=${threshold}`)
      .then(setResult).catch((e) => setError(e.message));
  }, [selected, threshold]);

  if (error) {
    return (
      <div className="page"><div className="empty-state">
        <div className="big-icon">⚠</div><div>Can't reach the fraud service.</div>
        <div style={{ fontSize: ".8rem", marginTop: ".5rem" }}>{error}</div>
      </div></div>
    );
  }
  if (!samples) {
    return <div className="page"><div className="loading"><div className="spinner amber" />Loading…</div></div>;
  }

  const color = result ? fraudBandColor(result.risk_band) : "#9a9aa8";
  const gt = result?.ground_truth;
  const pct = result ? result.fraud_probability * 100 : 0;
  const thrPct = (threshold * 100).toFixed(1);

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow"><span className="pulse amber" />Interactive demo</div>
        <h1 className="page-title amber">Fraud Detection</h1>
        <p className="page-desc">
          A bank processes millions of card payments. Almost all are genuine — in
          this dataset only <strong>0.17%</strong> are fraud. This model reads each
          payment and estimates how likely it is to be fraudulent.
        </p>
      </div>

      <div className="explainer">
        <div className="explainer-row">
          <div className="explainer-step">
            <div className="explainer-n">1</div>
            <div>
              <strong>The model scores the payment</strong>
              <p>It returns a probability — "there's a 14% chance this is fraud".</p>
            </div>
          </div>
          <div className="explainer-arrow">→</div>
          <div className="explainer-step">
            <div className="explainer-n">2</div>
            <div>
              <strong>You choose a cut-off</strong>
              <p>Score above it, the payment gets investigated. Below it, it goes through.</p>
            </div>
          </div>
          <div className="explainer-arrow">→</div>
          <div className="explainer-step">
            <div className="explainer-n">3</div>
            <div>
              <strong>The cut-off is a trade-off</strong>
              <p>Low: catch more fraud, bother more honest customers. High: the reverse.</p>
            </div>
          </div>
        </div>
      </div>

      <div className="txn-grid">
        <div>
          <div className="card">
            <StepLabel n="1" title="Pick a payment to check" done={selected !== null} />
            <p className="step-desc">
              Nine real payments from the dataset. The model has never seen them,
              and neither of us knows which are fraud until it decides.
            </p>

            <div className="txn-list">
              {samples.map((s) => (
                <button key={s.id} className={`txn ${selected === s.id ? "selected" : ""}`}
                        onClick={() => setSelected(s.id)}>
                  <div className="txn-num">{s.id}</div>
                  <div className="txn-body">
                    <div className="txn-amount">€{s.amount.toFixed(2)}</div>
                    <div className="txn-meta">Payment #{s.id} · hour {Math.floor(s.hour)} of 48</div>
                  </div>
                  <span className="txn-cta">{selected === s.id ? "checking" : "check →"}</span>
                </button>
              ))}
            </div>

            <Detail label="Why are the amounts so small, and where are the details?">
              Two things are unusual here, and both are deliberate.
              <br /><br />
              <strong>The amounts are small</strong> because card fraudsters often
              test a stolen card with a tiny payment first, to check it works before
              attempting anything larger. Small amounts are genuinely suspicious.
              <br /><br />
              <strong>There is no merchant or location</strong> because the bank that
              published this data anonymised it for privacy. The original fields were
              mathematically transformed into 28 numbers (V1–V28) that carry the
              signal but reveal nothing about the customer. The model uses those,
              plus the amount and timing.
            </Detail>
          </div>
        </div>

        <div>
          <div className="card">
            <StepLabel n="2" title="See what the model decided" done={result !== null} />

            {selected === null ? (
              <div className="result-empty">
                <div className="big-icon">◉</div>
                <div>Pick a payment on the left to score it.</div>
              </div>
            ) : !result ? (
              <div className="loading"><div className="spinner amber" />Scoring…</div>
            ) : (
              <div className="verdict">
                <div className="verdict-top">
                  <ProbRing probability={result.fraud_probability} color={color} />
                  <div className="verdict-body">
                    <div className="verdict-reading">
                      The model thinks there is a{" "}
                      <strong style={{ color }}>{pct >= 1 ? pct.toFixed(1) : pct.toFixed(2)}%</strong>{" "}
                      chance this €{result.amount.toFixed(2)} payment is fraud.
                    </div>
                    <div className="verdict-compare">
                      Your cut-off is <strong>{thrPct}%</strong> —{" "}
                      {result.is_flagged
                        ? <span style={{ color: "var(--amber)" }}>the score is above it, so this payment is flagged.</span>
                        : <span style={{ color: "var(--ok)" }}>the score is below it, so this payment goes through.</span>}
                    </div>
                    <div className="verdict-action-row">
                      <span className="badge" style={{ background: color }}>{result.risk_band}</span>
                      <span className="verdict-action-txt">{result.recommended_action}</span>
                    </div>
                  </div>
                </div>

                {gt && (
                  <div className={`truth ${gt.model_was_right ? "correct" : "wrong"}`}>
                    <span className="truth-icon">{gt.model_was_right ? "✓" : "✕"}</span>
                    <div>
                      <div className="truth-label">
                        {gt.outcome === "true_positive" && "Right call — this really was fraud, and it was caught"}
                        {gt.outcome === "true_negative" && "Right call — this really was genuine, and it went through"}
                        {gt.outcome === "false_negative" && "Wrong — this really was fraud, and it slipped through"}
                        {gt.outcome === "false_positive" && "Wrong — this was a genuine payment, flagged by mistake"}
                      </div>
                      <div className="truth-detail">
                        {gt.outcome === "false_negative" && "The score wasn't high enough to clear your cut-off. Lower the cut-off in step 3 and the model catches it."}
                        {gt.outcome === "false_positive" && "A real customer would get an unnecessary 'was this you?' message. This is the cost of a low cut-off."}
                        {gt.outcome === "true_positive" && "Caught before the money moved. This is the outcome the bank wants."}
                        {gt.outcome === "true_negative" && "No unnecessary friction for the customer."}
                      </div>
                    </div>
                  </div>
                )}

                <Detail label="What does the percentage actually mean?">
                  It is the model's confidence, not a certainty. A score of 14% means
                  this payment's pattern resembles payments that turned out to be
                  fraud roughly 14% of the time in the training data.
                  <br /><br />
                  It is <strong>not</strong> a yes/no answer. Turning it into a decision
                  requires the cut-off in step 3 — and where you put that line is a
                  business choice, not a modelling one.
                </Detail>
              </div>
            )}
          </div>

          {result && (
            <div className="card" style={{ marginTop: "1.25rem" }}>
              <StepLabel n="3" title="Move the cut-off and watch it change" done={touchedSlider} />
              <p className="step-desc">
                This is where the real decision lives. Drag the slider and the same
                payment is re-scored against the new cut-off.
              </p>

              <div className="threshold-box">
                <div className="threshold-head">
                  <span className="threshold-label">Flag anything above</span>
                  <span className="threshold-value">{thrPct}%</span>
                </div>
                <input type="range" min="0.005" max="0.9" step="0.005" value={threshold}
                       onChange={(e) => { setThreshold(Number(e.target.value)); setTouchedSlider(true); }} />
                <div className="threshold-scale">
                  <span>0.5% — catch nearly everything</span>
                  <span>90% — only the obvious</span>
                </div>
              </div>

              {selected === 4 ? (
                <div className="try-this">
                  <strong>Try this with payment 4</strong>
                  <p>
                    It scores 14.5%, and it is genuinely fraud. Set the cut-off above
                    15% and the model lets it through — a real fraud missed. Bring it
                    back below and the model catches it. Same payment, same model;
                    only the line moved.
                  </p>
                </div>
              ) : (
                <div className="try-this subtle">
                  <strong>Then try payment 4</strong>
                  <p>
                    It is the interesting one — real fraud that flips between caught
                    and missed depending on where you put the cut-off.
                  </p>
                </div>
              )}

              <Detail label="Why not set the cut-off very low and catch everything?">
                Because every flagged payment costs something — a blocked card, or a
                verification message to a customer who may have done nothing wrong.
                <br /><br />
                At a 1% cut-off this model catches 89% of fraud, but raises 124 false
                alarms across the test set. At 50% it raises only 12 false alarms, but
                misses more fraud.
                <br /><br />
                Banks usually lean toward catching fraud, because a missed fraud costs
                the whole transaction while a false alarm costs a text message. That is
                why this platform runs at 10%. The{" "}
                <Link to="/fraud/model" style={{ color: "var(--amber)" }}>model card</Link>{" "}
                shows the full trade-off.
              </Detail>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
