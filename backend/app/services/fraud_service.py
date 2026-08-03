"""
fraud_service.py
----------------
Loads the trained fraud-detection model and scores transactions.

IMPORTANT - why nothing here is pickled:
A joblib/pickle of an XGBoost model is tied to the exact library version that
wrote it. Loading it under a different xgboost or Python version fails with
"input stream corrupted". This project runs on one Python locally and a
different one inside the Docker container, so the artifacts are stored in
version-portable formats instead:

  fraud_model.json    XGBoost's own native format (Booster.save_model)
  fraud_meta.json     plain JSON - feature order, scaler mean/scale, metrics
  fraud_samples.json  plain JSON - demo transactions

The StandardScaler is just (x - mean) / scale, so its two numbers live in the
meta file and the transform is applied directly. No sklearn needed at runtime.

Model: Kaggle Credit Card Fraud (ULB), 284,807 real transactions, 0.173% fraud.
"""
import json
from pathlib import Path

import numpy as np
import xgboost as xgb

_HERE = Path(__file__).resolve().parent

# Operating threshold. The model is tuned for RECALL: a missed fraud costs the
# full transaction, while a false alarm costs a "was this you?" check. 0.10
# catches ~87% of fraud at ~75% precision (see the threshold table in the meta).
DEFAULT_THRESHOLD = 0.10


class FraudService:
    def __init__(self):
        self.booster = None
        self.meta = None
        self.samples = []
        self.is_loaded = False
        self.load_error = None

    def load(self):
        """Load model, metadata and demo samples. Safe to call once at startup."""
        try:
            self.booster = xgb.Booster()
            self.booster.load_model(str(_HERE / "fraud_model.json"))
            with open(_HERE / "fraud_meta.json") as f:
                self.meta = json.load(f)
            with open(_HERE / "fraud_samples.json") as f:
                self.samples = json.load(f)
            self.is_loaded = True
            self.load_error = None
        except Exception as exc:
            # Never crash the whole API because the fraud model is missing --
            # credit scoring must keep working.
            self.load_error = str(exc)
            self.is_loaded = False
            print(f"WARNING: fraud model failed to load ({exc}). "
                  f"Fraud endpoints will report unavailable.")

    # ---------- internals ----------
    def _build_row(self, transaction: dict) -> np.ndarray:
        """Turn a raw transaction dict into the feature vector the model expects."""
        v = transaction.get("features") or {}
        amount = float(transaction.get("amount", 0.0))
        time_s = float(transaction.get("time", 0.0))

        mean = self.meta["scaler"]["mean"]     # [Amount, Time]
        scale = self.meta["scaler"]["scale"]

        row = {f"V{i}": float(v.get(f"V{i}", 0.0)) for i in range(1, 29)}
        row["Amount_log"] = float(np.log1p(amount))
        row["Amount_scaled"] = (amount - mean[0]) / scale[0]
        row["Time_scaled"] = (time_s - mean[1]) / scale[1]
        row["Hour"] = (time_s / 3600) % 24

        return np.array([[row[f] for f in self.meta["features"]]], dtype=np.float32)

    # ---------- public API ----------
    def score(self, transaction: dict, threshold: float = DEFAULT_THRESHOLD) -> dict:
        if not self.is_loaded:
            raise RuntimeError("Fraud model is not loaded.")

        X = self._build_row(transaction)
        dmat = xgb.DMatrix(X, feature_names=self.meta["features"])
        probability = float(self.booster.predict(dmat)[0])
        is_flagged = probability >= threshold

        if probability >= 0.90:
            band, verdict = "Very High", "Block and investigate"
        elif probability >= 0.50:
            band, verdict = "High", "Hold for manual review"
        elif probability >= threshold:
            band, verdict = "Elevated", "Verify with cardholder"
        elif probability >= 0.01:
            band, verdict = "Low", "Allow, log for monitoring"
        else:
            band, verdict = "Very Low", "Allow"

        return {
            "fraud_probability": round(probability, 6),
            "fraud_score": round(probability * 100, 2),
            "is_flagged": bool(is_flagged),
            "risk_band": band,
            "recommended_action": verdict,
            "threshold_used": threshold,
            "amount": float(transaction.get("amount", 0.0)),
            "hour_of_day": round(float((float(transaction.get("time", 0.0)) / 3600) % 24), 1),
        }

    def get_samples(self) -> list:
        """Demo transactions, WITHOUT giving away the answer up front."""
        return [
            {"id": s["id"], "amount": s["amount"], "hour": s["hour"], "time": s["time"]}
            for s in self.samples
        ]

    def get_sample(self, sample_id: int) -> dict | None:
        return next((s for s in self.samples if s["id"] == sample_id), None)

    def model_info(self) -> dict:
        if not self.is_loaded:
            return {"available": False, "error": self.load_error}
        m = self.meta
        return {
            "available": True,
            "name": "Credit Card Fraud Detection",
            "algorithm": "XGBoost (scale_pos_weight for extreme imbalance)",
            "dataset": "Kaggle Credit Card Fraud (ULB) — anonymised PCA features",
            "n_transactions": m.get("n_transactions"),
            "n_fraud": m.get("n_fraud"),
            "fraud_rate": m.get("fraud_rate"),
            "imbalance_ratio": m.get("imbalance_ratio"),
            "roc_auc": m.get("roc_auc"),
            "pr_auc": m.get("pr_auc"),
            "default_threshold": DEFAULT_THRESHOLD,
            "thresholds": m.get("thresholds", []),
            "top_features": m.get("top_features", []),
        }


fraud_service = FraudService()
