RiskLens — AI-Powered Credit Risk Intelligence Platform

An end-to-end credit risk assessment platform that helps evaluate loan applications using machine learning. Given an applicant's financial details, the system predicts the probability of default and provides an explainable lending decision with risk-based recommendations.

🔗 Live Demo
Frontend: https://risklens-vert.vercel.app
Backend API: https://risklens-ri15.onrender.com

Note: The backend is hosted on Render's free tier and may take 30–60 seconds to wake up after inactivity.

Key Features:----
Predicts loan default probability using an XGBoost model.
Generates an AI-powered credit assessment including:
Risk score
Credit grade (AAA–C)
Risk category
Loan approval recommendation
Risk-based interest rate
Maximum eligible loan amount
Explainable predictions with the key factors influencing every decision.
Interactive React dashboard with charts, gauges, and detailed risk insights.
RESTful API built with FastAPI.
Dockerized deployment for easy scalability.


Model Performance:----
Credit Risk Model
Trained on Kaggle's Give Me Some Credit dataset (150K borrowers).
ROC-AUC: 0.868
Includes feature engineering, missing value handling, and outlier treatment.
Fraud Detection Model
Built on the Credit Card Fraud Detection dataset (285K transactions).
PR-AUC: 0.874
Recall: ~89% for fraudulent transactions.
