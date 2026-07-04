"""
models.py — advanced relational schema for RiskLens (Phase 6, comprehensive).

Design goals (what makes this "bank-grade" rather than a flat table):

  users          — analysts, with roles.
  applicants     — the people being assessed, as first-class records (reusable
                   across multiple assessments, not re-entered each time).
  loan_products  — the products a loan can be assessed against (home/auto/etc.),
                   each with its own rate band and limits.
  model_versions — which model + version produced a score (ML governance: you
                   must know which model made which decision, for audit/rollback).
  assessments    — links applicant + product + model_version + user, with the
                   result AND a status workflow (pending -> reviewed -> decided).
  audit_log      — append-only action trail.

Advanced touches:
  - Enums for controlled vocabularies (status, role, decision) — DB-enforced.
  - Indexes on the columns you actually query/filter/sort by.
  - CheckConstraints so bad data can't be inserted (score 0-100, prob 0-1).
  - Soft-delete (is_deleted) so records are archived, never truly lost.
  - Timestamps with created/updated tracking.
  - Relationships wired both ways for clean ORM navigation.
"""
from datetime import datetime, timezone
import enum

from sqlalchemy import (JSON, Boolean, CheckConstraint, Column, DateTime, Enum,
                        Float, ForeignKey, Index, Integer, Numeric, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


# ---------- Controlled vocabularies (DB-enforced enums) ----------
class UserRole(str, enum.Enum):
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class AssessmentStatus(str, enum.Enum):
    PENDING = "pending"        # scored, awaiting human review
    REVIEWED = "reviewed"      # a reviewer has looked at it
    DECIDED = "decided"        # final decision recorded
    ARCHIVED = "archived"


class DecisionOutcome(str, enum.Enum):
    APPROVED = "approved"
    DECLINED = "declined"
    REFERRED = "referred"      # sent for manual/senior review


# ---------- Mixins ----------
class TimestampMixin:
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                        onupdate=_utcnow, nullable=False)


class SoftDeleteMixin:
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)


# ---------- Tables ----------
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.ANALYST, nullable=False)

    assessments = relationship("Assessment", back_populates="analyst",
                               foreign_keys="Assessment.analyst_id")

    def __repr__(self):
        return f"<User id={self.id} name={self.name!r} role={self.role.value}>"


class Applicant(Base, TimestampMixin, SoftDeleteMixin):
    """A person who can be assessed. First-class so history ties to a person."""
    __tablename__ = "applicants"

    id = Column(Integer, primary_key=True)
    external_ref = Column(String(64), unique=True, nullable=True,
                          doc="Optional external/customer ID")
    full_name = Column(String(160), nullable=True)
    age = Column(Integer, nullable=True)
    annual_income = Column(Numeric(14, 2), nullable=True)

    assessments = relationship("Assessment", back_populates="applicant")

    __table_args__ = (
        CheckConstraint("age IS NULL OR (age >= 18 AND age <= 120)",
                        name="ck_applicant_age"),
        Index("ix_applicant_name", "full_name"),
    )

    def __repr__(self):
        return f"<Applicant id={self.id} name={self.full_name!r}>"


class LoanProduct(Base, TimestampMixin):
    """A product an assessment is made against (home loan, auto loan, etc.)."""
    __tablename__ = "loan_products"

    id = Column(Integer, primary_key=True)
    code = Column(String(32), unique=True, nullable=False)   # e.g. "HOME"
    name = Column(String(120), nullable=False)
    base_rate = Column(Float, nullable=False)                # starting interest %
    max_amount = Column(Numeric(14, 2), nullable=False)      # product ceiling
    active = Column(Boolean, default=True, nullable=False)

    assessments = relationship("Assessment", back_populates="product")

    def __repr__(self):
        return f"<LoanProduct {self.code} rate={self.base_rate}>"


class ModelVersion(Base, TimestampMixin):
    """
    ML governance: records which model + version scored an assessment. Real
    lenders MUST be able to say 'this decision came from model X v1.2', for
    audit, reproducibility, and rollback. Only one version is 'active' at a time.
    """
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)                # e.g. "credit_xgb"
    version = Column(String(32), nullable=False)             # e.g. "1.0.0"
    algorithm = Column(String(60), nullable=True)            # e.g. "XGBoost"
    roc_auc = Column(Float, nullable=True)                   # recorded metric
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    notes = Column(Text, nullable=True)

    assessments = relationship("Assessment", back_populates="model_version")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_name_version"),
    )

    def __repr__(self):
        return f"<ModelVersion {self.name}:{self.version} active={self.is_active}>"


class Assessment(Base, TimestampMixin, SoftDeleteMixin):
    """
    The core record: ties together WHO (analyst) assessed WHOM (applicant) for
    WHAT (product) using WHICH model (model_version), the result, and a status
    workflow with an optional final decision.
    """
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True)

    # Foreign keys — the relational heart of the schema.
    applicant_id = Column(Integer, ForeignKey("applicants.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("loan_products.id"), nullable=True, index=True)
    analyst_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    model_version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=True, index=True)

    # Inputs and full result as JSON (flexible); key results as columns (queryable).
    inputs = Column(JSON, nullable=False)
    result = Column(JSON, nullable=True)
    risk_score = Column(Integer, nullable=False)
    default_probability = Column(Float, nullable=False)
    risk_category = Column(String(40), nullable=False, index=True)
    risk_grade = Column(String(8), nullable=False, index=True)
    approval = Column(String(40), nullable=False)

    # Workflow.
    status = Column(Enum(AssessmentStatus), default=AssessmentStatus.PENDING,
                    nullable=False, index=True)
    decision = Column(Enum(DecisionOutcome), nullable=True)
    decision_note = Column(Text, nullable=True)

    # Relationships.
    applicant = relationship("Applicant", back_populates="assessments")
    product = relationship("LoanProduct", back_populates="assessments")
    analyst = relationship("User", back_populates="assessments",
                           foreign_keys=[analyst_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    model_version = relationship("ModelVersion", back_populates="assessments")

    __table_args__ = (
        CheckConstraint("risk_score >= 0 AND risk_score <= 100",
                        name="ck_assessment_score_range"),
        CheckConstraint("default_probability >= 0 AND default_probability <= 1",
                        name="ck_assessment_prob_range"),
        # Composite index: a very common query is "recent assessments by category".
        Index("ix_assessment_created_category", "created_at", "risk_category"),
    )

    def __repr__(self):
        return (f"<Assessment id={self.id} score={self.risk_score} "
                f"grade={self.risk_grade} status={self.status.value}>")


class AuditLog(Base):
    """Append-only trail. No updated_at (never modified), no soft-delete (never removed)."""
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    entity_type = Column(String(40), nullable=False)   # e.g. "assessment"
    entity_id = Column(Integer, nullable=True)
    action = Column(String(80), nullable=False, index=True)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False, index=True)

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
    )

    def __repr__(self):
        return f"<AuditLog id={self.id} action={self.action!r}>"
