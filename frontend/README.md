# Frontend — RiskLens (Phase 3)

A React app: an applicant form that calls the Phase 2 `/credit-risk` API and
displays the risk score, category, approval, and reasons.

## Run it (needs the backend running too!)

You need **TWO terminals**.

**Terminal 1 — backend** (from repo root):
```bash
cd backend
uvicorn app.main:app --reload
```

**Terminal 2 — frontend** (from repo root):
```bash
cd frontend
npm install      # first time only
npm run dev
```

Then open **http://localhost:5173** in your browser. The form is pre-filled —
just click **Assess Risk**.

## How it talks to the backend
`vite.config.js` proxies any `/api/*` request to `http://127.0.0.1:8000`, so the
browser never sees a cross-origin call during development. When you deploy
(Phase 4), you'll point it at your live backend URL instead.

## Structure
```
frontend/
├── index.html              # page shell, loads the app
├── vite.config.js          # dev server + API proxy
├── package.json            # dependencies & scripts
└── src/
    ├── main.jsx            # entry point
    ├── App.jsx             # form + state + API call
    ├── styles.css          # styling
    └── components/
        └── RiskResult.jsx  # score gauge, badges, reasons
```
