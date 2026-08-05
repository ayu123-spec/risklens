"""Create the demo accounts. Idempotent."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database.db import init_db, SessionLocal
from database.models import User, UserRole
from database.auth_models import UserCredential
from auth.security import hash_password

DEMO = [("admin",    "admin@risklens.demo",    UserRole.ADMIN,    "admin12345"),
        ("analyst",  "analyst@risklens.demo",  UserRole.ANALYST,  "analyst12345"),
        ("reviewer", "reviewer@risklens.demo", UserRole.REVIEWER, "reviewer12345")]

def main():
    init_db()
    db = SessionLocal()
    for name, email, role, pw in DEMO:
        u = db.query(User).filter(User.name == name).first()
        if u is None:
            u = User(name=name, email=email, role=role); db.add(u); db.flush()
        if db.get(UserCredential, u.id) is None:
            db.add(UserCredential(user_id=u.id, password_hash=hash_password(pw)))
            print(f"  created {name} ({role.value})")
        else:
            print(f"  {name} already has credentials")
    db.commit(); db.close()

if __name__ == "__main__":
    main()
