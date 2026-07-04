"""
db.py — connection + session handling with production-grade configuration.

- Postgres in production (via DATABASE_URL), SQLite locally (zero setup).
- Connection pooling tuned for a web app (pool_size, overflow, recycle, pre_ping).
- Session factory + FastAPI dependency.
"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from models import Base


def _normalize(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


DATABASE_URL = _normalize(os.getenv("DATABASE_URL", "sqlite:///risklens_local.db"))
IS_SQLITE = DATABASE_URL.startswith("sqlite")

if IS_SQLITE:
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    # SQLite doesn't enforce foreign keys by default — turn them on so the
    # constraints in the schema actually apply during local testing.
    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
else:
    # Postgres: real connection pooling for concurrent web traffic.
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,            # base connections kept open
        max_overflow=10,        # extra connections under load
        pool_recycle=1800,      # recycle after 30 min (avoids stale connections)
        pool_pre_ping=True,     # check a connection is alive before using it
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db():
    """Create all tables if absent. For real schema changes, use Alembic migrations."""
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
