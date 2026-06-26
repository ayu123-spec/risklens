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

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health():
    """Liveness check. Deployment platforms (Render) ping this to know the app is up."""
    return HealthResponse(
        status="ok",
        model_loaded=credit_service.is_loaded,
    )


@router.post("/credit-risk", response_model=CreditRiskResponse, tags=["credit"])
def assess_credit_risk(request: CreditRiskRequest):
    """
    Score a loan applicant's default risk.

    Send applicant features as JSON; get back a probability, 0-100 score,
    risk category, approval recommendation, and the reasons behind it.
    """
    try:
        # request.model_dump() turns the validated Pydantic object into a dict
        # the engine understands.
        result = credit_service.score(request.model_dump())
        return result
    except RuntimeError as e:
        # 503 = service unavailable, e.g. model wasn't loaded.
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        # Catch-all so an unexpected failure returns clean JSON, not a stack trace.
        raise HTTPException(status_code=500, detail=f"Scoring failed: {e}")
