"""Health Check API Router."""

from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.core.config import settings
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service Health & Database Status")
def health_check(response: Response):
    """Returns application health status and database connectivity details.

    Accurately reflects database connectivity for cloud / Render health monitoring
    without exposing credentials, error traces, or sensitive connection parameters.
    """
    db_status = check_db_connection()
    is_connected = bool(db_status.get("connected", False))

    if not is_connected:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "healthy" if is_connected else "unhealthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "database": "connected" if is_connected else "disconnected",
        "database_dialect": db_status.get("dialect", "unknown"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
