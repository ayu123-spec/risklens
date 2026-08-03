"""
routes.py
---------
THE API ROUTES — the actual HTTP endpoints.

FastAPI's APIRouter lets us group related endpoints. Each function below becomes
a URL. The decorators (@router.post / @router.get) declare the method and path.
Because we annotate the function with our Pydantic schemas, FastAPI automatically:
  - validates the incoming JSON,
  - converts it to a Python object,
  - documents it on the /docs page,
  - and validates our response on the way out.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.credit import (
    CreditRiskRequest, CreditRiskResponse, HealthResponse,
)
from app.services.credit_service import credit_service
from fastapi import Depends
from sqlalchemy.orm import Session
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from database.db import get_session
from db_routes import persist_assessment


router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    """Liveness check. Deployment platforms (Render) ping this to know the app is up."""
    return HealthResponse(
        status="ok",
        model_loaded=credit_service.is_loaded,
    )


@router.post("/credit-risk", response_model=CreditRiskResponse, tags=["credit"])
def assess_credit_risk(request: CreditRiskRequest, db: Session = Depends(get_session)):
    """
    Score a loan applicant's default risk, and persist the assessment.
    """
    try:
        inputs = request.model_dump()
        result = credit_service.score(inputs)
        # Persist to the database — but never let a save failure break scoring.
        try:
            result_dict = result.model_dump() if hasattr(result, "model_dump") else dict(result)
            persist_assessment(db, inputs, result_dict)
        except Exception:
            pass  # logged inside persist_assessment; user still gets their score
        return result
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")