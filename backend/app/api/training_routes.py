"""
training_routes.py
------------------
API endpoints for retraining the model on uploaded data.

  POST /api/train        — upload a CSV, retrain the model on it
  GET  /api/schema       — see what fields the current model expects

These let you retrain from the API (e.g. from the frontend, or curl/Postman)
instead of the command line. The heavy lifting reuses train_custom.py's logic.

SAFETY NOTE: retraining replaces the live model. In a real production system
you'd gate this behind authentication and run it as a background job. Here it's
synchronous and open — fine for development, flagged for hardening later.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.credit_service import credit_service

router = APIRouter()

# Path to the ml/credit_risk folder where the trainer and model live.
ML_DIR = Path(__file__).resolve().parents[3] / "ml" / "credit_risk"


@router.get("/schema", tags=["training"])
def get_schema():
    """Return the fields the currently loaded model expects."""
    import joblib
    try:
        schema = joblib.load(ML_DIR / "schema.joblib")
        return {
            "numeric_features": schema["numeric"],
            "categorical_features": schema["categorical"],
            "total_features": len(schema["numeric"]) + len(schema["categorical"]),
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No model schema found. Train a model first.")


@router.post("/train", tags=["training"])
async def train_on_upload(
    file: UploadFile = File(..., description="CSV file to train on"),
    target: str = Form(None, description="Name of the target column (optional if named 'defaulted', etc.)"),
    drop: str = Form("", description="Comma-separated columns to exclude, e.g. an ID column"),
):
    """
    Upload a CSV and retrain the model on it.

    The uploaded file is saved to a temp location, train_custom.py runs on it,
    and if successful the new model replaces the live one (and is reloaded so
    /credit-risk immediately uses it).
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file.")

    # Save the upload to a temp file.
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # Build the command to run the flexible trainer.
    cmd = [sys.executable, str(ML_DIR / "train_custom.py"), tmp_path]
    if target:
        cmd += ["--target", target]
    if drop:
        cmd += ["--drop", drop]

    # Run it. Capture output so we can return success info or the error message.
    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(tmp_path).unlink(missing_ok=True)  # clean up temp file

    if result.returncode != 0:
        # Training failed — return the helpful message from the trainer.
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Training failed. See details.",
                "output": result.stdout[-1500:] + result.stderr[-500:],
            },
        )

    # Success — reload the new model into the running API.
    credit_service.load()

    return {
        "status": "trained",
        "message": "Model retrained and reloaded. /credit-risk now uses the new model.",
        "training_log": result.stdout[-1500:],
    }
