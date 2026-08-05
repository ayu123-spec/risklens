"""
auth_routes.py
--------------
Authentication endpoints, mounted under /api/auth.

  POST /api/auth/login            exchange name/email + password for a token
  GET  /api/auth/me               who am I
  POST /api/auth/change-password  change your own password
  GET  /api/auth/users            list users            (admin)
  POST /api/auth/users            create a user         (admin)
  POST /api/auth/users/{id}/disable                     (admin)
  POST /api/auth/users/{id}/enable                      (admin)
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_session
from database.models import User, UserRole
from database.auth_models import UserCredential
from auth.security import (PasswordError, create_access_token, hash_password,
                           validate_password, verify_password)
from auth.auth_deps import current_user, require_admin

router = APIRouter()


# ---------------------------------------------------------------- schemas
class LoginIn(BaseModel):
    username: str = Field(..., description="Name or email")
    password: str


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str


class CreateUserIn(BaseModel):
    name: str
    email: str | None = None
    password: str
    role: str = "analyst"


class UserOut(BaseModel):
    id: int
    name: str
    email: str | None
    role: str
    is_active: bool
    last_login_at: str | None


def _user_out(u: User, c: UserCredential | None) -> UserOut:
    return UserOut(
        id=u.id, name=u.name, email=u.email, role=u.role.value,
        is_active=bool(c.is_active) if c else False,
        last_login_at=c.last_login_at.isoformat() if c and c.last_login_at else None,
    )


# ---------------------------------------------------------------- endpoints
@router.post("/auth/login", tags=["auth"])
def login(body: LoginIn, db: Session = Depends(get_session)):
    """
    Exchange credentials for a bearer token.

    Failures return an identical message whether the account is unknown or the
    password is wrong, so the endpoint cannot be used to enumerate valid users.
    """
    generic = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect username or password")

    user = (db.query(User)
            .filter((User.email == body.username) | (User.name == body.username))
            .first())
    if user is None:
        raise generic

    cred = db.get(UserCredential, user.id)
    if cred is None or not cred.is_active:
        raise generic

    if not verify_password(body.password, cred.password_hash):
        cred.failed_attempts = (cred.failed_attempts or 0) + 1
        db.commit()
        raise generic

    cred.failed_attempts = 0
    cred.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(user.id, user.role.value, user.name)
    token["user"] = _user_out(user, cred).model_dump()
    return token


@router.get("/auth/me", tags=["auth"])
def me(user: User = Depends(current_user), db: Session = Depends(get_session)):
    return _user_out(user, db.get(UserCredential, user.id)).model_dump()


@router.post("/auth/change-password", tags=["auth"])
def change_password(body: ChangePasswordIn,
                    user: User = Depends(current_user),
                    db: Session = Depends(get_session)):
    cred = db.get(UserCredential, user.id)
    if cred is None or not verify_password(body.current_password, cred.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Current password is incorrect")
    try:
        cred.password_hash = hash_password(body.new_password)
    except PasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    cred.password_changed_at = datetime.now(timezone.utc)
    db.commit()
    return {"status": "password changed"}


@router.get("/auth/users", tags=["auth"])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_session)):
    users = db.query(User).order_by(User.id).all()
    creds = {c.user_id: c for c in db.query(UserCredential).all()}
    return {"users": [_user_out(u, creds.get(u.id)).model_dump() for u in users]}


@router.post("/auth/users", tags=["auth"], status_code=status.HTTP_201_CREATED)
def create_user(body: CreateUserIn,
                _: User = Depends(require_admin),
                db: Session = Depends(get_session)):
    try:
        role = UserRole(body.role.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role must be one of: {', '.join(r.value for r in UserRole)}")

    try:
        validate_password(body.password)
    except PasswordError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if body.email and db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="A user with that email already exists")

    # A user may already exist without credentials — the seeder creates
    # analysts that way. Attach credentials rather than duplicating the user.
    user = db.query(User).filter(User.name == body.name).first()
    if user is None:
        user = User(name=body.name, email=body.email, role=role)
        db.add(user)
        db.flush()
    elif db.get(UserCredential, user.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="That user already has login credentials")

    db.add(UserCredential(user_id=user.id, password_hash=hash_password(body.password)))
    db.commit()
    db.refresh(user)
    return _user_out(user, db.get(UserCredential, user.id)).model_dump()


@router.post("/auth/users/{user_id}/disable", tags=["auth"])
def disable_user(user_id: int,
                 admin: User = Depends(require_admin),
                 db: Session = Depends(get_session)):
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="You cannot disable your own account")
    cred = db.get(UserCredential, user_id)
    if cred is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User has no credentials")
    cred.is_active = False
    db.commit()
    return {"status": "disabled", "user_id": user_id}


@router.post("/auth/users/{user_id}/enable", tags=["auth"])
def enable_user(user_id: int,
                _: User = Depends(require_admin),
                db: Session = Depends(get_session)):
    cred = db.get(UserCredential, user_id)
    if cred is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="User has no credentials")
    cred.is_active = True
    cred.failed_attempts = 0
    db.commit()
    return {"status": "enabled", "user_id": user_id}
