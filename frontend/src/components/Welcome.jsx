// Welcome.jsx — the landing page shown before the dashboard.
// Introduces RiskLens, explains what it does and who it's for, and collects
// the user's name (held in the app for a personalized greeting — this is a
// friendly touch, NOT authentication; the name isn't stored or sent anywhere).

import { useState } from "react";

const FEATURES = [
  {
    icon: "◷",
    title: "Instant risk scoring",
    text: "Enter an applicant's details and get a calibrated default probability in real time.",
  },
  {
    icon: "▦",
    title: "Industry-style grading",
    text: "Six risk tiers and AAA–C grades, with risk-based pricing and eligible loan limits.",
  },
  {
    icon: "◈",
    title: "Explainable decisions",
    text: "Every score comes with the factors behind it — no black box.",
  },
];

export default function Welcome({ onEnter }) {
  const [name, setName] = useState("");

  function submit() {
    const clean = name.trim();
    onEnter(clean || "Analyst"); // fall back to a neutral default if left blank
  }

  return (
    <div className="welcome">
      <div className="welcome-inner">
        <div className="welcome-brand">
          <div className="brand-mark welcome-mark">R</div>
          <div className="welcome-title">RiskLens</div>
        </div>

        <div className="welcome-eyebrow">
          <span className="pulse" />
          Credit risk intelligence platform
        </div>
        <h1 className="welcome-h1">Credit Risk Intelligence<br />for modern lending</h1>
        <p className="welcome-lead">
          RiskLens helps banks, NBFCs, and fintech lenders assess loan applicants —
          predicting default probability, assigning a risk grade, and recommending a
          credit decision, all with the reasoning made transparent.
        </p>

        <div className="welcome-stats">
          <div className="wstat">
            <div className="wstat-num">6</div>
            <div className="wstat-label">Risk tiers</div>
          </div>
          <div className="wstat">
            <div className="wstat-num">AAA–C</div>
            <div className="wstat-label">Grade scale</div>
          </div>
          <div className="wstat">
            <div className="wstat-num">&lt;1s</div>
            <div className="wstat-label">Scoring time</div>
          </div>
        </div>

        <div className="welcome-features">
          {FEATURES.map((f) => (
            <div className="welcome-feature" key={f.title}>
              <div className="wf-icon">{f.icon}</div>
              <div className="wf-title">{f.title}</div>
              <div className="wf-text">{f.text}</div>
            </div>
          ))}
        </div>

        <div className="welcome-entry">
          <label className="welcome-label">Let's get started — what should we call you?</label>
          <div className="welcome-row">
            <input
              className="welcome-input"
              type="text"
              placeholder="Your name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && submit()}
              autoFocus
            />
            <button className="welcome-btn" onClick={submit}>Enter dashboard</button>
          </div>
          <div className="welcome-note">For demonstration — your name stays in this session only.</div>
        </div>
      </div>
    </div>
  );
}
