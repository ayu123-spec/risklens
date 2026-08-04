"""
fraud_routes.py
---------------
HTTP endpoints for the fraud-detection capability, mounted under /api/fraud.

  GET  /api/fraud/model-info        model card: metrics, threshold table, top features
  GET  /api/fraud/samples           the demo transactions (answer withheld)
  POST /api/fraud/score/{id}        score one demo transaction, then reveal the truth
  POST /api/fraud/score             score an arbitrary transaction payload

Scoring a stored sample runs the model live — it is not a replayed prediction.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.fraud_service import fraud_service, DEFAULT_THRESHOLD

router = APIRouter()
\

class TransactionIn(BaseModel):
    amount: float = Field(..., ge=0, description="Transaction amount")
    time: float = Field(0, ge=0, description="Seconds since the first transaction")
    features: dict = Field(default_factory=dict, description="V1..V28 PCA components")


@router.get("/fraud/model-info", tags=["fraud"])
def model_info():
    """Model card — what this model is and how well it actually performs."""
    return fraud_service.model_info()


@router.get("/fraud/samples", tags=["fraud"])
def samples():
    """
    Real transactions from the held-out test set. The ground truth is deliberately
    withheld so the model has to be run before the answer is revealed.
    """
    if not fraud_service.is_loaded:
        raise HTTPException(status_code=503, detail="Fraud model is not loaded.")
    return {"samples": fraud_service.get_samples()}


@router.post("/fraud/score/{sample_id}", tags=["fraud"])
def score_sample(
    sample_id: int,
    threshold: float = Query(DEFAULT_THRESHOLD, ge=0.0, le=1.0),
):
    """Score one demo transaction and reveal whether it was genuinely fraud."""
    if not fraud_service.is_loaded:
        raise HTTPException(status_code=503, detail="Fraud model is not loaded.")

    sample = fraud_service.get_sample(sample_id)
    if sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    result = fraud_service.score(sample, threshold=threshold)

    actual_fraud = bool(sample["actual_fraud"])
    flagged = result["is_flagged"]
    if flagged and actual_fraud:
        outcome = "true_positive"
    elif flagged and not actual_fraud:
        outcome = "false_positive"
    elif not flagged and actual_fraud:
        outcome = "false_negative"
    else:
        outcome = "true_negative"

    result["ground_truth"] = {
        "actual_fraud": actual_fraud,
        "outcome": outcome,
        "model_was_right": outcome in ("true_positive", "true_negative"),
    }
    return result


@router.post("/fraud/score", tags=["fraud"])
def score_transaction(
    transaction: TransactionIn,
    threshold: float = Query(DEFAULT_THRESHOLD, ge=0.0, le=1.0),
):
    """Score an arbitrary transaction payload."""
    if not fraud_service.is_loaded:
        raise HTTPException(status_code=503, detail="Fraud model is not loaded.")
    try:
        return fraud_service.score(transaction.model_dump(), threshold=threshold)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fraud scoring failed: {exc}")
