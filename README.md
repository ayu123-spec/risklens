RiskLens — Credit Risk Intelligence Platform

An end-to-end, AI-powered credit-risk platform for lending decisions. Enter a loan
applicant's details and get an explainable risk assessment: a default probability,
a letter grade (AAA–C), a risk category, an approval recommendation, risk-based
pricing, a maximum eligible loan amount, a confidence score, and the specific
factors behind the decision.

Live demo:


Frontend: https://risklens-vert.vercel.app
API: https://risklens-ri15.onrender.com



Note: the free-tier backend sleeps after ~15 min of inactivity; the first
request after idle takes ~30–60s to wake.




Tech Stack

LayerTechnologyMLPython, scikit-learn, XGBoost, pandas, NumPyBackendFastAPI, SQLAlchemy, Pydantic, UvicornDatabasePostgreSQL (prod), SQLite (local dev)FrontendReact, Vite, React Router, Chart.jsDeploymentDocker, Render (backend), Vercel (frontend)


Features

Live in production


Explainable credit scoring — default probability, 0–100 risk score, and the
contributing factors behind every decision (no black box).
Industry-style risk tiering — 6 risk categories (Very Low → Extreme) and
AAA–C letter grades.
Business decision layer — approval recommendation, risk-based interest rate,
maximum eligible loan amount, and an honest confidence score (distance from the
decision boundary, not a fabricated number).
REST API — FastAPI backend with input validation and environment-aware CORS.
Premium React dashboard — risk gauge, factor-contribution chart, probability
breakdown, client-side validation, responsive design.
Dockerized deployment — reproducible container build, deployed live.


Built & verified (not yet wired into the live deployment)


Real-data credit model — trained on the Kaggle "Give Me Some Credit" dataset
(150K real borrowers). ROC-AUC 0.868. Includes tailored data cleaning
(outlier treatment, sentinel-code handling, 20% missing-income strategy) and
feature engineering (an aggregate delinquency signal was the strongest predictor).
Fraud detection model — Kaggle Credit Card Fraud dataset (285K transactions,
0.17% fraud, 578:1 imbalance). PR-AUC 0.874, ~89% recall. Uses
scale_pos_weight and threshold tuning optimized for catching fraud.
Advanced database layer — normalized 7-table PostgreSQL schema (users,
applicants, loan products, model versions, assessments, audit log) with:

ML model-versioning for governance (which model scored which decision)
a review/decision workflow (pending → reviewed → decided)
audit logging, soft-deletes, DB constraints, connection pooling
analytics queries (approval rate, risk distribution, portfolio exposure)



Multi-page frontend — Assess, Analytics (dashboard with charts), and History
pages with shared navigation, built in React Router.



Architecture

React (Vite) frontend  ──HTTP──▶  FastAPI backend  ──▶  ML model (XGBoost)
      │                                  │
   Vercel                            Render (Docker)
                                         │
                                   PostgreSQL  ◀── assessments, audit, analytics


Key Engineering Highlights


Monotonicity audit of the scoring model — caught and fixed a bug where lower
income wasn't increasing risk; corrected with a direct log-income term and
verified all 11 features move risk in the correct direction.
Honest handling of imbalanced data — recognized PR-AUC over accuracy for
rare-event problems; ~16% credit-default recall and ~89% fraud recall reflect
real, defensible model behavior rather than misleading vanity accuracy.
Resilient persistence — database saves are decoupled from scoring, so a DB
failure degrades gracefully (score still returns) instead of breaking the app.
Production-grade schema — enums, check constraints, indexes, migrations
(Alembic), and model-versioning for ML governance.



Running Locally

Backend

bashcd backend
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

Frontend

bashcd frontend
npm install
npm run dev

The backend uses SQLite locally by default (zero setup). Set DATABASE_URL to a
Postgres connection string for production.

Train the models

bash# Real-data credit model
python ml/credit_risk_real/train_real.py path/to/cs-training.csv
# Fraud model
python ml/fraud_detection/train_fraud.py path/to/creditcard.csv


Roadmap / To-Do

Done


 Phase 1 — Credit risk ML model (trained, audited, feature-verified)
 Phase 2 — FastAPI backend (validated endpoints, tiering, data ingestion)
 Phase 3 — React frontend (premium dashboard, charts, animations)
 Phase 4 — Deployment (Docker, Render + Vercel, live)
 Phase 5 — Fraud detection model (built, verified)
 Real-data credit model on Kaggle data (built, verified)
 Phase 6 — Advanced database layer + backend integration (built, verified)
 Multi-page frontend: Assess / Analytics / History (built, verified)


In progress — assembling built components into the live deployment


 Wire the backend integration into the live main.py
 Provision hosted PostgreSQL (Render free tier)
 Deploy the multi-page frontend + integrated backend together
 Swap the live model to the real-data (150K-borrower) model


Not started


 Phase 7 — BI dashboards (connect a BI tool to the live database)
 Phase 8 — Authentication, role-based access control, CI/CD, monitoring


Possible enhancements


 Per-prediction SHAP values for exact factor attribution
 Batch scoring (upload a CSV of applicants)
 Model performance monitoring / drift detection
 Automated tests in CI



Datasets


Give Me Some Credit — credit default
Credit Card Fraud Detection — fraud


Datasets are not committed to the repo (see .gitignore); download them from Kaggle
and run the training scripts.


License

For portfolio / educational purposes.
