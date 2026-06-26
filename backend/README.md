# Backend — RiskLens API (Phase 2)

A FastAPI service that wraps the credit risk engine from `ml/credit_risk/`
behind a REST API with request validation and auto-generated docs.

## Run it locally

```bash
# 1. Make sure the model exists (from repo root):
cd ml
pip install -r requirements.txt
python3 credit_risk/generate_data.py
python3 credit_risk/train.py

# 2. Start the API:
cd ../backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** — an interactive page where you can
fill in applicant details and hit "Execute" to see the model respond. No curl
needed.

## Endpoints

| Method | Path | What it does |
|--------|------|--------------|
| GET | `/` | Service info |
| GET | `/api/health` | Liveness check + whether the model is loaded |
| POST | `/api/credit-risk` | Score an applicant: returns probability, score, category, approval, reasons |

## Example request

```bash
curl -X POST http://127.0.0.1:8000/api/credit-risk \
  -H "Content-Type: application/json" \
  -d '{"age":26,"income":35000,"employment_length":1,"credit_score":560,
       "existing_loans":3,"num_delinquencies":4,"credit_history_length":2,
       "loan_amount":300000,"loan_tenure":12,"interest_rate":22.0,
       "debt_to_income":0.7,"loan_purpose":"personal"}'
```

Returns:
```json
{"default_probability":0.5211,"risk_score":52,"risk_category":"High Risk",
 "approval":"Manual Review","reasons":["High debt-to-income ratio", ...]}
```

## Structure

```
backend/app/
├── main.py                  # app entrypoint, CORS, startup model loading
├── api/routes.py            # the /credit-risk and /health endpoints
├── schemas/credit.py        # Pydantic request/response validation
└── services/credit_service.py  # loads CreditRiskEngine, bridges API <-> ML
```

## What's next (Phase 3)
A React frontend that posts to `/api/credit-risk` and displays the result.
