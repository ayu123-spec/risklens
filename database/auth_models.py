"""
auth_models.py
--------------
Credentials, kept in their own table rather than bolted onto `users`.

WHY A SEPARATE TABLE
  1. No migration. `init_db()` uses create_all(), which creates missing tables
     but will NOT add columns to a table that already exists. Putting the
     password hash on `users` would need an ALTER TABLE against production;
     a new table appears on its own.
  2. models.py is untouched, so nothing that currently works can break.
  3. It is defensible on its own terms — credentials have a different lifecycle
     and a different sensitivity than profile data, and separating them means a
     query that selects a user's profile cannot accidentally leak a hash.

The link is one-to-one on users.id.
"""
from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String)

try:
    from .models import Base
except ImportError:
    from models import Base


def _utcnow():
    return datetime.now(timezone.utc)


class UserCredential(Base):
    """One row per user who can log in. Users without a row simply cannot."""
    __tablename__ = "user_credentials"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)

    # bcrypt output is 60 chars; 128 leaves room to migrate algorithms later.
    password_hash = Column(String(128), nullable=False)

    # Disable an account without deleting it, so the audit trail stays intact.
    is_active = Column(Boolean, default=True, nullable=False)

    # Lets a token issued before a password change be rejected.
    password_changed_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    failed_attempts = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow,
                        onupdate=_utcnow, nullable=False)

    def __repr__(self):
        return f"<UserCredential user_id={self.user_id} active={self.is_active}>"
