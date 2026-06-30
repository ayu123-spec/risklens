# Dockerfile — builds the RiskLens backend for deployment (e.g. on Render).
#
# It installs Python deps, trains the model at build time (so the image ships
# with a ready model), and starts the API. Render/any container host runs this.

FROM python:3.12-slim

# System deps some ML libraries (xgboost) need at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (better build caching).
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy the ML code and backend code.
COPY ml ./ml
COPY backend ./backend

# Train the model at build time so the image contains model.joblib + schema.joblib.
# (On a fresh clone the artifacts are gitignored, so we generate them here.)
RUN cd ml && python credit_risk/generate_data.py && python credit_risk/train.py

# Render provides the port via $PORT; default to 8000 locally.
ENV PORT=8000
EXPOSE 8000

# Start the API. --host 0.0.0.0 so it's reachable from outside the container.
CMD ["sh", "-c", "cd backend && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
