"""
scoring.py
----------
The BUSINESS LOGIC layer. A raw probability like 0.27 means nothing to a loan
officer. This module turns it into:

  - a 0-100 risk score
  - a risk category (Very Low ... Critical)
  - an approval recommendation (Approved ... Rejected)
  - plain-English reasons

This is also your first taste of OOP done properly (Phase 2 builds on this).
We use a dataclass for the result and a class for the engine, which keeps
state (the loaded model) and behaviour (scoring) together = ENCAPSULATION.
"""

from dataclasses import dataclass, asdict
from enum import Enum

import joblib
import numpy as np
import pandas as pd


class RiskCategory(str, Enum):
    VERY_LOW = "Very Low Risk"
    LOW = "Low Risk"
    MEDIUM = "Medium Risk"
    HIGH = "High Risk"
    CRITICAL = "Critical Risk"


class Approval(str, Enum):
    APPROVED = "Approved"
    CONDITIONS = "Approved with Conditions"
    REVIEW = "Manual Review"
    REJECTED = "Rejected"


@dataclass
class RiskResult:
    """A structured, serialisable result. asdict() turns it into JSON for the API."""
    default_probability: float
    risk_score: int
    risk_category: str
    approval: str
    reasons: list

    def to_dict(self):
        return asdict(self)


class CreditRiskEngine:
    """
    Loads the trained model once and scores applicants.
    Keeping the model as instance state means the API loads it a single time,
    not on every request.
    """

    def __init__(self, model_path=None, schema_path=None):
        # Resolve paths relative to THIS file so the engine works whether you
        # run it from the repo root, the ml/ folder, or import it from the API.
        from pathlib import Path
        here = Path(__file__).resolve().parent
        model_path = model_path or here / "model.joblib"
        schema_path = schema_path or here / "schema.joblib"
        self.model = joblib.load(model_path)
        self.schema = joblib.load(schema_path)
        self.columns = self.schema["numeric"] + self.schema["categorical"]

    def _categorize(self, p: float) -> RiskCategory:
        # Thresholds are a BUSINESS decision, not an ML one. Tune to risk appetite.
        if p < 0.05:  return RiskCategory.VERY_LOW
        if p < 0.15:  return RiskCategory.LOW
        if p < 0.30:  return RiskCategory.MEDIUM
        if p < 0.55:  return RiskCategory.HIGH
        return RiskCategory.CRITICAL

    def _approval(self, cat: RiskCategory) -> Approval:
        return {
            RiskCategory.VERY_LOW: Approval.APPROVED,
            RiskCategory.LOW:      Approval.APPROVED,
            RiskCategory.MEDIUM:   Approval.CONDITIONS,
            RiskCategory.HIGH:     Approval.REVIEW,
            RiskCategory.CRITICAL: Approval.REJECTED,
        }[cat]

    def _reasons(self, applicant: dict) -> list:
        """
        Rule-based, human-readable reasons. In Phase 1 these are transparent
        heuristics tied to the strongest known risk drivers. Later you can wire
        in per-prediction SHAP values for fully model-driven explanations.
        """
        reasons = []
        if applicant.get("debt_to_income", 0) > 0.45:
            reasons.append("High debt-to-income ratio")
        if applicant.get("credit_score", 850) < 600:
            reasons.append("Low credit score")
        if applicant.get("num_delinquencies", 0) >= 2:
            reasons.append("Multiple past delinquencies")
        if applicant.get("credit_history_length", 99) < 3:
            reasons.append("Short credit history")
        if applicant.get("interest_rate", 0) > 18:
            reasons.append("Loan priced at high interest rate")
        if not reasons:
            reasons.append("No major risk factors detected")
        return reasons

    def score(self, applicant: dict) -> RiskResult:
        # Model expects a one-row DataFrame with the right columns.
        row = pd.DataFrame([{c: applicant.get(c) for c in self.columns}])
        p = float(self.model.predict_proba(row)[:, 1][0])
        cat = self._categorize(p)
        return RiskResult(
            default_probability=round(p, 4),
            risk_score=int(round(p * 100)),
            risk_category=cat.value,
            approval=self._approval(cat).value,
            reasons=self._reasons(applicant),
        )


if __name__ == "__main__":
    # Quick self-test with two contrasting applicants.
    engine = CreditRiskEngine()

    safe = {
        "age": 45, "income": 120000, "employment_length": 15, "credit_score": 780,
        "existing_loans": 0, "num_delinquencies": 0, "credit_history_length": 20,
        "loan_amount": 200000, "loan_tenure": 36, "interest_rate": 9.0,
        "debt_to_income": 0.15, "loan_purpose": "home",
    }
    risky = {
        "age": 26, "income": 35000, "employment_length": 1, "credit_score": 560,
        "existing_loans": 3, "num_delinquencies": 4, "credit_history_length": 2,
        "loan_amount": 300000, "loan_tenure": 12, "interest_rate": 22.0,
        "debt_to_income": 0.7, "loan_purpose": "personal",
    }

    import json
    print("SAFE applicant:")
    print(json.dumps(engine.score(safe).to_dict(), indent=2))
    print("\nRISKY applicant:")
    print(json.dumps(engine.score(risky).to_dict(), indent=2))
