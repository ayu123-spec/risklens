"""
auth_deps.py
------------
FastAPI dependencies for authentication and role-based access control.

USAGE
    # any logged-in user
    def endpoint(user: User = Depends(current_user)): ...

    # reviewers and admins only
    def endpoint(user: User = Depends(require_role(UserRole.REVIEWER,
                                                   UserRole.ADMIN))): ...

    # logged in if a token is present, None otherwise — for endpoints that are
    # public but behave differently when you are signed in
    def endpoint(user: User | None = Depends(optional_user)): ...
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database.db import get_session
from database.models import User, UserRole
from database.auth_models import UserCredential
from auth.security import decode_access_token

# auto_error=False so a missing header reaches our code and can produce a
# consistent 401 body, rather than FastAPI's default 403.
_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _user_from_token(creds, db: Session) -> User | None:
    if creds is None or not creds.credentials:
        return None
    payload = decode_access_token(creds.credentials)
    if not payload:
        return None
    try:
        user_id = int(payload.get("sub", ""))
    except (TypeError, ValueError):
        return None

    user = db.get(User, user_id)
    if user is None:
        return None

    # A disabled account must stop working immediately, even while its token
    # is still within its expiry window.
    cred = db.get(UserCredential, user_id)
    if cred is None or not cred.is_active:
        return None

    return user


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_session),
) -> User:
    """Require a valid token. Raises 401 otherwise."""
    user = _user_from_token(creds, db)
    if user is None:
        raise _UNAUTHORIZED
    return user


def optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_session),
) -> User | None:
    """Return the user if signed in, None if not. Never raises."""
    return _user_from_token(creds, db)


def require_role(*allowed: UserRole):
    """
    Dependency factory restricting an endpoint to specific roles.

    ADMIN is deliberately allowed everywhere — an admin locked out of the
    reviewer screens cannot fix anything.
    """
    allowed_set = set(allowed) | {UserRole.ADMIN}

    def _check(user: User = Depends(current_user)) -> User:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(f"This action requires one of: "
                        f"{', '.join(sorted(r.value for r in allowed_set))}. "
                        f"Your role is '{user.role.value}'."),
            )
        return user

    return _check


# Common shorthands
require_analyst = require_role(UserRole.ANALYST, UserRole.REVIEWER)
require_reviewer = require_role(UserRole.REVIEWER)
require_admin = require_role(UserRole.ADMIN)
