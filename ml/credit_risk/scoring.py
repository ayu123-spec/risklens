"""
scoring.py
----------
The BUSINESS LOGIC layer. Converts a raw default probability into a full,
industry-style credit decision:

  - 6 risk tiers (Very Low -> Extreme)
  - a letter risk grade (AAA -> C), the way lenders actually grade borrowers
  - an approval recommendation
  - risk-based pricing (suggested interest rate)
  - max eligible loan amount (shrinks as risk rises)
  - an HONEST confidence score (distance from the decision boundary)
  - plain-English reasons, generated only from features the model actually uses
  - a one-line customer summary

OOP: a dataclass for the structured result, a class for the engine that owns
the model. Thresholds and pricing are BUSINESS decisions, deliberately kept
separate from the ML so they can be tuned to a lender's risk appetite.
"""

from dataclasses import dataclass, asdict
from enum import Enum

import joblib
import numpy as np
import pandas as pd


class RiskCategory(str, Enum):
    VERY_LOW = "Very Low Risk"
    LOW = "Low Risk"
    MODERATE = "Moderate Risk"
    HIGH = "High Risk"
    VERY_HIGH = "Very High Risk"
    EXTREME = "Extreme Risk"


class Approval(str, Enum):
    AUTO_APPROVE = "Auto Approve"
    APPROVE = "Approve"
    CONDITIONAL = "Approve with Conditions"
    MANUAL_REVIEW = "Manual Review"
    COLLATERAL = "Reject or Require Collateral"
    REJECT = "Reject"


@dataclass
class RiskResult:
    """Structured, serialisable result. asdict() turns it into JSON for the API."""
    default_probability: float
    risk_score: int
    risk_category: str
    risk_grade: str
    approval: str
    suggested_interest_rate: float
    max_eligible_loan: int
    confidence: int
    reasons: list
    summary: str

    def to_dict(self):
        return asdict(self)


class CreditRiskEngine:
    """Loads the trained model once and produces a full credit decision."""

    def __init__(self, model_path=None, schema_path=None):
        from pathlib import Path
        here = Path(__file__).resolve().parent
        model_path = model_path or here / "model.joblib"
        schema_path = schema_path or here / "schema.joblib"
        self.model = joblib.load(model_path)
        self.schema = joblib.load(schema_path)
        self.columns = self.schema["numeric"] + self.schema["categorical"]

    # ---- Risk tiering (6 industry-style bands) ----
    def _categorize(self, p: float) -> RiskCategory:
        if p < 0.05:  return RiskCategory.VERY_LOW
        if p < 0.10:  return RiskCategory.LOW
        if p < 0.20:  return RiskCategory.MODERATE
        if p < 0.35:  return RiskCategory.HIGH
        if p < 0.50:  return RiskCategory.VERY_HIGH
        return RiskCategory.EXTREME

    # ---- Letter grade (AAA -> C), finer than the category ----
    def _grade(self, p: float) -> str:
        if p < 0.02:  return "AAA"
        if p < 0.05:  return "AA"
        if p < 0.10:  return "A"
        if p < 0.20:  return "BBB"
        if p < 0.35:  return "BB"
        if p < 0.50:  return "B"
        if p < 0.70:  return "CCC"
        if p < 0.85:  return "CC"
        return "C"

    def _approval(self, cat: RiskCategory) -> Approval:
        return {
            RiskCategory.VERY_LOW:  Approval.AUTO_APPROVE,
            RiskCategory.LOW:       Approval.APPROVE,
            RiskCategory.MODERATE:  Approval.CONDITIONAL,
            RiskCategory.HIGH:      Approval.MANUAL_REVIEW,
            RiskCategory.VERY_HIGH: Approval.COLLATERAL,
            RiskCategory.EXTREME:   Approval.REJECT,
        }[cat]

    # ---- Risk-based pricing: riskier borrowers are priced higher ----
    def _interest_rate(self, cat: RiskCategory) -> float:
        return {
            RiskCategory.VERY_LOW:  8.0,
            RiskCategory.LOW:       9.5,
            RiskCategory.MODERATE: 12.0,
            RiskCategory.HIGH:     16.0,
            RiskCategory.VERY_HIGH: 20.0,
            RiskCategory.EXTREME:   0.0,   # rejected -> no offer
        }[cat]

    # ---- Max eligible loan: a fraction of requested, shrinking with risk ----
    def _max_loan(self, cat: RiskCategory, requested: float) -> int:
        frac = {
            RiskCategory.VERY_LOW:  1.00,
            RiskCategory.LOW:       0.90,
            RiskCategory.MODERATE:  0.75,
            RiskCategory.HIGH:      0.50,
            RiskCategory.VERY_HIGH: 0.25,
            RiskCategory.EXTREME:   0.0,
        }[cat]
        return int(round((requested or 0) * frac))

    # ---- HONEST confidence: how decisive is the probability? ----
    def _confidence(self, p: float) -> int:
        """
        Confidence = how far the probability sits from the 50% decision boundary,
        scaled to 0-100. A prediction near 0% or 100% is highly confident; one
        near 50% is a coin-flip and gets low confidence. This is a real, defensible
        definition -- NOT a made-up number layered on top of the probability.
        """
        return int(round(abs(p - 0.5) / 0.5 * 100))

    def _reasons(self, applicant: dict) -> list:
        """
        Human-readable reasons, generated ONLY from features the model actually
        uses. We never cite a factor (e.g. credit utilization) that isn't a real
        model input -- an explanation must reflect the actual decision.
        """
        reasons = []
        if applicant.get("debt_to_income", 0) > 0.45:
            reasons.append(f"High debt-to-income ratio ({applicant['debt_to_income']:.0%})")
        if applicant.get("credit_score", 850) < 600:
            reasons.append(f"Low credit score ({applicant.get('credit_score')})")
        if applicant.get("num_delinquencies", 0) >= 2:
            reasons.append(f"{applicant['num_delinquencies']} past delinquencies")
        if applicant.get("credit_history_length", 99) < 3:
            reasons.append(f"Short credit history ({applicant.get('credit_history_length')} yrs)")
        if applicant.get("interest_rate", 0) > 18:
            reasons.append("Loan priced at high interest rate")
        if applicant.get("existing_loans", 0) >= 4:
            reasons.append(f"{applicant['existing_loans']} existing loans")
        if not reasons:
            reasons.append("No major risk factors detected")
        return reasons

    def _summary(self, cat: RiskCategory, grade: str, p: float, reasons: list) -> str:
        """A concise narrative explaining the rating, in plain language."""
        lead = reasons[0].lower() if reasons and "No major" not in reasons[0] else None
        band = cat.value.replace(" Risk", "")
        if lead:
            return (f"Graded {grade} ({band}) with an estimated {p:.0%} default probability, "
                    f"driven mainly by {lead}.")
        return (f"Graded {grade} ({band}) with an estimated {p:.0%} default probability; "
                f"no major risk factors flagged.")

    def score(self, applicant: dict) -> RiskResult:
        row = pd.DataFrame([{c: applicant.get(c) for c in self.columns}])
        p = float(self.model.predict_proba(row)[:, 1][0])
        cat = self._categorize(p)
        grade = self._grade(p)
        reasons = self._reasons(applicant)
        return RiskResult(
            default_probability=round(p, 4),
            risk_score=int(round(p * 100)),
            risk_category=cat.value,
            risk_grade=grade,
            approval=self._approval(cat).value,
            suggested_interest_rate=self._interest_rate(cat),
            max_eligible_loan=self._max_loan(cat, applicant.get("loan_amount", 0)),
            confidence=self._confidence(p),
            reasons=reasons,
            summary=self._summary(cat, grade, p, reasons),
        )


if __name__ == "__main__":
    import json
    engine = CreditRiskEngine()
    safe = {"age": 45, "income": 120000, "employment_length": 15, "credit_score": 780,
            "existing_loans": 0, "num_delinquencies": 0, "credit_history_length": 20,
            "loan_amount": 200000, "loan_tenure": 36, "interest_rate": 9.0,
            "debt_to_income": 0.15, "loan_purpose": "home"}
    risky = {"age": 26, "income": 35000, "employment_length": 1, "credit_score": 560,
             "existing_loans": 5, "num_delinquencies": 4, "credit_history_length": 2,
             "loan_amount": 300000, "loan_tenure": 12, "interest_rate": 22.0,
             "debt_to_income": 0.7, "loan_purpose": "personal"}
    print("SAFE:\n", json.dumps(engine.score(safe).to_dict(), indent=2))
    print("\nRISKY:\n", json.dumps(engine.score(risky).to_dict(), indent=2))
