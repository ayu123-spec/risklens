"""
schemas.py
----------
PYDANTIC SCHEMAS — the contract for what goes in and out of the API.

Why this matters: without validation, a request missing `credit_score` or
sending `age: "banana"` would crash deep inside the model with a confusing
error. Pydantic checks every field BEFORE it reaches your engine and returns a
clean 422 error explaining exactly what was wrong. This is one of the biggest
reasons to use FastAPI.

Each Field(...) below sets sensible bounds (ge = greater-or-equal,
le = less-or-equal) so impossible values are rejected at the door.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class CreditRiskRequest(BaseModel):
    """The applicant data the caller must send. Matches the model's features."""
    age: int = Field(..., ge=18, le=100, description="Applicant age in years")
    income: float = Field(..., gt=0, description="Annual income")
    employment_length: float = Field(..., ge=0, le=50, description="Years employed")
    credit_score: int = Field(..., ge=300, le=850, description="Credit bureau score")
    existing_loans: int = Field(..., ge=0, le=50, description="Count of current loans")
    num_delinquencies: int = Field(..., ge=0, le=50, description="Past missed payments")
    credit_history_length: int = Field(..., ge=0, le=80, description="Years of credit history")
    loan_amount: float = Field(..., gt=0, description="Requested loan amount")
    loan_tenure: int = Field(..., gt=0, le=480, description="Loan term in months")
    interest_rate: float = Field(..., gt=0, le=40, description="Annual interest rate %")
    debt_to_income: float = Field(..., ge=0, le=3, description="Debt-to-income ratio")
    loan_purpose: Literal["home", "auto", "personal", "education", "business"]

    # An example payload that shows up in the auto-generated /docs page.
    model_config = {
        "json_schema_extra": {
            "example": {
                "age": 26, "income": 35000, "employment_length": 1,
                "credit_score": 560, "existing_loans": 3, "num_delinquencies": 4,
                "credit_history_length": 2, "loan_amount": 300000, "loan_tenure": 12,
                "interest_rate": 22.0, "debt_to_income": 0.7, "loan_purpose": "personal",
            }
        }
    }


class CreditRiskResponse(BaseModel):
    """What the API sends back. Mirrors the engine's RiskResult."""
    default_probability: float
    risk_score: int
    risk_category: str
    risk_grade: str
    approval: str
    suggested_interest_rate: float
    max_eligible_loan: int
    confidence: int
    reasons: List[str]
    summary: str


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
