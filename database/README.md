# Advanced Database Layer (Phase 6)

A bank-grade relational data model for RiskLens, with production engineering
rigor and built-in analytics — not just a flat table of rows.

## Schema (7 tables)
- **users** — analysts/reviewers, with roles (analyst/reviewer/admin).
- **applicants** — people being assessed, as reusable first-class records.
- **loan_products** — products to assess against (home/auto/etc.), each with rate & ceiling.
- **model_versions** — ML governance: which model+version scored each assessment
  (for audit, reproducibility, rollback). One active version at a time.
- **assessments** — links applicant + product + model + analyst, with the result
  and a status workflow (pending → reviewed → decided) + final decision.
- **audit_log** — append-only action trail.

## Advanced engineering
- **Enums** for controlled vocabularies (status, role, decision) — DB-enforced.
- **CheckConstraints** so invalid data can't be inserted (score 0-100, prob 0-1).
- **Indexes** on queried/filtered/sorted columns, incl. composite indexes.
- **Soft-delete** (is_deleted) — records archived, never truly lost.
- **Connection pooling** tuned for web traffic (pool_size, overflow, recycle, pre_ping).
- **Transactions** with commit/rollback via a context manager.
- **Alembic migrations** for versioned schema evolution (see alembic_setup.md).

## Analytics (data → business answers)
- `approval_rate` — overall approval percentage.
- `risk_distribution` / `grade_distribution` — the portfolio's risk shape.
- `assessments_over_time` — daily volume time series.
- `portfolio_exposure` — avg default probability + high-risk count.

## Files
- `models.py` — the schema (SQLAlchemy ORM).
- `db.py` — connection + pooling. Postgres in prod, SQLite locally.
- `repository.py` — writes, workflow transitions, and analytics.
- `test_db.py` — comprehensive end-to-end test (run it: `python test_db.py`).

## Run it (zero setup)
```
pip install sqlalchemy
cd database
python test_db.py     # exercises the whole layer on SQLite
```

## Production (Postgres)
Set `DATABASE_URL` to your Postgres URL — same code, no changes. See the
provisioning guide for Render's free Postgres.
