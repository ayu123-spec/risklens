# Fraud Detection (Phase 5)

A credit-card fraud detection model on the Kaggle "Credit Card Fraud Detection"
dataset (mlg-ulb/creditcardfraud) — 284,807 real transactions, only **0.173% fraud**.

## The challenge: extreme imbalance
99.83% of transactions are legitimate. A naive model predicting "never fraud"
would be 99.83% "accurate" while catching ZERO fraud. Beating that is the whole
task. We use XGBoost with `scale_pos_weight` (~578:1) to weight fraud heavily.

## Tuned for high recall (catching fraud)
A missed fraud costs the bank the full transaction; a false alarm costs only a
"was this you?" check. So we prioritize recall and expose a threshold table to
choose the operating point.

## Honest results (held-out test set)
- **ROC-AUC: 0.980**
- **PR-AUC: 0.874** — the metric that matters for extreme imbalance.
- At a tuned threshold, **catches ~89% of fraud** (87 of 98) — a strong operational
  result. The recall/false-alarm tradeoff is tunable to the bank's risk appetite.

## Feature engineering
V1–V28 are already PCA-anonymized by the data provider. We add: `Amount_log`
(fraud amounts are skewed — this made the top predictors), scaled Amount/Time,
and hour-of-day. Top fraud predictors: V14, V4, V12, Amount_log.

## How to run
1. Download `creditcard.csv` from kaggle.com/datasets/mlg-ulb/creditcardfraud
2. `pip install xgboost scikit-learn pandas`
3. `python train_fraud.py path/to/creditcard.csv`

## Note
Standalone model, separate from the live credit-risk app. Demonstrates handling
extreme imbalance and the recall/precision tradeoff central to fraud detection.
