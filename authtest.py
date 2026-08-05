import os
os.environ.setdefault("DATABASE_URL","postgresql://risklens:test@localhost/risklens_ts")
os.environ.setdefault("JWT_SECRET","test-secret-for-suite")
from fastapi import FastAPI, Depends
from database.models import User, UserRole
from auth.auth_routes import router as auth_router
from auth.auth_deps import current_user, optional_user, require_role, require_admin

app = FastAPI()
app.include_router(auth_router, prefix="/api")

@app.get("/api/public")
def public(): return {"ok": True}

@app.get("/api/public-aware")
def public_aware(user: User | None = Depends(optional_user)):
    return {"signed_in": user is not None, "name": user.name if user else None}

@app.get("/api/any-user")
def any_user(user: User = Depends(current_user)): return {"name": user.name}

@app.get("/api/reviewer-only")
def reviewer_only(user: User = Depends(require_role(UserRole.REVIEWER))):
    return {"name": user.name}

@app.get("/api/admin-only")
def admin_only(user: User = Depends(require_admin)): return {"name": user.name}
