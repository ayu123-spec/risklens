"""
main.py
-------
THE APP ENTRYPOINT. Run it with:

  cd backend
  uvicorn app.main:app --reload

Then open http://127.0.0.1:8000/docs in your browser for the interactive API.

What this file does:
  - creates the FastAPI app,
  - enables CORS so your React frontend (Phase 3) can call it from the browser,
  - loads the ML model once when the app starts up (lifespan),
  - mounts all the routes under /api.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.training_routes import router as training_router
from app.services.credit_service import credit_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- runs ONCE on startup ---
    # Load the model here so the first request isn't slow and we fail fast if
    # the model file is missing.
    credit_service.load()
    print("Credit risk model loaded. API ready.")
    yield
    # --- runs ONCE on shutdown (nothing to clean up yet) ---


app = FastAPI(
    title="RiskLens — Banking Risk Intelligence API",
    description="Credit risk scoring API. Phase 2 of the RiskLens platform.",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS: browsers block a web page from calling an API on a different origin
# unless the API says it's allowed. In development we allow localhost; in
# production, set the FRONTEND_URL environment variable to your deployed frontend
# (e.g. https://risklens.vercel.app) and it will be allowed automatically.
_dev_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_frontend_url = os.getenv("FRONTEND_URL", "").strip()
_allowed_origins = _dev_origins + ([_frontend_url] if _frontend_url else [])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# All endpoints live under /api, e.g. POST /api/credit-risk
app.include_router(router, prefix="/api")
app.include_router(training_router, prefix="/api")


@app.get("/", tags=["system"])
def root():
    """A friendly landing response so hitting the base URL isn't a 404."""
    return {"service": "RiskLens API", "docs": "/docs", "health": "/api/health"}
