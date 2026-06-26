"""
credit_service.py
-----------------
THE SERVICE LAYER — the bridge between the web API and your ML engine.

Design principle (SEPARATION OF CONCERNS): the API routes shouldn't know how
the model works, and the model shouldn't know it's behind a web server. This
service sits between them. If you later swap the model or add caching, only this
file changes; the routes stay untouched.

It loads CreditRiskEngine ONCE when the app starts (not per request), which is
important: loading a model on every call would make the API painfully slow.
"""

import sys
from pathlib import Path

# Make the ml/ package importable. We walk up from this file to the repo root,
# then point Python at the ml/ folder so `from credit_risk.scoring import ...` works.
REPO_ROOT = Path(__file__).resolve().parents[3]
ML_DIR = REPO_ROOT / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from credit_risk.scoring import CreditRiskEngine  # noqa: E402


class CreditService:
    """Thin wrapper that owns the engine instance and exposes a clean method."""

    def __init__(self):
        self._engine = None  # lazy: not loaded until first needed

    def load(self):
        """Called once at app startup. Raises clearly if the model is missing."""
        try:
            self._engine = CreditRiskEngine()
        except FileNotFoundError as e:
            raise RuntimeError(
                "Model file not found. Run the training pipeline first:\n"
                "  cd ml && python3 credit_risk/train.py"
            ) from e

    @property
    def is_loaded(self) -> bool:
        return self._engine is not None

    def score(self, applicant: dict) -> dict:
        """Score one applicant. Returns a plain dict ready to become JSON."""
        if self._engine is None:
            raise RuntimeError("Engine not loaded. Call load() at startup.")
        return self._engine.score(applicant).to_dict()


# A single shared instance the whole app uses (simple dependency injection).
credit_service = CreditService()
