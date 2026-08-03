import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet } from "../api.js";
import { RISK_RAMP, gradeColor } from "../chartTheme.js";

export default function HistoryPage() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet("/api/assessments?limit=50")
      .then((d) => setRows(d.assessments))
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="page">
        <div className="empty-state">
          <div className="big-icon">⚠</div>
          <div>Can't load history. Make sure the backend is running.</div>
        </div>
      </div>
    );
  }

  if (!rows) {
    return (
      <div className="page">
        <div className="loading"><div className="spinner" />Loading history…</div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="page-head">
        <div className="eyebrow"><span className="pulse" />Assessment records</div>
        <h1 className="page-title">History</h1>
        <p className="page-desc">
          Every assessment, most recent first — with its grade, decision, and where
          it sits in the review workflow.
        </p>
      </div>

      {rows.length === 0 ? (
        <div className="empty-state">
          <div className="big-icon">◔</div>
          <div>No assessments recorded yet.</div>
          <div style={{ marginTop: "0.5rem" }}>
            <Link to="/">Run your first assessment →</Link>
          </div>
        </div>
      ) : (
        <div className="card" style={{ padding: "0.5rem" }}>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Score</th>
                  <th>Grade</th>
                  <th>Category</th>
                  <th>Recommendation</th>
                  <th>Status</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((a) => (
                  <tr key={a.id}>
                    <td style={{ color: "var(--faint)" }}>#{a.id}</td>
                    <td style={{ fontFamily: "Space Grotesk", fontWeight: 600 }}>{a.risk_score}</td>
                    <td><span className="grade-chip" style={{ color: gradeColor(a.risk_grade) }}>{a.risk_grade}</span></td>
                    <td>
                      <span style={{ color: RISK_RAMP[a.risk_category] || "var(--ink)" }}>
                        {a.risk_category.replace(" Risk", "")}
                      </span>
                    </td>
                    <td style={{ color: "var(--muted)" }}>{a.approval}</td>
                    <td><span className={`pill ${a.status}`}>{a.status}</span></td>
                    <td style={{ color: "var(--faint)", fontSize: "0.82rem" }}>
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
