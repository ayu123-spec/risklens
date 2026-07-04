"""End-to-end integration test: mount the routes like main.py does, hit every endpoint."""
import os
os.environ["DATABASE_URL"] = "sqlite:///integration_test.db"
for f in ["integration_test.db"]:
    if os.path.exists(f): os.remove(f)

from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database.db import init_db, get_session
import database.repository as repo
import db_routes
from db_routes import persist_assessment

# Simulate main.py wiring
app = FastAPI()
init_db()
# seed reference data on startup (as main.py would)
from database.db import SessionLocal
_db = SessionLocal(); repo.seed_reference_data(_db); _db.close()

app.include_router(db_routes.router, prefix="/api")

# Simulate the existing /api/credit-risk endpoint that now ALSO persists
@app.post("/api/credit-risk")
def credit_risk(inputs: dict, db: Session = Depends(get_session)):
    # (in reality the scoring engine computes this; we simulate a result)
    result = {
        "risk_score": inputs.get("_score", 8),
        "default_probability": inputs.get("_prob", 0.08),
        "risk_category": inputs.get("_cat", "Low Risk"),
        "risk_grade": inputs.get("_grade", "A"),
        "approval": inputs.get("_appr", "Approve"),
    }
    saved = persist_assessment(db, inputs, result)
    result["assessment_id"] = saved.id
    return result

client = TestClient(app)
passed, failed = 0, 0
def check(name, cond, extra=""):
    global passed, failed
    if cond: passed += 1; print(f"  [PASS] {name}")
    else: failed += 1; print(f"  [FAIL] {name} — {extra}")

print("=== 1. POST /api/credit-risk persists to DB ===")
r = client.post("/api/credit-risk", json={"age": 30, "income": 35000, "loan_purpose": "home"})
check("credit-risk returns 200", r.status_code == 200, r.text)
check("response has assessment_id", "assessment_id" in r.json(), r.text)
first_id = r.json().get("assessment_id")

# add a few more with varied risk
for s, p, c, g, a in [(73,0.73,"Extreme Risk","CC","Reject"),
                       (25,0.25,"High Risk","BB","Manual Review"),
                       (3,0.03,"Very Low Risk","AAA","Auto Approve")]:
    client.post("/api/credit-risk", json={"age":30,"income":40000,"loan_purpose":"auto",
                "_score":s,"_prob":p,"_cat":c,"_grade":g,"_appr":a})

print("\n=== 2. GET /api/assessments (history) ===")
r = client.get("/api/assessments")
check("list returns 200", r.status_code == 200)
check("has 4 assessments", len(r.json()["assessments"]) == 4, str(len(r.json()["assessments"])))

print("\n=== 3. GET /api/assessments/{id} (detail) ===")
r = client.get(f"/api/assessments/{first_id}")
check("detail returns 200", r.status_code == 200)
check("detail has inputs", "inputs" in r.json() and r.json()["inputs"]["income"]==35000, r.text)
r404 = client.get("/api/assessments/99999")
check("missing id returns 404", r404.status_code == 404)

print("\n=== 4. Workflow: review then decide ===")
r = client.post(f"/api/assessments/{first_id}/review", json={"reviewer_name":"Priya"})
check("review returns 200", r.status_code == 200)
check("status is reviewed", r.json()["status"] == "reviewed", r.text)
r = client.post(f"/api/assessments/{first_id}/decide",
                json={"reviewer_name":"Priya","decision":"approved","note":"ok"})
check("decide returns 200", r.status_code == 200)
check("status decided, decision approved",
      r.json()["status"]=="decided" and r.json()["decision"]=="approved", r.text)
rbad = client.post(f"/api/assessments/{first_id}/decide",
                   json={"reviewer_name":"Priya","decision":"nonsense"})
check("invalid decision returns 400", rbad.status_code == 400)

print("\n=== 5. Analytics endpoints ===")
for path, key in [("/api/analytics/approval-rate","approval_rate"),
                  ("/api/analytics/risk-distribution","distribution"),
                  ("/api/analytics/grade-distribution","distribution"),
                  ("/api/analytics/portfolio-exposure","avg_default_probability"),
                  ("/api/analytics/over-time","series")]:
    r = client.get(path)
    check(f"GET {path}", r.status_code == 200 and key in r.json(), r.text)

print("\n=== 6. Verify data actually persisted (not just in-memory) ===")
r = client.get("/api/analytics/approval-rate")
check("approval-rate computed from stored data", r.json()["total"]==4, r.text)

import os as _os
_os.remove("integration_test.db")
print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed")
print("=== INTEGRATION WORKS ===" if failed==0 else "=== ISSUES FOUND ===")
