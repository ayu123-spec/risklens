"""
train_real.py
-------------
Train the credit-risk model on the REAL 'Give Me Some Credit' data, using the
cleaning + feature engineering in clean_features.py, and handling the ~7% class
imbalance with XGBoost's scale_pos_weight. Saves a calibrated model + schema.

USAGE:
    python train_real.py path/to/cs-training.csv

Prints honest metrics (ROC-AUC, PR-AUC, confusion matrix, recall on defaulters)
so you can see how it really performs -- not vanity accuracy.
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             roc_auc_score)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from clean_features import clean_and_engineer, TARGET


def main(csv_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} rows")

    df = clean_and_engineer(df)
    X = df.drop(columns=[TARGET])
    y = df[TARGET]
    feature_names = list(X.columns)

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    imbalance_ratio = (y == 0).sum() / (y == 1).sum()
    print(f"Class imbalance (neg/pos): {imbalance_ratio:.1f}  -> scale_pos_weight")

    xgb = XGBClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.1,
        scale_pos_weight=imbalance_ratio,
        eval_metric="logloss", random_state=42, n_jobs=-1,
    )
    xgb.fit(Xtr, ytr)

    model = CalibratedClassifierCV(xgb, method="isotonic", cv=3)
    model.fit(Xtr, ytr)

    # Honest evaluation
    proba = model.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)
    ap = average_precision_score(yte, proba)
    preds = (proba >= 0.5).astype(int)
    cm = confusion_matrix(yte, preds)
    recall = cm[1, 1] / (cm[1, 0] + cm[1, 1])

    print("\n" + "=" * 50)
    print("HONEST METRICS (held-out real test set)")
    print("=" * 50)
    print(f"ROC-AUC: {auc:.3f}")
    print(f"PR-AUC:  {ap:.3f}  (key metric for imbalanced data)")
    print(f"Recall on defaulters: {recall*100:.0f}% "
          f"({cm[1,1]} of {cm[1,0]+cm[1,1]} caught)")
    print(f"Confusion matrix:\n{cm}")

    # Save in the same format the app uses (model + schema)
    here = Path(__file__).resolve().parent
    joblib.dump(model, here / "model_real.joblib")
    schema = {
        "numeric": feature_names,   # all engineered features are numeric here
        "categorical": [],
        "target": TARGET,
        "auc": round(float(auc), 3),
    }
    joblib.dump(schema, here / "schema_real.joblib")
    print(f"\nSaved model_real.joblib + schema_real.joblib")
    print(f"Features model expects ({len(feature_names)}): {feature_names}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python train_real.py path/to/cs-training.csv")
        sys.exit(1)
    main(sys.argv[1])
