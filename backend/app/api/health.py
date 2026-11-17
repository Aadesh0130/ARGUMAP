"""Health Check API Router."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Service Health & Database Status")
def health_check():
    """Returns application health status and database connectivity details."""
    db_status = check_db_connection()
    
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "database": "connected" if db_status["connected"] else "disconnected",
        "database_dialect": db_status["dialect"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
