# Roadmap & Build Notes

This platform is built in self-contained phases. Each one runs before the next
begins, so you always have something working and explainable.

## Phase 1 — Credit Risk Engine ✅ DONE
**Where:** `ml/credit_risk/`
- Synthetic data generator with realistic risk relationships.
- Trains Logistic Regression vs XGBoost, compares them.
- Evaluates with ROC-AUC and PR-AUC (not accuracy — the data is imbalanced).
- Calibrates probabilities so the scores are trustworthy.
- SHAP for global feature importance.
- Business-logic `CreditRiskEngine` (OOP): probability → risk category →
  approval recommendation → plain-English reasons.

**What you learned:** the ML workflow, why accuracy misleads on imbalanced data,
calibration, and how raw model output becomes a product decision.

## Phase 2 — FastAPI Backend 🔨 NEXT
**Where:** `backend/`
- A `/credit-risk` POST endpoint taking applicant features, returning the score.
- Pydantic schemas to validate input (reject bad/missing fields cleanly).
- A service layer that loads `CreditRiskEngine` once and calls it per request.
- OOP domain models (Customer, Loan) — fleshes out the classes from the spec.
- `/health` endpoint and auto-generated Swagger docs at `/docs`.

**What you'll learn:** REST APIs, request validation, dependency injection,
how a model gets served in production.

## Phase 3 — React Frontend ⬜
**Where:** `frontend/`
- Vite + React app. A form for applicant details.
- Calls the API, renders score, a risk gauge, category badge, and reason list.

**What you'll learn:** frontend basics, calling APIs, state, CORS.

## Phase 4 — Deployment ⬜ ("deploy & use it" milestone)
**Where:** `deploy/`
- Dockerise the backend, deploy to Render (free tier).
- Deploy the frontend to Vercel (free tier).
- Wire them together. **Result: a live public URL.**

## Phase 5 — Fraud Detection ⬜
- Second model on transaction data: Isolation Forest (unsupervised anomaly) +
  XGBoost (supervised). Same generate → train → score → explain pattern.

## Phase 6 — Database ⬜
- Replace CSV with Postgres. Then model a star schema (dim/fact tables).
- This is the on-ramp to the Snowflake warehouse in the original spec.

## Phase 7 — BI Dashboards ⬜
- Connect Power BI / Tableau to the database for executive dashboards.

## Phase 8 — Production Hardening ⬜
- JWT auth, role-based access control, GitHub Actions CI/CD, logging, health
  monitoring.

---

### Why not build it all at once?
A repo full of empty files reads as scaffolding, not work, and you can't explain
code you didn't write. Building each layer on top of the last means every part
is real, runnable, and defensible in an interview. The structure grows with the
code.
