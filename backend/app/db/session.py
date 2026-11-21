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


def _normalize_db_url(url: str) -> str:
    """Normalize legacy postgres:// scheme to postgresql:// for SQLAlchemy compatibility."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _mask_db_url(url: str) -> str:
    """Mask credentials in database URL to prevent sensitive leaks in logs and error messages."""
    if not url:
        return ""
    try:
        from sqlalchemy.engine import make_url
        return make_url(url).render_as_string(hide_password=True)
    except Exception:
        import re
        return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


def _make_engine(url: str):
    """Create a SQLAlchemy engine for *url*, returning None on failure."""
    is_sqlite = url.startswith("sqlite")
    connect_args = {"check_same_thread": False} if is_sqlite else {}
    engine_kwargs = {
        "connect_args": connect_args,
        "echo": False,
        "future": True,
    }
    if not is_sqlite:
        engine_kwargs["pool_pre_ping"] = True
    try:
        eng = create_engine(url, **engine_kwargs)
        # Probe the connection immediately so we know it actually works
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        return eng
    except Exception as exc:
        logger.warning("Could not connect to '%s': %s", _mask_db_url(url), exc)
        return None


# ---------------------------------------------------------------------------
# Engine initialisation — primary URL then guarded SQLite fallback
# ---------------------------------------------------------------------------
_normalized_url = _normalize_db_url(settings.DATABASE_URL)
engine = _make_engine(_normalized_url)

if engine is None:
    is_production = settings.is_production
    is_postgres = _normalized_url.startswith("postgresql")

    # In production, or when explicitly targeting PostgreSQL in production,
    # NEVER silently fall back to local SQLite! Raise an error so deployment fails visibly.
    if is_production:
        safe_url = _mask_db_url(_normalized_url)
        error_msg = (
            f"CRITICAL: Failed to connect to production database ({safe_url}). "
            f"Automatic SQLite fallback is disabled in production (APP_ENV={settings.APP_ENV}). "
            f"Please verify your DATABASE_URL, PostgreSQL credentials, and database server status."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    else:
        logger.warning(
            "Primary DATABASE_URL failed in development mode. Falling back to local SQLite: %s",
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
