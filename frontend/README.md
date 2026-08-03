# RiskLens Frontend (Multi-Page Premium)

A three-page React frontend in the electric-blue-on-black premium aesthetic.

## Pages
- **Assess** (/) — the credit assessment form + animated gauge, factor chart, probability split.
- **Analytics** (/analytics) — KPI tiles + risk-distribution doughnut, grade bar chart,
  volume-over-time line chart. Driven by the /api/analytics/* endpoints.
- **History** (/history) — table of past assessments with grade, category, and workflow status.

## Stack
React + Vite + React Router + Chart.js. Shared design system in styles.css,
shared chart theming in chartTheme.js, central API helper in api.js.

## Run
```
npm install
npm run dev
```
Needs the backend running on :8000 (dev proxy is configured in vite.config.js).

## Deploy
Set VITE_API_URL to your backend URL. Build: `npm run build`, output in dist/.

## Structure
- src/App.jsx — routing + nav
- src/pages/ — AssessPage, AnalyticsPage, HistoryPage
- src/components/RiskDashboard.jsx — the assessment result view
- src/api.js, src/chartTheme.js, src/useCountUp.js — shared helpers
