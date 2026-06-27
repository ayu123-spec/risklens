"""
train_custom.py
---------------
Train the credit-risk model on ANY CSV you provide — your own data, a Kaggle
dataset, anything — instead of being locked to the built-in synthetic data.

WHAT IT DOES
  1. Loads your CSV.
  2. Validates it (does the target column exist? are there rows? etc.) and
     fails with a CLEAR message if something is wrong, before wasting time.
  3. Auto-detects which columns are numeric vs categorical so you don't have
     to configure each one by hand.
  4. Trains Logistic Regression + XGBoost, compares them, calibrates the winner.
  5. Saves model.joblib + schema.joblib in the SAME format the API already
     uses, so the rest of the app keeps working.

USAGE
  # simplest — target column is named "defaulted" (or "target"/"label"/"y"):
  python train_custom.py path/to/your_data.csv

  # if your target column has a different name, say so:
  python train_custom.py path/to/your_data.csv --target is_default

  # drop columns that shouldn't be features (e.g. an ID column):
  python train_custom.py data.csv --target is_default --drop customer_id,application_date

IMPORTANT — if your columns differ from the original 12, the model will train
fine, but the API and frontend form expect specific fields. After training,
run the printed "fields this model expects" list and update the frontend form
to match. The API reads the schema dynamically, so it adapts automatically.
"""

import argparse
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, average_precision_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from xgboost import XGBClassifier

# Common names people use for the target column. We auto-detect these.
COMMON_TARGET_NAMES = ["defaulted", "default", "target", "label", "y", "is_default", "bad"]


class DataValidationError(Exception):
    """Raised when the input data can't be used. Carries a human-friendly message."""
    pass


def find_target_column(df: pd.DataFrame, explicit: str | None) -> str:
    """Figure out which column is the thing to predict."""
    if explicit:
        if explicit not in df.columns:
            raise DataValidationError(
                f"You specified target column '{explicit}', but the CSV has no such column.\n"
                f"Available columns: {list(df.columns)}"
            )
        return explicit
    # Try the common names.
    for name in COMMON_TARGET_NAMES:
        if name in df.columns:
            return name
    raise DataValidationError(
        "Could not find a target column automatically.\n"
        f"Looked for: {COMMON_TARGET_NAMES}\n"
        f"Your columns: {list(df.columns)}\n"
        "Re-run with --target YOUR_COLUMN_NAME to tell me which column to predict."
    )


def validate(df: pd.DataFrame, target: str):
    """Check the data is usable; raise a clear error if not."""
    if len(df) < 50:
        raise DataValidationError(
            f"Only {len(df)} rows found. Need at least 50 (realistically hundreds+) to train a meaningful model."
        )
    y = df[target]
    n_classes = y.nunique(dropna=True)
    if n_classes < 2:
        raise DataValidationError(
            f"Target column '{target}' has only {n_classes} unique value(s). "
            "It must have at least 2 (e.g. 0 = repaid, 1 = defaulted)."
        )
    if n_classes > 10:
        raise DataValidationError(
            f"Target column '{target}' has {n_classes} unique values, which looks like a "
            "regression target or an ID, not a default/no-default label. "
            "This pipeline does binary classification (default vs not)."
        )
    # Warn (not fail) on heavy missingness.
    null_frac = df.isnull().mean()
    bad = null_frac[null_frac > 0.5]
    if len(bad) > 0:
        print(f"  WARNING: these columns are >50% empty and may hurt the model: {list(bad.index)}")


def detect_column_types(df: pd.DataFrame, feature_cols: list) -> tuple[list, list]:
    """
    Decide which features are numeric vs categorical.
    Rule: if pandas reads it as a number AND it has more than ~12 distinct
    values, treat it as numeric. Otherwise treat it as categorical (text, or
    a small set of codes like 1/2/3 for a category).
    """
    numeric, categorical = [], []
    for col in feature_cols:
        is_numeric_dtype = pd.api.types.is_numeric_dtype(df[col])
        n_unique = df[col].nunique(dropna=True)
        if is_numeric_dtype and n_unique > 12:
            numeric.append(col)
        else:
            categorical.append(col)
    return numeric, categorical


def main():
    ap = argparse.ArgumentParser(description="Train the credit-risk model on any CSV.")
    ap.add_argument("csv", help="Path to your CSV file")
    ap.add_argument("--target", default=None, help="Name of the column to predict")
    ap.add_argument("--drop", default="", help="Comma-separated columns to exclude (e.g. IDs)")
    ap.add_argument("--out", default=None, help="Where to save model files (default: next to this script)")
    args = ap.parse_args()

    out_dir = Path(args.out).resolve() if args.out else Path(__file__).resolve().parent

    # --- Load ---
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"ERROR: file not found: {csv_path}")
        sys.exit(1)
    print(f"Loading {csv_path} ...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"ERROR: could not read CSV: {e}")
        sys.exit(1)
    print(f"  {len(df):,} rows, {len(df.columns)} columns")

    # --- Figure out target + features ---
    try:
        target = find_target_column(df, args.target)
        print(f"  Target column: '{target}'")
        drop_cols = [c.strip() for c in args.drop.split(",") if c.strip()]
        feature_cols = [c for c in df.columns if c != target and c not in drop_cols]
        if drop_cols:
            print(f"  Dropping (not used as features): {drop_cols}")
        if not feature_cols:
            raise DataValidationError("No feature columns left after removing target and dropped columns.")

        validate(df, target)
        numeric, categorical = detect_column_types(df, feature_cols)
    except DataValidationError as e:
        print("\n--- CANNOT TRAIN ---")
        print(e)
        sys.exit(1)

    print(f"  Numeric features ({len(numeric)}): {numeric}")
    print(f"  Categorical features ({len(categorical)}): {categorical}")

    # Drop rows missing the target; fill feature gaps simply.
    df = df.dropna(subset=[target]).copy()
    # Coerce target to 0/1 if it's not already.
    y = df[target]
    if y.dtype == object or sorted(y.dropna().unique().tolist()) not in ([0, 1], [0], [1]):
        # Map the two most common classes to 0/1 (lower count -> 1 = the rare "bad" class).
        counts = y.value_counts()
        positive_class = counts.index[-1]  # rarer class treated as the event (default)
        y = (y == positive_class).astype(int)
        print(f"  Mapped target: '{positive_class}' -> 1 (default), others -> 0")
    X = df[feature_cols]

    # --- Preprocessing: scale numbers, one-hot categories, impute missing ---
    from sklearn.impute import SimpleImputer
    pre = ColumnTransformer([
        ("num", Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
        ]), numeric),
        ("cat", Pipeline([
            ("impute", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]), categorical),
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    def evaluate(name, model):
        proba = model.predict_proba(X_test)[:, 1]
        auc = roc_auc_score(y_test, proba)
        ap_ = average_precision_score(y_test, proba)
        print(f"\n=== {name} ===  ROC-AUC: {auc:.3f}  PR-AUC: {ap_:.3f}")
        print(classification_report(y_test, (proba >= 0.5).astype(int), digits=3))
        return auc

    results = {}
    print("\nTraining Logistic Regression ...")
    logit = Pipeline([("prep", pre), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))])
    logit.fit(X_train, y_train)
    results["logistic"] = (logit, evaluate("Logistic Regression", logit))

    print("Training XGBoost ...")
    scale = max((y_train == 0).sum() / max((y_train == 1).sum(), 1), 1)
    xgb = Pipeline([("prep", pre), ("clf", XGBClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.9,
        colsample_bytree=0.9, scale_pos_weight=scale, eval_metric="logloss", random_state=42))])
    xgb.fit(X_train, y_train)
    results["xgboost"] = (xgb, evaluate("XGBoost", xgb))

    best_name = max(results, key=lambda k: results[k][1])
    best = results[best_name][0]
    print(f"\n>>> Best model: {best_name} (AUC={results[best_name][1]:.3f})")

    print("Calibrating ...")
    calibrated = CalibratedClassifierCV(best, method="isotonic", cv=3)
    calibrated.fit(X_train, y_train)

    # --- Save in the format the API/engine expect ---
    joblib.dump(calibrated, out_dir / "model.joblib")
    joblib.dump({"numeric": numeric, "categorical": categorical}, out_dir / "schema.joblib")
    print(f"\nSaved model.joblib and schema.joblib to {out_dir}")

    # --- Tell the user what the API/form now expect ---
    print("\n" + "=" * 60)
    print("FIELDS THIS MODEL EXPECTS (update your frontend form to match):")
    print("=" * 60)
    for c in numeric:
        print(f"  {c}  (number)")
    for c in categorical:
        opts = sorted(df[c].dropna().astype(str).unique().tolist())[:8]
        print(f"  {c}  (category: {opts}{'...' if len(opts) == 8 else ''})")
    print("=" * 60)
    if set(numeric + categorical) != {
        "age","income","employment_length","credit_score","existing_loans",
        "num_delinquencies","credit_history_length","loan_amount","loan_tenure",
        "interest_rate","debt_to_income","loan_purpose"}:
        print("NOTE: these columns differ from the original 12. The API will adapt\n"
              "automatically (it reads the schema), but the React form is hardcoded —\n"
              "update frontend/src/App.jsx's field list to match the above.")


if __name__ == "__main__":
    main()
