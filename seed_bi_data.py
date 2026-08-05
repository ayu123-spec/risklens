"""
seed_bi_data.py
---------------
Generate a realistic body of assessment history so BI dashboards have something
to show. A handful of live test assessments makes for an empty-looking dashboard;
this produces months of plausible volume with the seasonality and risk mix a
lending book would actually have.

USAGE
    # against your local SQLite database
    python seed_bi_data.py

    # against the production Postgres
    set DATABASE_URL=postgresql://user:pass@host/dbname
    python seed_bi_data.py --months 6 --per-day 12

SAFETY
    Refuses to run if the database already holds more assessments than
    --max-existing (default 100), so it cannot be accidentally re-run against a
    database that already has real history. Pass --force to override.
"""
import argparse
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from database.db import SessionLocal, init_db
from database.models import (Applicant, Assessment, AssessmentStatus, AuditLog,
                             DecisionOutcome, LoanProduct, ModelVersion, User,
                             UserRole)
import database.repository as repo

FIRST_NAMES = ["Aarav","Priya","Rohan","Ananya","Vikram","Meera","Arjun","Divya",
               "Karan","Sneha","Rahul","Isha","Aditya","Nisha","Sanjay","Pooja",
               "Nikhil","Kavya","Amit","Riya"]
LAST_NAMES = ["Sharma","Patel","Reddy","Iyer","Nair","Singh","Gupta","Menon",
              "Desai","Kulkarni","Bose","Rao","Joshi","Chopra","Malhotra"]

ANALYSTS = [("Ayuush Raj", UserRole.ANALYST), ("Priya Menon", UserRole.ANALYST),
            ("Rohan Desai", UserRole.ANALYST), ("Sneha Iyer", UserRole.REVIEWER),
            ("Vikram Nair", UserRole.REVIEWER)]

# (category, grade, approval, pd_low, pd_high) with realistic relative frequency
TIERS = [
    ("Very Low Risk",  "AAA", "Auto Approve",                 0.005, 0.05, 0.18),
    ("Low Risk",       "A",   "Approve",                      0.05,  0.10, 0.24),
    ("Moderate Risk",  "BBB", "Approve with Conditions",      0.10,  0.20, 0.22),
    ("High Risk",      "BB",  "Manual Review",                0.20,  0.35, 0.17),
    ("Very High Risk", "B",   "Reject or Require Collateral", 0.35,  0.50, 0.11),
    ("Extreme Risk",   "CC",  "Reject",                       0.50,  0.85, 0.08),
]
PRODUCT_WEIGHTS = {"HOME": 0.30, "AUTO": 0.24, "PERSONAL": 0.26,
                   "EDUCATION": 0.12, "BUSINESS": 0.08}


def weighted_tier():
    r = random.random()
    acc = 0.0
    for t in TIERS:
        acc += t[5]
        if r <= acc:
            return t
    return TIERS[-1]


def weighted_product(products):
    r = random.random()
    acc = 0.0
    for code, w in PRODUCT_WEIGHTS.items():
        acc += w
        if r <= acc:
            return products.get(code)
    return next(iter(products.values()), None)


def day_volume(day_index, base_per_day):
    """Weekday-heavy volume with a slow upward trend and some noise."""
    date = datetime.now(timezone.utc) - timedelta(days=day_index)
    weekday_factor = 0.35 if date.weekday() >= 5 else 1.0
    trend = 1.0 + 0.5 * (1 - day_index / 200)          # busier recently
    seasonal = 1.0 + 0.18 * math.sin(day_index / 14)   # fortnightly ripple
    n = base_per_day * weekday_factor * trend * seasonal
    return max(0, int(random.gauss(n, n * 0.25)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=6)
    ap.add_argument("--per-day", type=int, default=12)
    ap.add_argument("--max-existing", type=int, default=100)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    init_db()
    db = SessionLocal()

    existing = db.query(Assessment).count()
    if existing > args.max_existing and not args.force:
        print(f"Refusing to seed: {existing} assessments already exist "
              f"(limit {args.max_existing}). Use --force to override.")
        db.close()
        return

    repo.seed_reference_data(db)
    products = {p.code: p for p in db.query(LoanProduct).all()}
    model = repo.get_active_model(db)

    users = []
    for name, role in ANALYSTS:
        users.append(repo.get_or_create_user(
            db, name=name, email=name.lower().replace(" ", ".") + "@risklens.demo",
            role=role))
    analysts = [u for u in users if u.role == UserRole.ANALYST]
    reviewers = [u for u in users if u.role == UserRole.REVIEWER]

    days = args.months * 30
    created = 0
    applicants_made = 0

    print(f"Seeding ~{args.months} months of history…")

    for day_index in range(days, -1, -1):
        n = day_volume(day_index, args.per_day)
        for _ in range(n):
            ts = (datetime.now(timezone.utc)
                  - timedelta(days=day_index,
                              hours=random.randint(0, 23),
                              minutes=random.randint(0, 59)))

            # ~35% are returning applicants, so history ties to people
            applicant = None
            if applicants_made > 20 and random.random() < 0.35:
                applicant = (db.query(Applicant)
                             .offset(random.randint(0, applicants_made - 1))
                             .first())
            if applicant is None:
                applicant = Applicant(
                    full_name=f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
                    age=random.randint(21, 68),
                    annual_income=round(random.lognormvariate(11.2, 0.55), 2),
                    external_ref=f"CUST-{applicants_made + 1000}",
                    created_at=ts,
                )
                if hasattr(Applicant, "updated_at"):
                    applicant.updated_at = ts
                db.add(applicant)
                db.flush()
                applicants_made += 1

            cat, grade, approval, pd_lo, pd_hi, _ = weighted_tier()
            pd_val = round(random.uniform(pd_lo, pd_hi), 4)
            product = weighted_product(products)
            analyst = random.choice(analysts)
            loan_amount = round(random.lognormvariate(12.3, 0.7), 2)

            a = Assessment(
                applicant_id=applicant.id,
                product_id=product.id if product else None,
                analyst_id=analyst.id,
                model_version_id=model.id if model else None,
                inputs={"age": applicant.age,
                        "income": float(applicant.annual_income or 0),
                        "loan_amount": loan_amount,
                        "loan_purpose": (product.code.lower() if product else "personal")},
                result={"risk_category": cat, "risk_grade": grade},
                risk_score=int(round(pd_val * 100)),
                default_probability=pd_val,
                risk_category=cat,
                risk_grade=grade,
                approval=approval,
                status=AssessmentStatus.PENDING,
                created_at=ts,
            )
            if hasattr(Assessment, "updated_at"):
                a.updated_at = ts

            # Older assessments have mostly been worked through the queue.
            age_days = day_index
            if age_days > 3 and random.random() < 0.8:
                reviewer = random.choice(reviewers)
                a.reviewer_id = reviewer.id
                if random.random() < 0.75:
                    a.status = AssessmentStatus.DECIDED
                    if approval in ("Auto Approve", "Approve"):
                        a.decision = DecisionOutcome.APPROVED
                    elif approval in ("Reject", "Reject or Require Collateral"):
                        a.decision = DecisionOutcome.DECLINED
                    else:
                        a.decision = random.choice(
                            [DecisionOutcome.APPROVED, DecisionOutcome.REFERRED,
                             DecisionOutcome.DECLINED])
                else:
                    a.status = AssessmentStatus.REVIEWED

            db.add(a)
            db.flush()
            db.add(AuditLog(user_id=analyst.id, entity_type="assessment",
                            entity_id=a.id, action="assessment.created",
                            detail=f"grade {grade}, score {a.risk_score}",
                            created_at=ts))
            created += 1

        if day_index % 30 == 0:
            db.commit()
            print(f"  {days - day_index:>4} days done · {created:>5} assessments")

    db.commit()
    total = db.query(Assessment).count()
    print(f"\nDone. {created} assessments created ({applicants_made} applicants).")
    print(f"Database now holds {total} assessments.")
    db.close()


if __name__ == "__main__":
    main()
