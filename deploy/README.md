# Deployment Guide — Phase 4

Get RiskLens onto a live public URL: backend on **Render**, frontend on **Vercel**.
Both have free tiers. Order matters: deploy the backend first (you need its URL
for the frontend), then the frontend.

## Prerequisites
- All code pushed to GitHub (Render and Vercel deploy from your repo).
- A Render account (render.com) and a Vercel account (vercel.com) — sign in with GitHub.

---

## Step 1 — Backend on Render

1. Render dashboard → **New** → **Web Service**.
2. Connect your GitHub repo (risklens).
3. Render auto-detects the `Dockerfile` at the repo root. Settings:
   - **Environment:** Docker
   - **Region:** closest to you
   - **Instance type:** Free
4. **Create Web Service.** First build takes ~5-10 min (it installs ML deps and
   trains the model — this is expected).
5. When live, Render gives you a URL like `https://risklens-api.onrender.com`.
   **Copy it** — the frontend needs it.
6. Test it: open `https://YOUR-RENDER-URL/api/health` — you should see
   `{"status":"ok","model_loaded":true}`.

> Free-tier note: Render spins the service down after ~15 min of inactivity, so
> the first request after idle takes ~30-60s to wake. Normal for free tier.

---

## Step 2 — Frontend on Vercel

1. Vercel dashboard → **Add New** → **Project**.
2. Import your GitHub repo.
3. Vercel reads `vercel.json` (builds from `frontend/`). Confirm:
   - **Framework:** Vite
   - **Build command:** `cd frontend && npm install && npm run build`
   - **Output directory:** `frontend/dist`
4. **Environment Variables** — add one:
   - Name: `VITE_API_URL`
   - Value: your Render backend URL from Step 1 (e.g. `https://risklens-api.onrender.com`)
5. **Deploy.** Takes ~2 min.
6. Vercel gives you a URL like `https://risklens.vercel.app`.

---

## Step 3 — Connect them (CORS)

The backend must allow the frontend's origin.

1. Back in Render → your service → **Environment**.
2. Add a variable:
   - Name: `FRONTEND_URL`
   - Value: your Vercel URL from Step 2 (e.g. `https://risklens.vercel.app`)
3. Save — Render redeploys automatically (~2 min).

Now open your Vercel URL, enter a name, run an assessment. It should score live.

---

## Troubleshooting

- **"Can't reach the API"** on the live site → check `VITE_API_URL` is set in
  Vercel and matches the Render URL exactly (https, no trailing slash).
- **CORS error in browser console** → check `FRONTEND_URL` in Render matches your
  Vercel URL exactly.
- **First request hangs ~30s** → free-tier Render waking up. Wait, retry.
- **Backend build fails** → check Render build logs; the training step needs the
  ML deps, which are in `backend/requirements.txt`.

## What's deployed
- Backend: FastAPI + the trained model, served at `/api/*`, Dockerized.
- Frontend: the React dashboard, static build on Vercel's CDN.
