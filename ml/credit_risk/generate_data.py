"""
generate_data.py
----------------
Creates a realistic synthetic loan dataset so you can run the whole pipeline
today without hunting for data. Later you can swap this for a real dataset
(e.g. the "Give Me Some Credit" or "Home Credit Default Risk" sets on Kaggle)
and the rest of the code barely changes.

WHY SYNTHETIC FIRST: it lets you learn the mechanics end-to-end with data you
fully understand. We deliberately bake in *realistic relationships* (e.g. high
debt-to-income raises default risk) so the model has something real to learn.
"""

import numpy as np
import pandas as pd

# A fixed seed means you get the same data every run -> reproducible experiments.
RNG = np.random.default_rng(42)
N = 10_000  # number of loan applicants


def generate() -> pd.DataFrame:
    # --- Customer demographic features ---
    age = RNG.integers(21, 70, N)
    # Income is right-skewed in real life, so we use a lognormal distribution.
    income = np.round(RNG.lognormal(mean=11.2, sigma=0.5, size=N)).astype(int)
    employment_length = np.clip(RNG.normal(8, 5, N), 0, 40).round(1)

    # --- Financial / credit-bureau features ---
    credit_score = np.clip(RNG.normal(680, 80, N), 300, 850).astype(int)
    existing_loans = RNG.poisson(1.2, N)
    num_delinquencies = RNG.poisson(0.4, N)
    # Credit history length: related to age (you can't have 30 years of credit
    # at 25), but with real independent variation — some people open credit
    # early, others late. This avoids near-perfect correlation with age, which
    # would otherwise make the two features statistically indistinguishable.
    credit_history_length = np.clip(
        age - RNG.integers(18, 25, N) - RNG.exponential(5, N), 0, None
    ).round(0)

    # --- Loan-specific features ---
    loan_amount = np.round(RNG.lognormal(mean=11.5, sigma=0.6, size=N)).astype(int)
    loan_tenure = RNG.choice([12, 24, 36, 48, 60], N, p=[0.1, 0.2, 0.3, 0.25, 0.15])
    interest_rate = np.clip(RNG.normal(12, 3, N), 6, 28).round(2)
    loan_purpose = RNG.choice(
        ["home", "auto", "personal", "education", "business"],
        N, p=[0.3, 0.25, 0.25, 0.1, 0.1],
    )

    # Debt-to-income: a key risk signal. Total monthly debt payments vs income.
    # We model the new loan's EMI plus a modest share of income going to
    # existing obligations, so DTI lands in a realistic ~0.1-0.6 band.
    new_loan_emi = loan_amount / loan_tenure
    existing_obligation = existing_loans * RNG.normal(3000, 1000, N).clip(0)
    monthly_obligation = new_loan_emi + existing_obligation
    monthly_income = income / 12
    dti = np.clip(monthly_obligation / monthly_income, 0.02, 1.2).round(3)

    df = pd.DataFrame({
        "age": age,
        "income": income,
        "employment_length": employment_length,
        "credit_score": credit_score,
        "existing_loans": existing_loans,
        "num_delinquencies": num_delinquencies,
        "credit_history_length": credit_history_length,
        "loan_amount": loan_amount,
        "loan_tenure": loan_tenure,
        "interest_rate": interest_rate,
        "debt_to_income": dti,
        "loan_purpose": loan_purpose,
    })

    # --- Create the TARGET (defaulted: 1 = yes, 0 = no) ---
    # Every feature here has a REAL, intentional effect in a sensible direction,
    # so the model learns relationships that match real-world credit intuition.
    # (A subtle earlier version left age and loan-size as "spectator" features
    # with no direct signal, which let the model learn meaningless noise. Fixed.)

    # Loan burden: the loan relative to income matters more than raw amount.
    # A 500k loan is heavy on 35k income, trivial on 5M. This is the honest way
    # to let loan_amount raise risk without entangling it with DTI.
    loan_to_income = (df.loan_amount / df.income).clip(0, 15)

    # Direct income effect: lower income -> higher risk, ACROSS THE WHOLE RANGE,
    # not just via the loan-to-income ratio. We use log(income) so the effect is
    # smooth and monotonic from very low to very high earners (each doubling of
    # income lowers risk by a steady amount, which matches reality). This is the
    # fix for income previously having only a weak, saturating, indirect voice.
    # Reference point: ~80k income is "neutral".
    income_effect = -0.65 * (np.log(df.income.clip(lower=1)) - np.log(80000))

    # Age effect: risk is highest for the very young (thin track record) and
    # eases as applicants get older and more established, leveling off.
    # Negative coefficient = older -> lower risk. Strengthened so the model
    # learns it stably rather than splitting it with credit-history length.
    age_effect = -0.045 * (df.age - 30)

    z = (
        -4.8                                  # baseline: most people repay
        - 0.015 * (df.credit_score - 680)     # higher score -> lower risk
        + 2.4 * (df.debt_to_income - 0.35)    # higher DTI -> higher risk
        + 0.20 * loan_to_income               # bigger loan vs income -> higher risk
        + income_effect                       # lower income -> higher risk (direct)
        + age_effect                          # older -> lower risk
        + 0.55 * df.num_delinquencies         # past delinquencies hurt
        + 0.30 * df.existing_loans            # more existing debt -> higher risk
        + 0.012 * (df.loan_tenure - 36)       # longer tenure -> modestly higher risk
        + 0.05 * (df.interest_rate - 12)      # priced-up loans are riskier
        - 0.03 * df.employment_length         # job stability helps
        + RNG.normal(0, 0.5, N)               # noise: the world isn't perfectly predictable
    )
    prob_default = 1 / (1 + np.exp(-z))        # logistic squashing into 0..1
    df["defaulted"] = (RNG.random(N) < prob_default).astype(int)
    return df


if __name__ == "__main__":
    from pathlib import Path
    here = Path(__file__).resolve().parent
    data = generate()
    data.to_csv(here / "loans.csv", index=False)
    rate = data.defaulted.mean()
    print(f"Wrote loans.csv  rows={len(data):,}  default_rate={rate:.1%}")
    print(data.head())
