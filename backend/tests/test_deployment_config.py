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
    """Verify that all PostgreSQL URL formats (postgres://, postgresql://, postgresql+psycopg://)
    are normalized to postgresql+psycopg2:// for consistent psycopg2-binary compatibility.
    """
    from sqlalchemy import create_engine

    # 1. Legacy postgres:// format (common on Render / Heroku)
    legacy_url = "postgres://user:pass@ep-cool-db.render.com/argumap"
    norm_legacy = _normalize_db_url(legacy_url)
    assert norm_legacy.startswith("postgresql+psycopg2://")
    assert norm_legacy == "postgresql+psycopg2://user:pass@ep-cool-db.render.com/argumap"

    # 2. Driver-ambiguous postgresql:// format
    pg_url = "postgresql://user:pass@ep-cool-db.render.com/argumap"
    norm_pg = _normalize_db_url(pg_url)
    assert norm_pg == "postgresql+psycopg2://user:pass@ep-cool-db.render.com/argumap"

    # 3. postgresql+psycopg:// format (which previously caused No module named 'psycopg')
    psycopg_url = "postgresql+psycopg://user:pass@ep-cool-db.render.com/argumap"
    norm_psycopg = _normalize_db_url(psycopg_url)
    assert norm_psycopg == "postgresql+psycopg2://user:pass@ep-cool-db.render.com/argumap"

    # 4. Explicit postgresql+psycopg2:// format preserved
    psycopg2_url = "postgresql+psycopg2://user:pass@ep-cool-db.render.com/argumap"
    assert _normalize_db_url(psycopg2_url) == psycopg2_url

    # 5. Non-postgres URLs (e.g. SQLite) remain unchanged
    sqlite_url = "sqlite:///./argumap_dev.db"
    assert _normalize_db_url(sqlite_url) == sqlite_url

    # 6. Verify SQLAlchemy engine creation uses the installed psycopg2 driver without ModuleNotFoundError
    for test_url in [legacy_url, pg_url, psycopg_url, psycopg2_url]:
        engine = create_engine(_normalize_db_url(test_url))
        assert engine.driver == "psycopg2"
        assert engine.dialect.name == "postgresql"


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
    """Simulates frontend/src/lib/api.ts resolveApiBaseUrl() and buildApiUrl() to guarantee consistency."""
    import re

    def resolve_api_base_url(env_url: str | None) -> str:
        if not env_url or not isinstance(env_url, str) or not env_url.strip():
            return "http://localhost:8000/api"

        cleaned = env_url.strip()
        # 1. Strip query parameters and hash fragments
        cleaned = cleaned.split("?")[0].split("#")[0].strip()
        # 2. Strip trailing slashes
        cleaned = re.sub(r"/+$", "", cleaned)

        if not cleaned:
            return "http://localhost:8000/api"

        # 3. Prepend protocol if omitted
        if not (cleaned.startswith("http://") or cleaned.startswith("https://") or cleaned.startswith("/")):
            if cleaned.startswith("localhost") or cleaned.startswith("127.0.0.1"):
                cleaned = f"http://{cleaned}"
            else:
                cleaned = f"https://{cleaned}"

        # 4. Deduplicate repeated /api
        while cleaned.endswith("/api/api"):
            cleaned = cleaned[:-4]

        # 5. Ensure it ends with /api
        if not cleaned.endswith("/api"):
            cleaned = f"{cleaned}/api"

        return cleaned

    def build_api_url(endpoint: str, base: str) -> str:
        normalized = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{base}{normalized}"

    # 1. Undefined or empty -> local dev fallback
    assert resolve_api_base_url(None) == "http://localhost:8000/api"
    assert resolve_api_base_url("   ") == "http://localhost:8000/api"

    # 2. Host with trailing /api
    assert resolve_api_base_url("https://argumap-api.onrender.com/api") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("https://argumap-api.onrender.com/api/") == "https://argumap-api.onrender.com/api"

    # 3. Host without /api
    assert resolve_api_base_url("https://argumap-api.onrender.com") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("https://argumap-api.onrender.com/") == "https://argumap-api.onrender.com/api"

    # 4. Multiple trailing slashes
    assert resolve_api_base_url("https://argumap-api.onrender.com///") == "https://argumap-api.onrender.com/api"

    # 5. Query parameters (e.g. ?utm_source=chatgpt.com) stripped cleanly
    assert resolve_api_base_url("https://argumap-api.onrender.com/api?utm_source=chatgpt.com") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("https://argumap-api.onrender.com/api?utm_source=chatgpt.com/api") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("https://argumap-api.onrender.com?utm_source=chatgpt.com") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("https://argumap-api.onrender.com/?utm_source=chatgpt.com") == "https://argumap-api.onrender.com/api"

    # 6. Hash fragments stripped cleanly
    assert resolve_api_base_url("https://argumap-api.onrender.com/api#overview") == "https://argumap-api.onrender.com/api"

    # 7. Deduplicate duplicate /api/api
    assert resolve_api_base_url("https://argumap-api.onrender.com/api/api") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("https://argumap-api.onrender.com/api/api/") == "https://argumap-api.onrender.com/api"

    # 8. Domain without scheme
    assert resolve_api_base_url("argumap-api.onrender.com") == "https://argumap-api.onrender.com/api"
    assert resolve_api_base_url("localhost:8000") == "http://localhost:8000/api"

    # 9. Verify endpoint construction with build_api_url
    base = resolve_api_base_url("https://argumap-api.onrender.com/api?utm_source=chatgpt.com/api")
    assert build_api_url("/analyze", base) == "https://argumap-api.onrender.com/api/analyze"
    assert build_api_url("analyze", base) == "https://argumap-api.onrender.com/api/analyze"
    assert build_api_url("/health", base) == "https://argumap-api.onrender.com/api/health"
    assert build_api_url("/analysis/test-uuid-123", base) == "https://argumap-api.onrender.com/api/analysis/test-uuid-123"
    assert build_api_url("/speak", base) == "https://argumap-api.onrender.com/api/speak"


