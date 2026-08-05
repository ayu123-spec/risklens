-- ============================================================================
-- bi_views.sql — reporting views for BI tools (Power BI, Tableau, Metabase)
--
-- Run once against the production database:
--     psql "<your DATABASE_URL>" -f bi_views.sql
--
-- Safe to re-run: every object is dropped and recreated.
--
-- WHY VIEWS RATHER THAN POINTING BI AT THE TABLES DIRECTLY
--   The schema is normalised for the application: an assessment stores foreign
--   keys, not names, and enums rather than labels. A BI tool pointed straight
--   at it produces charts full of "3" and "PENDING". These views denormalise
--   and label everything so the tool can chart them without extra joins, and
--   they give a stable contract. Views are read-only, so a misconfigured BI
--   connection cannot write.
--
-- ROBUSTNESS NOTES — each of these was a real failure found in testing:
--   1. loan_amount lives inside a JSON column. One row holding a non-numeric
--      value broke four views with a hard cast error and left the dashboard
--      blank. safe_numeric() returns NULL instead of erroring.
--   2. is_deleted is nullable. Filtering on "= FALSE" silently dropped rows
--      where it was NULL. "IS NOT TRUE" keeps them.
--   3. TO_CHAR(..., 'Day') pads to nine characters, so "Monday   " and
--      "Monday" grouped as different values. Now trimmed, with a sort order.
--   4. The activity view only joined on analyst_id, so reviewers never
--      appeared despite doing the review work.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Helper: cast JSON text to numeric, returning NULL instead of erroring.
-- Pure SQL (not exception-handling plpgsql) so Postgres can inline it.
-- ----------------------------------------------------------------------------
DROP FUNCTION IF EXISTS safe_numeric(text) CASCADE;
CREATE FUNCTION safe_numeric(txt text) RETURNS numeric
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT CASE
        WHEN txt ~ '^\s*-?\d+(\.\d+)?([eE][+-]?\d+)?\s*$' THEN txt::numeric
        ELSE NULL
    END
$$;


-- ----------------------------------------------------------------------------
-- 1. vw_assessments — the main fact table. One row per assessment, fully
--    denormalised. Most dashboards can be built from this view alone.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_assessments CASCADE;
CREATE VIEW vw_assessments AS
SELECT
    a.id                                    AS assessment_id,
    a.created_at                            AS assessed_at,
    a.created_at::date                      AS assessment_date,
    DATE_TRUNC('month', a.created_at)::date AS assessment_month,
    DATE_TRUNC('week',  a.created_at)::date AS assessment_week,
    TRIM(TO_CHAR(a.created_at, 'Day'))      AS day_of_week,
    EXTRACT(ISODOW FROM a.created_at)::int  AS day_of_week_order,
    EXTRACT(HOUR FROM a.created_at)::int    AS hour_of_day,

    a.risk_score,
    a.default_probability,
    ROUND((a.default_probability * 100)::numeric, 2) AS default_probability_pct,
    a.risk_category,
    a.risk_grade,
    a.approval                              AS recommendation,

    CASE a.risk_category
        WHEN 'Very Low Risk'  THEN 1
        WHEN 'Low Risk'       THEN 2
        WHEN 'Moderate Risk'  THEN 3
        WHEN 'High Risk'      THEN 4
        WHEN 'Very High Risk' THEN 5
        WHEN 'Extreme Risk'   THEN 6
        ELSE 99
    END                                     AS risk_tier_order,

    CASE WHEN a.risk_grade IN ('AAA','AA','A','BBB')
         THEN 'Investment grade' ELSE 'Sub-investment grade'
    END                                     AS grade_band,

    a.status::text                          AS workflow_status,
    a.decision::text                        AS final_decision,
    CASE WHEN a.decision IS NULL THEN 'Awaiting decision'
         ELSE INITCAP(a.decision::text) END AS decision_label,

    app.id                                  AS applicant_id,
    app.full_name                           AS applicant_name,
    app.age                                 AS applicant_age,
    CASE
        WHEN app.age IS NULL THEN 'Unknown'
        WHEN app.age < 25 THEN '18-24'
        WHEN app.age < 35 THEN '25-34'
        WHEN app.age < 45 THEN '35-44'
        WHEN app.age < 55 THEN '45-54'
        WHEN app.age < 65 THEN '55-64'
        ELSE '65+'
    END                                     AS age_band,
    CASE
        WHEN app.age IS NULL THEN 99
        WHEN app.age < 25 THEN 1 WHEN app.age < 35 THEN 2
        WHEN app.age < 45 THEN 3 WHEN app.age < 55 THEN 4
        WHEN app.age < 65 THEN 5 ELSE 6
    END                                     AS age_band_order,
    app.annual_income,

    COALESCE(p.code, 'UNASSIGNED')          AS product_code,
    COALESCE(p.name, 'Unassigned')          AS product_name,
    p.base_rate                             AS product_base_rate,

    safe_numeric(a.inputs ->> 'loan_amount') AS loan_amount,

    COALESCE(analyst.name,  'Unassigned')   AS analyst_name,
    COALESCE(reviewer.name, 'Not reviewed') AS reviewer_name,

    COALESCE(m.name || ' v' || m.version, 'Unknown') AS model_version,
    m.algorithm                             AS model_algorithm

FROM assessments a
LEFT JOIN applicants     app      ON app.id      = a.applicant_id
LEFT JOIN loan_products  p        ON p.id        = a.product_id
LEFT JOIN users          analyst  ON analyst.id  = a.analyst_id
LEFT JOIN users          reviewer ON reviewer.id = a.reviewer_id
LEFT JOIN model_versions m        ON m.id        = a.model_version_id
WHERE a.is_deleted IS NOT TRUE;


-- ----------------------------------------------------------------------------
-- 2. vw_daily_volume — pre-aggregated time series for fast trend visuals.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_daily_volume CASCADE;
CREATE VIEW vw_daily_volume AS
SELECT
    a.created_at::date                              AS assessment_date,
    COUNT(*)                                        AS assessments,
    COUNT(*) FILTER (WHERE a.approval IN ('Auto Approve','Approve'))
                                                    AS auto_approved,
    COUNT(*) FILTER (WHERE a.approval = 'Manual Review')
                                                    AS sent_to_review,
    COUNT(*) FILTER (WHERE a.approval IN ('Reject','Reject or Require Collateral'))
                                                    AS rejected,
    ROUND(AVG(a.default_probability)::numeric, 4)   AS avg_default_probability,
    ROUND(AVG(a.risk_score)::numeric, 1)            AS avg_risk_score,
    COUNT(*) FILTER (WHERE a.default_probability >= 0.35)
                                                    AS high_risk_count,
    COALESCE(SUM(safe_numeric(a.inputs ->> 'loan_amount')), 0)
                                                    AS total_requested_amount
FROM assessments a
WHERE a.is_deleted IS NOT TRUE
GROUP BY a.created_at::date;


-- ----------------------------------------------------------------------------
-- 3. vw_risk_mix — portfolio shape by month, risk tier and product.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_risk_mix CASCADE;
CREATE VIEW vw_risk_mix AS
SELECT
    DATE_TRUNC('month', a.created_at)::date         AS assessment_month,
    a.risk_category,
    CASE a.risk_category
        WHEN 'Very Low Risk'  THEN 1 WHEN 'Low Risk'       THEN 2
        WHEN 'Moderate Risk'  THEN 3 WHEN 'High Risk'      THEN 4
        WHEN 'Very High Risk' THEN 5 WHEN 'Extreme Risk'   THEN 6
        ELSE 99 END                                 AS risk_tier_order,
    a.risk_grade,
    COALESCE(p.name, 'Unassigned')                  AS product_name,
    COUNT(*)                                        AS assessments,
    ROUND(AVG(a.default_probability)::numeric, 4)   AS avg_default_probability,
    COALESCE(SUM(safe_numeric(a.inputs ->> 'loan_amount')), 0)
                                                    AS total_requested_amount
FROM assessments a
LEFT JOIN loan_products p ON p.id = a.product_id
WHERE a.is_deleted IS NOT TRUE
GROUP BY 1, 2, 3, 4, 5;


-- ----------------------------------------------------------------------------
-- 4. vw_portfolio_kpi — single-row headline figures for KPI cards.
--    Returns zeros rather than NULLs on an empty database.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_portfolio_kpi CASCADE;
CREATE VIEW vw_portfolio_kpi AS
SELECT
    COUNT(*)                                          AS total_assessments,
    COUNT(DISTINCT a.applicant_id)                    AS unique_applicants,
    COUNT(*) FILTER (WHERE a.approval IN ('Auto Approve','Approve'))
                                                      AS approved,
    COALESCE(ROUND(100.0 * COUNT(*) FILTER (WHERE a.approval IN ('Auto Approve','Approve'))
             / NULLIF(COUNT(*), 0), 1), 0)            AS approval_rate_pct,
    COALESCE(ROUND(AVG(a.default_probability)::numeric, 4), 0)
                                                      AS avg_default_probability,
    COUNT(*) FILTER (WHERE a.default_probability >= 0.35)
                                                      AS high_risk_count,
    COUNT(*) FILTER (WHERE a.status::text = 'PENDING') AS awaiting_review,
    COALESCE(SUM(safe_numeric(a.inputs ->> 'loan_amount')), 0)
                                                      AS total_requested_amount,
    COALESCE(ROUND(SUM(safe_numeric(a.inputs ->> 'loan_amount')
                       * a.default_probability::numeric), 2), 0)
                                                      AS expected_loss_exposure,
    MIN(a.created_at)::date                           AS first_assessment,
    MAX(a.created_at)::date                           AS latest_assessment
FROM assessments a
WHERE a.is_deleted IS NOT TRUE;


-- ----------------------------------------------------------------------------
-- 5. vw_user_activity — throughput per person, covering BOTH assessments run
--    and assessments reviewed. Correlated subqueries rather than a double
--    join, which would multiply rows and corrupt the averages. Every user
--    appears, including those with no activity yet.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_analyst_activity CASCADE;
DROP VIEW IF EXISTS vw_user_activity CASCADE;
CREATE VIEW vw_user_activity AS
SELECT
    u.id                                            AS user_id,
    u.name                                          AS user_name,
    u.role::text                                    AS role,
    (SELECT COUNT(*) FROM assessments a
      WHERE a.analyst_id = u.id AND a.is_deleted IS NOT TRUE)
                                                    AS assessments_run,
    (SELECT COUNT(*) FROM assessments a
      WHERE a.reviewer_id = u.id AND a.is_deleted IS NOT TRUE)
                                                    AS assessments_reviewed,
    (SELECT COALESCE(ROUND(AVG(a.default_probability)::numeric, 4), 0)
       FROM assessments a
      WHERE a.analyst_id = u.id AND a.is_deleted IS NOT TRUE)
                                                    AS avg_default_probability,
    (SELECT COUNT(*) FROM assessments a
      WHERE a.analyst_id = u.id AND a.is_deleted IS NOT TRUE
        AND a.approval IN ('Auto Approve','Approve'))
                                                    AS approved,
    (SELECT COUNT(*) FROM assessments a
      WHERE a.analyst_id = u.id AND a.is_deleted IS NOT TRUE
        AND a.status::text = 'PENDING')             AS still_pending,
    (SELECT MAX(a.created_at)::date FROM assessments a
      WHERE (a.analyst_id = u.id OR a.reviewer_id = u.id)
        AND a.is_deleted IS NOT TRUE)               AS last_active
FROM users u;

-- Backwards-compatible alias for anything pointing at the old name.
CREATE VIEW vw_analyst_activity AS
SELECT user_name AS analyst_name, role, assessments_run AS assessments,
       avg_default_probability, approved, assessments_reviewed AS decided,
       still_pending, last_active
FROM vw_user_activity;


-- ----------------------------------------------------------------------------
-- 6. vw_workflow_funnel — how assessments move through the review queue.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_workflow_funnel CASCADE;
CREATE VIEW vw_workflow_funnel AS
SELECT
    a.status::text                                  AS workflow_status,
    CASE a.status::text WHEN 'PENDING'  THEN 1
                        WHEN 'REVIEWED' THEN 2
                        WHEN 'DECIDED'  THEN 3
                        ELSE 4 END                  AS stage_order,
    COALESCE(a.decision::text, 'n/a')               AS final_decision,
    COUNT(*)                                        AS assessments,
    ROUND(AVG(a.default_probability)::numeric, 4)   AS avg_default_probability
FROM assessments a
WHERE a.is_deleted IS NOT TRUE
GROUP BY 1, 2, 3;


-- ----------------------------------------------------------------------------
-- Optional: a read-only role for the BI tool.
-- ----------------------------------------------------------------------------
-- CREATE ROLE bi_reader LOGIN PASSWORD 'change-me';
-- GRANT CONNECT ON DATABASE risklens TO bi_reader;
-- GRANT USAGE ON SCHEMA public TO bi_reader;
-- GRANT SELECT ON vw_assessments, vw_daily_volume, vw_risk_mix,
--                 vw_portfolio_kpi, vw_user_activity, vw_analyst_activity,
--                 vw_workflow_funnel
--       TO bi_reader;
-- GRANT EXECUTE ON FUNCTION safe_numeric(text) TO bi_reader;
