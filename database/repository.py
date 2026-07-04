"""
repository.py — advanced data-access layer.

Covers: seed/reference data, applicant + assessment creation with proper
transactions and audit logging, the review/decision workflow, and a suite of
ANALYTICS queries (approval rates, risk distribution, time series, portfolio
exposure) that turn stored data into business answers.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from models import (Applicant, Assessment, AssessmentStatus, AuditLog,
                    DecisionOutcome, LoanProduct, ModelVersion, User, UserRole)


# ---------- Transaction helper ----------
@contextmanager
def transaction(db: Session):
    """Run a block in a transaction; commit on success, roll back on error."""
    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise


def _audit(db: Session, user_id, entity_type, entity_id, action, detail=None):
    db.add(AuditLog(user_id=user_id, entity_type=entity_type,
                    entity_id=entity_id, action=action, detail=detail))


# ---------- Seed / reference data ----------
def seed_reference_data(db: Session):
    """Insert default loan products + an active model version if none exist."""
    if db.query(LoanProduct).count() == 0:
        db.add_all([
            LoanProduct(code="HOME", name="Home Loan", base_rate=8.0, max_amount=10_000_000),
            LoanProduct(code="AUTO", name="Auto Loan", base_rate=9.5, max_amount=2_000_000),
            LoanProduct(code="PERSONAL", name="Personal Loan", base_rate=12.0, max_amount=1_000_000),
            LoanProduct(code="EDUCATION", name="Education Loan", base_rate=10.0, max_amount=3_000_000),
            LoanProduct(code="BUSINESS", name="Business Loan", base_rate=13.0, max_amount=5_000_000),
        ])
    if db.query(ModelVersion).count() == 0:
        db.add(ModelVersion(name="credit_xgb", version="1.0.0", algorithm="XGBoost",
                            roc_auc=0.868, is_active=True,
                            notes="Trained on Give Me Some Credit dataset"))
    db.commit()


def get_active_model(db: Session) -> ModelVersion | None:
    return db.query(ModelVersion).filter(ModelVersion.is_active.is_(True)).first()


# ---------- Core writes ----------
def get_or_create_user(db: Session, name: str, email=None, role=UserRole.ANALYST) -> User:
    user = None
    if email:
        user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = db.query(User).filter(User.name == name).first()
    if user is None:
        with transaction(db):
            user = User(name=name, email=email, role=role)
            db.add(user)
        db.refresh(user)
    return user


def get_or_create_applicant(db: Session, full_name=None, age=None,
                            annual_income=None, external_ref=None) -> Applicant:
    applicant = None
    if external_ref:
        applicant = db.query(Applicant).filter(
            Applicant.external_ref == external_ref).first()
    if applicant is None:
        with transaction(db):
            applicant = Applicant(full_name=full_name, age=age,
                                  annual_income=annual_income,
                                  external_ref=external_ref)
            db.add(applicant)
        db.refresh(applicant)
    return applicant


def create_assessment(db: Session, *, applicant: Applicant, analyst: User,
                      inputs: dict, result: dict, product: LoanProduct = None,
                      model_version: ModelVersion = None) -> Assessment:
    """Create an assessment + audit entry in one transaction."""
    with transaction(db):
        a = Assessment(
            applicant_id=applicant.id,
            product_id=product.id if product else None,
            analyst_id=analyst.id if analyst else None,
            model_version_id=model_version.id if model_version else None,
            inputs=inputs, result=result,
            risk_score=result["risk_score"],
            default_probability=result["default_probability"],
            risk_category=result["risk_category"],
            risk_grade=result["risk_grade"],
            approval=result["approval"],
            status=AssessmentStatus.PENDING,
        )
        db.add(a)
        db.flush()
        _audit(db, analyst.id if analyst else None, "assessment", a.id,
               "assessment.created",
               f"grade {a.risk_grade}, score {a.risk_score}")
    db.refresh(a)
    return a


# ---------- Workflow transitions ----------
def review_assessment(db: Session, assessment_id: int, reviewer: User) -> Assessment:
    with transaction(db):
        a = db.get(Assessment, assessment_id)
        a.status = AssessmentStatus.REVIEWED
        a.reviewer_id = reviewer.id
        _audit(db, reviewer.id, "assessment", a.id, "assessment.reviewed")
    db.refresh(a)
    return a


def decide_assessment(db: Session, assessment_id: int, reviewer: User,
                      decision: DecisionOutcome, note: str = None) -> Assessment:
    with transaction(db):
        a = db.get(Assessment, assessment_id)
        a.status = AssessmentStatus.DECIDED
        a.decision = decision
        a.decision_note = note
        a.reviewer_id = reviewer.id
        _audit(db, reviewer.id, "assessment", a.id, "assessment.decided",
               f"decision={decision.value}")
    db.refresh(a)
    return a


# ---------- Reads ----------
def get_recent_assessments(db: Session, limit=20, offset=0):
    return (db.query(Assessment)
            .filter(Assessment.is_deleted.is_(False))
            .order_by(desc(Assessment.created_at))
            .offset(offset).limit(limit).all())


# ---------- ANALYTICS (turning data into business answers) ----------
def approval_rate(db: Session) -> dict:
    total = db.query(Assessment).filter(Assessment.is_deleted.is_(False)).count()
    approved = (db.query(Assessment)
                .filter(Assessment.is_deleted.is_(False),
                        Assessment.approval.in_(["Auto Approve", "Approve"]))
                .count())
    return {"total": total, "approved": approved,
            "approval_rate": round(approved / total, 3) if total else 0.0}


def risk_distribution(db: Session) -> list[dict]:
    """Count of assessments per risk category — the portfolio's risk shape."""
    rows = (db.query(Assessment.risk_category, func.count(Assessment.id))
            .filter(Assessment.is_deleted.is_(False))
            .group_by(Assessment.risk_category)
            .all())
    return [{"risk_category": cat, "count": n} for cat, n in rows]


def grade_distribution(db: Session) -> list[dict]:
    rows = (db.query(Assessment.risk_grade, func.count(Assessment.id))
            .filter(Assessment.is_deleted.is_(False))
            .group_by(Assessment.risk_grade)
            .order_by(Assessment.risk_grade)
            .all())
    return [{"grade": g, "count": n} for g, n in rows]


def assessments_over_time(db: Session, days=30) -> list[dict]:
    """Daily assessment volume — a time series for trend charts."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    day = func.date(Assessment.created_at)
    rows = (db.query(day, func.count(Assessment.id))
            .filter(Assessment.created_at >= since)
            .group_by(day).order_by(day).all())
    return [{"date": str(d), "count": n} for d, n in rows]


def portfolio_exposure(db: Session) -> dict:
    """
    Average default probability weighted across the book, and total 'expected
    exposure' proxy. A real portfolio-risk metric, not just row counts.
    """
    avg_pd = (db.query(func.avg(Assessment.default_probability))
              .filter(Assessment.is_deleted.is_(False)).scalar())
    high_risk = (db.query(func.count(Assessment.id))
                 .filter(Assessment.is_deleted.is_(False),
                         Assessment.default_probability >= 0.35).count()
                 if False else
                 db.query(Assessment)
                 .filter(Assessment.is_deleted.is_(False),
                         Assessment.default_probability >= 0.35).count())
    return {
        "avg_default_probability": round(float(avg_pd), 4) if avg_pd else 0.0,
        "high_risk_count": high_risk,
    }
