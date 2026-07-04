"""
clean_features.py
-----------------
Cleaning + feature engineering for the real 'Give Me Some Credit' dataset
(Kaggle). Tailored to the ACTUAL problems in that data, discovered by inspection:

  - MonthlyIncome ~20% missing        -> median-fill + a "was missing" flag
  - NumberOfDependents ~3% missing    -> fill with 0
  - RevolvingUtilization up to 50,708 -> clip to [0, 1.5] (it's meant to be a ratio)
  - DebtRatio up to 329,664           -> clip at 97.5th percentile
  - age has 0 / under-18 rows         -> set to median age
  - past-due cols use 96/98 as a "not available" sentinel -> treat as missing

Engineered features (this is where real signal is added):
  - TotalPastDue        : sum of the three delinquency buckets (strongest predictor)
  - IncomePerDependent  : financial strain proxy
  - HasRealEstate       : homeownership proxy
  - MonthlyDebtEst      : DebtRatio * MonthlyIncome
  - income_was_missing  : missingness is itself predictive

Reusable: import clean_and_engineer(df) from training or serving code.
"""
import numpy as np
import pandas as pd

PASTDUE_COLS = [
    "NumberOfTime30-59DaysPastDueNotWorse",
    "NumberOfTimes90DaysLate",
    "NumberOfTime60-89DaysPastDueNotWorse",
]
TARGET = "SeriousDlqin2yrs"


def clean_and_engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Take raw GMSC data, return a cleaned + feature-engineered copy."""
    df = df.copy()
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # --- Cleaning ---
    # Past-due sentinels 96/98 mean "not available", not real counts.
    for c in PASTDUE_COLS:
        df[c] = df[c].replace([96, 98], np.nan)
        df[c] = df[c].fillna(df[c].median())

    # Utilization is a ratio; kill absurd outliers.
    df["RevolvingUtilizationOfUnsecuredLines"] = (
        df["RevolvingUtilizationOfUnsecuredLines"].clip(0, 1.5)
    )

    # DebtRatio: clip the extreme tail.
    dr_cap = df["DebtRatio"].quantile(0.975)
    df["DebtRatio"] = df["DebtRatio"].clip(0, dr_cap)

    # Fix impossible ages.
    med_age = int(df.loc[df["age"] >= 18, "age"].median())
    df.loc[df["age"] < 18, "age"] = med_age

    # Income: flag missingness, then fill.
    df["income_was_missing"] = df["MonthlyIncome"].isnull().astype(int)
    df["MonthlyIncome"] = df["MonthlyIncome"].fillna(df["MonthlyIncome"].median())

    # Dependents: fill with 0.
    df["NumberOfDependents"] = df["NumberOfDependents"].fillna(0)

    # --- Feature engineering ---
    df["TotalPastDue"] = df[PASTDUE_COLS].sum(axis=1)
    df["IncomePerDependent"] = df["MonthlyIncome"] / (df["NumberOfDependents"] + 1)
    df["HasRealEstate"] = (df["NumberRealEstateLoansOrLines"] > 0).astype(int)
    df["MonthlyDebtEst"] = df["DebtRatio"] * df["MonthlyIncome"]

    return df
