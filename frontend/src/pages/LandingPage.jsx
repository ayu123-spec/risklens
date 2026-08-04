import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "../api.js";

/**
 * The chooser. Two capabilities, each with live figures pulled from its own
 * part of the API — so the cards reflect the real system rather than static copy.
 * Stats fail quietly: if the backend is asleep the cards still render.
 */
export default function LandingPage() {
  const [creditStats, setCreditStats] = useState(null);
  const [fraudStats, setFraudStats] = useState(null);

  useEffect(() => {
    apiGet("/api/analytics/approval-rate").then(setCreditStats).catch(() => {});
    apiGet("/api/fraud/model-info").then(setFraudStats).catch(() => {});
  }, []);

  return (
    <div className="landing">
      <div className="landing-inner">
        <div className="landing-mark">R</div>
        <h1 className="landing-title">Banking risk intelligence</h1>
        <p className="landing-sub">
          Two machine-learning capabilities on one platform — explainable credit
          decisioning and real-time fraud detection. Choose where to start.
        </p>

        <div className="capability-grid">
          {/* ---------- Credit Risk ---------- */}
          <Link to="/credit" className="capability">
            <div className="cap-icon">◈</div>
            <div className="cap-name">Credit Risk</div>
            <p className="cap-desc">
              Score a loan applicant's probability of default. Returns a risk grade,
              an approval recommendation, risk-based pricing and the factors driving
              the decision — every assessment stored and analysed.
            </p>
            <div className="cap-stats">
              <div>
                <div className="cap-stat-val">
                  {creditStats ? creditStats.total : "—"}
                </div>
                <div className="cap-stat-lbl">Assessments</div>
              </div>
              <div>
                <div className="cap-stat-val">
                  {creditStats ? `${Math.round(creditStats.approval_rate * 100)}%` : "—"}
                </div>
                <div className="cap-stat-lbl">Approval rate</div>
              </div>
              <div>
                <div className="cap-stat-val">AAA–C</div>
                <div className="cap-stat-lbl">Grade scale</div>
              </div>
            </div>
            <div className="cap-cta">Assess an applicant →</div>
          </Link>

          {/* ---------- Fraud Detection ---------- */}
          <Link to="/fraud" className="capability amber">
            <div className="cap-icon amber">◉</div>
            <div className="cap-name">Fraud Detection</div>
            <p className="cap-desc">
              Flag fraudulent card transactions in a stream where only 0.17% are
              fraud. Tuned for recall — a missed fraud costs far more than a
              verification call. Score real transactions and move the threshold.
            </p>
            <div className="cap-stats">
              <div>
                <div className="cap-stat-val">
                  {fraudStats?.available ? fraudStats.pr_auc : "—"}
                </div>
                <div className="cap-stat-lbl">PR-AUC</div>
              </div>
              <div>
                <div className="cap-stat-val">
                  {fraudStats?.available ? `${fraudStats.imbalance_ratio}:1` : "—"}
                </div>
                <div className="cap-stat-lbl">Imbalance</div>
              </div>
              <div>
                <div className="cap-stat-val">
                  {fraudStats?.available
                    ? `${(fraudStats.n_transactions / 1000).toFixed(0)}K`
                    : "—"}
                </div>
                <div className="cap-stat-lbl">Transactions</div>
              </div>
            </div>
            <div className="cap-cta amber">Score transactions →</div>
          </Link>
        </div>

        <div className="landing-foot">
          Models trained on public lending and transaction datasets · For
          demonstration purposes
        </div>
      </div>
    </div>
  );
}
