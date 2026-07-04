"""
train_fraud.py
--------------
Fraud detection on the Kaggle 'Credit Card Fraud Detection' dataset
(mlg-ulb/creditcardfraud). 284,807 transactions, only 0.173% fraud — an
EXTREME class imbalance, which is the central challenge.

Design choices:
  - Features V1..V28 are already PCA-anonymized + scaled by the data provider.
  - We add engineered features: log(Amount), scaled Amount/Time, hour-of-day.
  - XGBoost with scale_pos_weight (~578:1) to handle the imbalance.
  - Tuned for HIGH RECALL: a missed fraud costs the full amount, while a false
    alarm costs only a "was this you?" check. So we accept more false positives
    to catch more fraud, and expose a threshold table to pick the operating point.

USAGE:
    python train_fraud.py path/to/creditcard.csv
"""
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, confusion_matrix,
                             precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


def engineer(df: pd.DataFrame, scaler=None, fit=False):
    df = df.copy()
    df["Amount_log"] = np.log1p(df["Amount"])
    df["Hour"] = (df["Time"] / 3600) % 24
    cols = ["Amount", "Time"]
    if fit:
        scaler = StandardScaler().fit(df[cols])
    df[["Amount_scaled", "Time_scaled"]] = scaler.transform(df[cols])
    return df, scaler


def main(csv_path):
    df = pd.read_csv(csv_path)
    print(f"Loaded {len(df):,} transactions, {int(df['Class'].sum())} fraud "
          f"({df['Class'].mean()*100:.3f}%)")

    df, scaler = engineer(df, fit=True)
    features = ([c for c in df.columns if c.startswith("V")]
                + ["Amount_log", "Amount_scaled", "Time_scaled", "Hour"])
    X, y = df[features], df["Class"]

    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42)

    ratio = (y == 0).sum() / (y == 1).sum()
    print(f"Imbalance: {ratio:.0f}:1  -> scale_pos_weight")

    model = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.1,
        scale_pos_weight=ratio, eval_metric="aucpr",
        random_state=42, n_jobs=-1)
    model.fit(Xtr, ytr)

    proba = model.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)
    ap = average_precision_score(yte, proba)
    n_fraud = int(yte.sum())

    print("\n" + "=" * 62)
    print("HONEST METRICS (held-out test set)")
    print("=" * 62)
    print(f"ROC-AUC: {auc:.3f}")
    print(f"PR-AUC:  {ap:.3f}  (key metric for extreme imbalance)")
    print(f"\nThreshold tuning (recall vs false alarms):")
    print(f"{'thresh':>8} {'recall':>8} {'precision':>10} {'false_alarms':>13} {'caught':>10}")
    for t in [0.5, 0.3, 0.1, 0.05, 0.01]:
        preds = (proba >= t).astype(int)
        cm = confusion_matrix(yte, preds)
        print(f"{t:>8} {recall_score(yte,preds)*100:>7.0f}% "
              f"{precision_score(yte,preds,zero_division=0)*100:>9.0f}% "
              f"{cm[0,1]:>13} {cm[1,1]:>6}/{n_fraud}")

    here = Path(__file__).resolve().parent
    joblib.dump(model, here / "fraud_model.joblib")
    joblib.dump({"features": features, "scaler": scaler,
                 "roc_auc": round(float(auc), 3),
                 "pr_auc": round(float(ap), 3)}, here / "fraud_schema.joblib")
    print(f"\nSaved fraud_model.joblib + fraud_schema.joblib")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python train_fraud.py path/to/creditcard.csv")
        sys.exit(1)
    main(sys.argv[1])
