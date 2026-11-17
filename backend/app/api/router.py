"""Central API Router for ARGUMAP."""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.debates import router as debates_router
from app.api.analysis import router as analysis_router

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(debates_router)
api_router.include_router(analysis_router)
