# Training on Your Own Data

The model is no longer locked to the built-in synthetic data. Feed it any CSV.

## Two ways to retrain

### 1. Command line
```bash
cd ml
# target column auto-detected if named defaulted/target/label/y/is_default/bad:
python credit_risk/train_custom.py path/to/your.csv

# otherwise name it, and drop any ID columns:
python credit_risk/train_custom.py your.csv --target is_default --drop customer_id
```

### 2. API upload
With the backend running:
```bash
curl -X POST http://127.0.0.1:8000/api/train \
  -F "file=@your.csv" -F "target=is_default" -F "drop=customer_id"
```
Or use the interactive docs at http://127.0.0.1:8000/docs → POST /api/train.

Check what fields the current model expects:
```bash
curl http://127.0.0.1:8000/api/schema
```

## What it does automatically
- Finds the target column (or you name it with --target)
- Detects numeric vs categorical columns
- Imputes missing values, scales numbers, one-hot encodes categories
- Trains Logistic Regression + XGBoost, picks the better one, calibrates it
- Saves model.joblib + schema.joblib (same format the API uses)

## The one catch: different columns
If your CSV has different columns than the original 12, training works and the
API adapts (it reads schema.joblib). BUT the React form is hardcoded to the
original fields. After training on new columns, update the field list in
`frontend/src/App.jsx` to match what `/api/schema` reports.

## Where to get real data
Kaggle: "Give Me Some Credit" or "Home Credit Default Risk". Download the CSV,
point train_custom.py at it, name the target column, and you have a model
trained on real lending data instead of synthetic.
