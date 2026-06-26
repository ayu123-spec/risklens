# Banking Risk Intelligence Platform

A credit-risk and (eventually) fraud-detection platform, built **one runnable
vertical slice at a time**. The goal is a deployed, working system you fully
understand — not a skeleton.

> **Status:** Phase 1 complete and runnable (credit risk ML + scoring engine).
> Phases 2–4 (API, frontend, deploy) are the active next steps. Later phases are
> roadmap, not stub files — folders fill with real code as each phase is built.

## Repository structure

```
banking-risk-platform/
├── ml/                        # Machine learning layer
│   └── credit_risk/
│       ├── generate_data.py   #  ✅ synthetic loan data generator
│       ├── train.py           #  ✅ trains + evaluates + calibrates + saves model
│       └── scoring.py         #  ✅ business logic: score → category → approval
│
├── backend/                   # FastAPI service (Phase 2 — in progress)
│   └── app/
│       ├── api/               #  route handlers
│       ├── core/              #  config, settings
│       ├── models/            #  OOP domain classes (Customer, Loan, ...)
│       ├── schemas/           #  Pydantic request/response models
│       └── services/          #  wires the ML engine into the API
│
├── frontend/                  # React app (Phase 3 — planned)
│   └── src/
│       ├── components/        #  KPI cards, risk gauge, form
│       └── pages/             #  Credit Risk page, dashboard
│
├── deploy/                    # Dockerfiles, Render/Vercel config (Phase 4)
├── docs/                      # Architecture, API docs, design notes
└── README.md                  # you are here
```

## Run what exists today

```bash
cd ml
pip install -r requirements.txt
python3 credit_risk/generate_data.py   # writes loans.csv
python3 credit_risk/train.py           # trains, saves model.joblib
python3 credit_risk/scoring.py         # demo: scores a safe vs risky applicant
```

See `ml/credit_risk/` and the per-phase notes in `docs/ROADMAP.md`.

## Roadmap

| Phase | Layer | Status |
|-------|-------|--------|
| 1 | Credit risk model + business logic | ✅ Done |
| 2 | FastAPI backend (`/credit-risk` endpoint, validation, OOP) | ✅ Done |
| 3 | React frontend (form + score display) | 🔨 Next |
| 4 | Deploy (Render + Vercel, live URL) | ⬜ Planned |
| 5 | Fraud detection engine | ⬜ Planned |
| 6 | Database (Postgres → star schema → Snowflake) | ⬜ Planned |
| 7 | BI dashboards (Power BI / Tableau) | ⬜ Planned |
| 8 | Auth, RBAC, CI/CD, monitoring | ⬜ Planned |

Each phase is self-contained and runnable before the next begins.
```
