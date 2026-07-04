"""
db_routes.py — the API endpoints that use the advanced database layer.

This is the technical integration: it wires the 7-table schema (applicants,
products, model versions, assessments, workflow, audit, analytics) into real
HTTP endpoints, WITHOUT changing the existing /api/credit-risk contract the
frontend already uses.

Mounted under /api in main.py. Uses FastAPI dependency injection for DB sessions.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.db import get_session
from database.models import DecisionOutcome
import database.repository as repo

router = APIRouter()


# ---------- Pydantic response shapes ----------
class AssessmentOut(BaseModel):
    id: int
    applicant_id: int
    risk_score: int
    default_probability: float
    risk_category: str
    risk_grade: str
    approval: str
    status: str
    decision: Optional[str] = None
    created_at: str

    @classmethod
    def from_orm_row(cls, a):
        return cls(
            id=a.id, applicant_id=a.applicant_id, risk_score=a.risk_score,
            default_probability=a.default_probability, risk_category=a.risk_category,
            risk_grade=a.risk_grade, approval=a.approval, status=a.status.value,
            decision=a.decision.value if a.decision else None,
            created_at=a.created_at.isoformat(),
        )


class DecisionIn(BaseModel):
    reviewer_name: str
    decision: str            # "approved" | "declined" | "referred"
    note: Optional[str] = None


class ReviewIn(BaseModel):
    reviewer_name: str


# ---------- Persistence helper (called by the main credit-risk endpoint) ----------
def persist_assessment(db: Session, inputs: dict, result: dict,
                       analyst_name: str = "web-user"):
    """
    Bridge the simple form submission into the advanced schema:
    create/find an applicant from the inputs, attach the active model version,
    tie to a default analyst, and save. Returns the saved Assessment.
    """
    analyst = repo.get_or_create_user(db, name=analyst_name)
    applicant = repo.get_or_create_applicant(
        db,
        full_name=inputs.get("applicant_name"),
        age=inputs.get("age"),
        annual_income=inputs.get("income"),
    )
    model = repo.get_active_model(db)
    # Map the loan_purpose to a product if present.
    product = None
    purpose = (inputs.get("loan_purpose") or "").upper()
    if purpose:
        from database.models import LoanProduct
        product = db.query(LoanProduct).filter(LoanProduct.code == purpose).first()
    return repo.create_assessment(db, applicant=applicant, analyst=analyst,
                                  inputs=inputs, result=result,
                                  product=product, model_version=model)


# ---------- History endpoints ----------
@router.get("/assessments")
def list_assessments(limit: int = Query(20, le=100), offset: int = 0,
                     db: Session = Depends(get_session)):
    rows = repo.get_recent_assessments(db, limit=limit, offset=offset)
    return {"assessments": [AssessmentOut.from_orm_row(a).model_dump() for a in rows],
            "limit": limit, "offset": offset}


@router.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: int, db: Session = Depends(get_session)):
    from database.models import Assessment
    a = db.get(Assessment, assessment_id)
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")
    out = AssessmentOut.from_orm_row(a).model_dump()
    out["inputs"] = a.inputs
    out["result"] = a.result
    return out


# ---------- Workflow endpoints ----------
@router.post("/assessments/{assessment_id}/review")
def review(assessment_id: int, body: ReviewIn, db: Session = Depends(get_session)):
    from database.models import UserRole
    reviewer = repo.get_or_create_user(db, name=body.reviewer_name,
                                       role=UserRole.REVIEWER)
    from database.models import Assessment
    if not db.get(Assessment, assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    a = repo.review_assessment(db, assessment_id, reviewer)
    return AssessmentOut.from_orm_row(a).model_dump()


@router.post("/assessments/{assessment_id}/decide")
def decide(assessment_id: int, body: DecisionIn, db: Session = Depends(get_session)):
    from database.models import UserRole, Assessment
    if not db.get(Assessment, assessment_id):
        raise HTTPException(status_code=404, detail="Assessment not found")
    try:
        outcome = DecisionOutcome(body.decision)
    except ValueError:
        raise HTTPException(status_code=400,
                            detail="decision must be approved/declined/referred")
    reviewer = repo.get_or_create_user(db, name=body.reviewer_name,
                                       role=UserRole.REVIEWER)
    a = repo.decide_assessment(db, assessment_id, reviewer, outcome, body.note)
    return AssessmentOut.from_orm_row(a).model_dump()


# ---------- Analytics endpoints ----------
@router.get("/analytics/approval-rate")
def analytics_approval(db: Session = Depends(get_session)):
    return repo.approval_rate(db)


@router.get("/analytics/risk-distribution")
def analytics_risk(db: Session = Depends(get_session)):
    return {"distribution": repo.risk_distribution(db)}


@router.get("/analytics/grade-distribution")
def analytics_grade(db: Session = Depends(get_session)):
    return {"distribution": repo.grade_distribution(db)}


@router.get("/analytics/portfolio-exposure")
def analytics_exposure(db: Session = Depends(get_session)):
    return repo.portfolio_exposure(db)


@router.get("/analytics/over-time")
def analytics_time(days: int = Query(30, le=365), db: Session = Depends(get_session)):
    return {"series": repo.assessments_over_time(db, days=days)}
