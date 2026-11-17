"""Database Session and Engine Management.

Startup order:
  1. Try to connect with DATABASE_URL from .env / environment.
  2. If that fails (e.g. PostgreSQL not running), automatically fall back
     to a local SQLite file so development always works out-of-the-box.
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Base class shared by all ORM models
# ---------------------------------------------------------------------------
Base = declarative_base()

_SQLITE_FALLBACK = "sqlite:///./argumap_dev.db"


def _make_engine(url: str):
    """Create a SQLAlchemy engine for *url*, returning None on failure."""
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    try:
        eng = create_engine(url, connect_args=connect_args, echo=False, future=True)
        # Probe the connection immediately so we know it actually works
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as exc:
        logger.warning("Could not connect to '%s': %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Engine initialisation — primary URL then SQLite fallback
# ---------------------------------------------------------------------------
engine = _make_engine(settings.DATABASE_URL)

if engine is None and not settings.DATABASE_URL.startswith("sqlite"):
    logger.warning(
        "Primary DATABASE_URL failed. Falling back to local SQLite: %s",
        _SQLITE_FALLBACK,
    )
    engine = _make_engine(_SQLITE_FALLBACK)

if engine is None:
    logger.error(
        "CRITICAL: Could not initialise any database engine. "
        "Check DATABASE_URL in backend/.env"
    )

SessionLocal = (
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if engine is not None
    else None
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a database session; raises RuntimeError if DB unavailable."""
    if SessionLocal is None:
        raise RuntimeError(
            "Database engine is not initialised. "
            "Check DATABASE_URL in backend/.env — "
            "for local dev use: DATABASE_URL=sqlite:///./argumap_dev.db"
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def check_db_connection() -> dict:
    """Return a dict describing current DB connectivity."""
    if engine is None:
        return {"connected": False, "dialect": "unknown", "error": "Engine not configured"}
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"connected": True, "dialect": engine.dialect.name, "error": None}
    except Exception as exc:
        logger.warning("Database connection check failed: %s", exc)
        return {"connected": False, "dialect": engine.dialect.name, "error": str(exc)}


def init_db():
    """Create all ORM tables (dev / test convenience helper)."""
    if engine is not None:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified on: %s", engine.url)
    else:
        logger.error("init_db() called but engine is None — skipping table creation.")
