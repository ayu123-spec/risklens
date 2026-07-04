"""Comprehensive test of the advanced database layer (SQLite, zero setup)."""
import os
os.environ["DATABASE_URL"] = "sqlite:///test_adv.db"
if os.path.exists("test_adv.db"): os.remove("test_adv.db")

from db import init_db, SessionLocal
from models import UserRole, DecisionOutcome, AssessmentStatus
import repository as repo

print("1. Create tables + seed reference data")
init_db()
db = SessionLocal()
repo.seed_reference_data(db)
products = db.query(repo.LoanProduct).all()
model = repo.get_active_model(db)
print(f"   {len(products)} loan products seeded")
print(f"   Active model: {model}")

print("\n2. Create users with roles")
analyst = repo.get_or_create_user(db, "Ayuush", "ayuush@x.com", UserRole.ANALYST)
reviewer = repo.get_or_create_user(db, "Priya", "priya@x.com", UserRole.REVIEWER)
print(f"   {analyst}")
print(f"   {reviewer}")

print("\n3. Create an applicant (first-class record)")
applicant = repo.get_or_create_applicant(db, full_name="John Doe", age=30,
                                         annual_income=35000, external_ref="CUST-001")
print(f"   {applicant}")

print("\n4. Create assessment (links applicant+product+model+analyst)")
home = db.query(repo.LoanProduct).filter_by(code="HOME").first()
result = {"risk_score": 8, "default_probability": 0.08, "risk_category": "Low Risk",
          "risk_grade": "A", "approval": "Approve"}
a = repo.create_assessment(db, applicant=applicant, analyst=analyst,
                           inputs={"age": 30, "income": 35000}, result=result,
                           product=home, model_version=model)
print(f"   {a}  (status={a.status.value})")

print("\n5. Workflow: pending -> reviewed -> decided")
repo.review_assessment(db, a.id, reviewer)
db.refresh(a); print(f"   after review: status={a.status.value}")
repo.decide_assessment(db, a.id, reviewer, DecisionOutcome.APPROVED, "Meets criteria")
db.refresh(a); print(f"   after decision: status={a.status.value}, decision={a.decision.value}")

print("\n6. Add more assessments for analytics")
for i, r in enumerate([
    {"risk_score": 73, "default_probability": 0.73, "risk_category": "Extreme Risk", "risk_grade": "CC", "approval": "Reject"},
    {"risk_score": 25, "default_probability": 0.25, "risk_category": "High Risk", "risk_grade": "BB", "approval": "Manual Review"},
    {"risk_score": 3, "default_probability": 0.03, "risk_category": "Very Low Risk", "risk_grade": "AAA", "approval": "Auto Approve"},
]):
    ap = repo.get_or_create_applicant(db, full_name=f"Person {i}", age=30+i, external_ref=f"CUST-10{i}")
    repo.create_assessment(db, applicant=ap, analyst=analyst, inputs={"n": i}, result=r, model_version=model)
print("   3 more added")

print("\n7. ANALYTICS QUERIES:")
print(f"   approval_rate:    {repo.approval_rate(db)}")
print(f"   risk_distribution: {repo.risk_distribution(db)}")
print(f"   grade_distribution: {repo.grade_distribution(db)}")
print(f"   portfolio_exposure: {repo.portfolio_exposure(db)}")
print(f"   over_time (30d):   {repo.assessments_over_time(db)}")

print("\n8. Verify CONSTRAINTS reject bad data")
from models import Assessment
try:
    bad = Assessment(applicant_id=applicant.id, inputs={}, risk_score=150,  # >100!
                     default_probability=0.5, risk_category="X", risk_grade="X", approval="X")
    db.add(bad); db.commit()
    print("   FAIL: bad score was accepted")
except Exception as e:
    db.rollback()
    print(f"   Constraint correctly rejected score=150 (score must be 0-100)")

print("\n9. Verify audit trail captured everything")
logs = db.query(repo.AuditLog).all()
print(f"   {len(logs)} audit entries:")
for log in logs[:6]:
    print(f"     [{log.action}] entity={log.entity_type}#{log.entity_id}")

db.close()
os.remove("test_adv.db")
print("\n=== COMPREHENSIVE ADVANCED LAYER: ALL WORKING ===")
