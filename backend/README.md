# Backend — FastAPI service (Phase 2)

This folder will hold the FastAPI app that wraps the credit risk engine from
`ml/credit_risk/scoring.py` behind a REST API. Build it next.

Planned layout:
- `app/main.py`         — FastAPI app entrypoint
- `app/api/`            — route handlers (/credit-risk, /health)
- `app/schemas/`        — Pydantic models validating applicant input
- `app/services/`       — loads CreditRiskEngine, calls .score()
- `app/models/`         — OOP domain classes (Customer, Loan, Account)
- `app/core/`           — config/settings

