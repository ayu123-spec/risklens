"""
main.py
-------
THE APP ENTRYPOINT. Run it with:
  cd backend
  uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs in your browser for the interactive API.

What this file does:
  - creates the FastAPI app,
  - enables CORS so the React frontend can call it from the browser,
  - loads the credit-risk model and the fraud-detection model at startup,
  - initialises the database and seeds reference data,
  - mounts all the routes under /api.
"""
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# The database/ package and db_routes.py live at the REPO ROOT, three levels
# above this file. Add the repo root to sys.path so they can be imported.
#   this file: <repo>/backend/app/main.py   ->  dirname x3  ->  <repo>
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app.api.routes import router
from app.api.training_routes import router as training_router
from app.api.fraud_routes import router as fraud_router
from app.services.credit_service import credit_service
from app.services.fraud_service import fraud_service

from database.db import init_db, SessionLocal
import database.repository as repo
from db_routes import router as db_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- runs ONCE on startup ---
    # Load models here so the first request isn't slow and we fail fast if a
    # model file is missing.
    credit_service.load()
    print("Credit risk model loaded. API ready.")

    # Fraud model. It loads defensively -- if the artifacts are missing, the
    # fraud endpoints report unavailable but credit scoring keeps working.
    fraud_service.load()
    print("Fraud model loaded." if fraud_service.is_loaded
          else "Fraud model unavailable.")

    # Create tables if absent and seed reference data (loan products, model
    # version). Wrapped so a database problem never stops the API from serving
    # scores -- persistence degrades, scoring keeps working.
    try:
        init_db()
        _seed = SessionLocal()
        repo.seed_reference_data(_seed)
        _seed.close()
        print("Database initialized and seeded.")
    except Exception as exc:
        print(f"WARNING: database init failed ({exc}). Scoring still works; "
              f"history/analytics will be unavailable.")

    yield
    # --- runs ONCE on shutdown (nothing to clean up yet) ---


app = FastAPI(
    title="RiskLens — Banking Risk Intelligence API",
    description="Credit risk scoring and fraud detection, with persistence, "
                "workflow and analytics.",
    version="0.4.0",
    lifespan=lifespan,
)

# CORS: browsers block a web page from calling an API on a different origin
# unless the API says it's allowed. In development we allow localhost; in
# production, set the FRONTEND_URL environment variable to your deployed frontend.
#
# Vercel gives an app several URLs: a stable one (risklens-vert.vercel.app) AND a
# unique one per deployment (risklens-abc123-user.vercel.app). To avoid CORS
# breaking whenever you view a preview/deployment URL, we also allow any
# *.vercel.app origin via a regex. FRONTEND_URL still pins your main domain.
_dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
_allowed_origins = _dev_origins + ([_frontend_url] if _frontend_url else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
)

# All endpoints live under /api, e.g. POST /api/credit-risk
app.include_router(router, prefix="/api")
app.include_router(training_router, prefix="/api")
# Database-backed endpoints: /api/assessments, /api/analytics/*, review & decide
app.include_router(db_router, prefix="/api")
# Fraud detection: /api/fraud/model-info, /api/fraud/samples, /api/fraud/score
app.include_router(fraud_router, prefix="/api")


@app.get("/", tags=["system"])
def root():
    """A friendly landing response so hitting the base URL isn't a 404."""
    return {
        "service": "RiskLens API",
        "docs": "/docs",
        "health": "/api/health",
        "capabilities": ["credit-risk", "fraud-detection"],
    }
