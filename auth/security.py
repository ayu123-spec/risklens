"""
security.py
-----------
Password hashing and JWT handling. No passlib — passlib 1.7.4 is incompatible
with bcrypt 4.x+ and fails at runtime with a version-detection error, so bcrypt
is used directly.

CONFIGURATION
  JWT_SECRET       required in production. Falls back to a random value at
                   import time in development, which means restarting the server
                   invalidates existing tokens — deliberate, so a missing secret
                   is noticed rather than silently insecure.
  JWT_EXPIRE_HOURS default 12.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

# bcrypt refuses anything longer than this, so it is validated up front rather
# than surfacing as a 500 from deep inside the hashing call.
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8

ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))

_secret = os.getenv("JWT_SECRET", "").strip()
if not _secret:
    # Ephemeral secret: tokens die on restart. Fine locally, loud in production.
    _secret = secrets.token_urlsafe(48)
    print("WARNING: JWT_SECRET is not set. Using a random per-process secret — "
          "tokens will be invalidated on restart. Set JWT_SECRET in production.")
JWT_SECRET = _secret


class PasswordError(ValueError):
    """Raised when a password cannot be used, with a message safe to show."""


def validate_password(password: str) -> None:
    """Check a password can actually be hashed before trying."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise PasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise PasswordError(
            f"Password must be at most {MAX_PASSWORD_BYTES} bytes "
            f"(bcrypt's limit). Note that accented and non-Latin characters "
            f"use more than one byte each.")


def hash_password(password: str) -> str:
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"),
                         bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time check. Returns False rather than raising on bad input."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"),
                              password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Over-long password, or a malformed/corrupted hash in the database.
        return False


def create_access_token(user_id: int, role: str, name: str) -> dict:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),      # JWT spec: 'sub' must be a string
        "role": role,
        "name": name,
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    return {
        "access_token": jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM),
        "token_type": "bearer",
        "expires_at": expires.isoformat(),
        "expires_in": JWT_EXPIRE_HOURS * 3600,
    }


def decode_access_token(token: str) -> dict | None:
    """Return the payload, or None if the token is invalid or expired."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
