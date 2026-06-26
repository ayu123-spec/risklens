"""
train.py
--------
The core of Phase 1. This script:

  1. Loads the data
  2. Splits it into train / test (so we measure performance on UNSEEN data)
  3. Builds a preprocessing + model pipeline
  4. Trains TWO models (Logistic Regression and XGBoost) and compares them
  5. Evaluates them honestly with metrics that matter for IMBALANCED data
  6. Calibrates probabilities (so "30% risk" really means ~30%)
  7. Computes SHAP values for explainability
  8. Saves the winning model to disk for the API to use

Run it with:  python3 train.py
"""

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    roc_auc_score, average_precision_score,
    classification_report, confusion_matrix,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

# Columns the model will learn from, split by type because they need
# different preprocessing.
NUMERIC = [
    "age", "income", "employment_length", "credit_score", "existing_loans",
    "num_delinquencies", "credit_history_length", "loan_amount",
    "loan_tenure", "interest_rate", "debt_to_income",
]
CATEGORICAL = ["loan_purpose"]
TARGET = "defaulted"


def build_preprocessor() -> ColumnTransformer:
    """
    Numeric features get scaled (mean 0, std 1) so no single large-magnitude
    feature (like income) dominates. Categorical features get one-hot encoded
    (turned into 0/1 columns) because models need numbers, not text.
    """
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])


def evaluate(name, model, X_test, y_test):
    """
    Print the metrics that actually matter when classes are imbalanced.
    Plain accuracy is misleading here: a model that predicts "never defaults"
    would be 92% accurate on our 8% data while being completely useless.
    """
    proba = model.predict_proba(X_test)[:, 1]   # P(default) for each applicant
    preds = (proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, proba)           # ranking quality, 0.5=random, 1.0=perfect
    ap = average_precision_score(y_test, proba)  # precision-recall, better for imbalance

    print(f"\n=== {name} ===")
    print(f"ROC-AUC: {auc:.3f}   PR-AUC: {ap:.3f}")
    print("Confusion matrix [ [TN FP] [FN TP] ]:")
    print(confusion_matrix(y_test, preds))
    print(classification_report(y_test, preds, digits=3))
    return auc


def main():
    from pathlib import Path
    here = Path(__file__).resolve().parent
    df = pd.read_csv(here / "loans.csv")
    X = df[NUMERIC + CATEGORICAL]
    y = df[TARGET]

    # stratify=y keeps the same 8% default rate in both train and test sets.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    results = {}

    # --- Model 1: Logistic Regression (simple, fast, interpretable baseline) ---
    # class_weight="balanced" tells it to care more about the rare default cases.
    logit = Pipeline([
        ("prep", build_preprocessor()),
        ("clf", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    logit.fit(X_train, y_train)
    results["logistic"] = (logit, evaluate("Logistic Regression", logit, X_test, y_test))

    # --- Model 2: XGBoost (gradient-boosted trees, usually the strongest) ---
    # scale_pos_weight handles imbalance: ratio of negatives to positives.
    scale = (y_train == 0).sum() / (y_train == 1).sum()
    xgb = Pipeline([
        ("prep", build_preprocessor()),
        ("clf", XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9,
            scale_pos_weight=scale, eval_metric="logloss",
            random_state=42,
        )),
    ])
    xgb.fit(X_train, y_train)
    results["xgboost"] = (xgb, evaluate("XGBoost", xgb, X_test, y_test))

    # --- Pick the winner by ROC-AUC ---
    best_name = max(results, key=lambda k: results[k][1])
    best_model = results[best_name][0]
    print(f"\n>>> Best model: {best_name} (AUC={results[best_name][1]:.3f})")

    # --- Calibrate the winner ---
    # Tree models often output over-confident probabilities. Calibration makes
    # the numbers trustworthy, which matters when you show "73% risk" to a banker.
    calibrated = CalibratedClassifierCV(best_model, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train)
    print("Calibrated probabilities ready.")

    # --- Save everything the API needs ---
    joblib.dump(calibrated, here / "model.joblib")
    joblib.dump({"numeric": NUMERIC, "categorical": CATEGORICAL}, here / "schema.joblib")
    print("Saved model.joblib and schema.joblib")

    # --- SHAP explainability on the raw (uncalibrated) tree model ---
    # SHAP explains WHY the model made each prediction. We only run it for the
    # tree model since TreeExplainer is fast and exact for XGBoost.
    if best_name == "xgboost":
        try:
            import shap
            prep = best_model.named_steps["prep"]
            clf = best_model.named_steps["clf"]
            X_test_enc = prep.transform(X_test)
            feat_names = prep.get_feature_names_out()
            explainer = shap.TreeExplainer(clf)
            shap_vals = explainer.shap_values(X_test_enc)
            mean_abs = np.abs(shap_vals).mean(axis=0)
            top = sorted(zip(feat_names, mean_abs), key=lambda t: -t[1])[:8]
            print("\nTop global drivers of default risk (by mean |SHAP|):")
            for f, v in top:
                print(f"  {f:35s} {v:.4f}")
        except Exception as e:
            print(f"(SHAP step skipped: {e})")


if __name__ == "__main__":
    main()
