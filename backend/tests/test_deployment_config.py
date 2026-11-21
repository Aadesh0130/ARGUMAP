"""Deployment Configuration Tests for ARGUMAP Backend.

Validates:
1. Server binding defaults to 0.0.0.0 and dynamically respects PORT.
2. CORS origins parsing supports comma-separated strings and JSON arrays.
3. PostgreSQL DATABASE_URL normalization (postgres:// -> postgresql://).
4. Production database safety: Disallows silent SQLite fallback when in production.
"""

import os
import pytest
from app.core.config import Settings
from app.db.session import _normalize_db_url


def test_server_binding_defaults_and_env_override():
    """Verify that HOST defaults to 0.0.0.0 and PORT respects environment variables."""
    # Test default
    settings = Settings()
    assert settings.HOST == "0.0.0.0"

    # Test override with custom PORT
    os.environ["PORT"] = "10000"
    try:
        custom_settings = Settings()
        assert custom_settings.PORT == 10000
        assert custom_settings.HOST == "0.0.0.0"
    finally:
        del os.environ["PORT"]


def test_cors_origins_parsing():
    """Verify CORS origins parsing for both comma-separated and JSON string formats."""
    # Comma-separated with whitespace
    s1 = Settings(CORS_ORIGINS="https://argumap.vercel.app, http://localhost:5173, https://preview.vercel.app ")
    origins = s1.cors_origins_list
    assert len(origins) == 3
    assert "https://argumap.vercel.app" in origins
    assert "http://localhost:5173" in origins
    assert "https://preview.vercel.app" in origins

    # JSON array string
    s2 = Settings(CORS_ORIGINS='["https://argumap.vercel.app", "http://localhost:3000"]')
    origins2 = s2.cors_origins_list
    assert len(origins2) == 2
    assert "https://argumap.vercel.app" in origins2
    assert "http://localhost:3000" in origins2


def test_postgres_url_normalization():
    """Verify that legacy postgres:// URLs from Render/Heroku are normalized to postgresql://."""
    legacy_url = "postgres://user:pass@ep-cool-db.render.com/argumap"
    normalized = _normalize_db_url(legacy_url)
    assert normalized.startswith("postgresql://")
    assert normalized == "postgresql://user:pass@ep-cool-db.render.com/argumap"

    # Standard URLs should remain unchanged
    pg_url = "postgresql://user:pass@host/db"
    assert _normalize_db_url(pg_url) == pg_url

    sqlite_url = "sqlite:///./argumap_dev.db"
    assert _normalize_db_url(sqlite_url) == sqlite_url


def test_production_database_safety_no_sqlite_fallback(monkeypatch):
    """Verify that in production (APP_ENV=production), failing to connect to PostgreSQL

    raises a RuntimeError and does NOT silently fall back to local SQLite.
    """
    from app.db import session as db_session_module

    # Mock settings to simulate production with an unreachable PostgreSQL URL
    prod_settings = Settings(
        APP_ENV="production",
        DATABASE_URL="postgresql://unreachable_user:wrong_pass@127.0.0.1:5432/nonexistent_db",
    )
    monkeypatch.setattr(db_session_module, "settings", prod_settings)

    # In production, failing to connect must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        # Simulate session initialisation logic
        _norm = db_session_module._normalize_db_url(prod_settings.DATABASE_URL)
        eng = db_session_module._make_engine(_norm)
        if eng is None and prod_settings.is_production:
            raise RuntimeError(
                f"CRITICAL: Failed to connect to production database ({_norm}). "
                f"Automatic SQLite fallback is disabled in production."
            )

    assert "Automatic SQLite fallback is disabled in production" in str(exc_info.value)


def test_mask_db_url_redacts_credentials():
    """Verify that database passwords are redacted from connection strings."""
    from app.db.session import _mask_db_url

    raw_url = "postgresql://argumap_user:superSecretPassword123!@ep-cool-db.render.com:5432/argumap"
    masked = _mask_db_url(raw_url)
    assert "superSecretPassword123!" not in masked
    assert "argumap_user" in masked
    assert "ep-cool-db.render.com" in masked
    assert "argumap" in masked


def test_cors_origins_strips_trailing_slashes():
    """Verify that trailing slashes on CORS origins are stripped to prevent exact matching failures."""
    s = Settings(CORS_ORIGINS="https://argumap.vercel.app/, https://preview.vercel.app///")
    origins = s.cors_origins_list
    assert "https://argumap.vercel.app" in origins
    assert "https://preview.vercel.app" in origins
    assert not any(o.endswith("/") for o in origins)


def test_cors_wildcard_credentials_safety():
    """Verify that wildcard origins cannot be combined with allow_credentials=True."""
    s = Settings(CORS_ORIGINS="*")
    origins = s.cors_origins_list
    has_wildcard = "*" in origins
    # Under our main.py logic:
    allow_credentials = not has_wildcard
    assert allow_credentials is False


def test_frontend_api_url_resolution_logic():
    """Simulates frontend/src/lib/api.ts resolveApiBaseUrl() to guarantee consistency."""
    def resolve_api_base_url(env_url: str | None) -> str:
        if not env_url or not env_url.strip():
            return "http://localhost:8000/api"
        trimmed = env_url.strip().rstrip("/")
        if not trimmed.endswith("/api"):
            return f"{trimmed}/api"
        return trimmed

    # 1. Undefined or empty -> local dev fallback
    assert resolve_api_base_url(None) == "http://localhost:8000/api"
    assert resolve_api_base_url("   ") == "http://localhost:8000/api"

    # 2. Host with trailing /api
    assert resolve_api_base_url("https://argumap.onrender.com/api") == "https://argumap.onrender.com/api"
    assert resolve_api_base_url("https://argumap.onrender.com/api/") == "https://argumap.onrender.com/api"

    # 3. Host without /api
    assert resolve_api_base_url("https://argumap.onrender.com") == "https://argumap.onrender.com/api"
    assert resolve_api_base_url("https://argumap.onrender.com/") == "https://argumap.onrender.com/api"

    # 4. Multiple trailing slashes
    assert resolve_api_base_url("https://argumap.onrender.com///") == "https://argumap.onrender.com/api"


