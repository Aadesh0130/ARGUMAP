"""Main FastAPI Application Entrypoint for ARGUMAP Backend."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from app.core.config import settings
from app.core.errors import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
)
from app.db.session import init_db
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize tables if local dev database is active
    init_db()
    yield
    # Shutdown: Clean up any background pools if required
    pass


app = FastAPI(
    title=f"{settings.PROJECT_NAME} Backend API",
    description="Automated Argument Structure Analysis and Debate Reasoning Service.",
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Exception handlers for uniform error envelope
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)

# CORS Middleware (Configurable via environment variables)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/", summary="Root Welcome & Metadata", tags=["Root"])
def read_root():
    return {
        "project": settings.PROJECT_NAME,
        "title": "Automated Argument Structure Analysis and Debate Reasoning",
        "version": settings.VERSION,
        "status": "running",
        "documentation": "/docs",
        "api_endpoints": {
            "health": f"{settings.API_V1_STR}/health",
            "debates": f"{settings.API_V1_STR}/debates",
            "analyze": f"{settings.API_V1_STR}/analyze",
        },
    }


# Mount central API router under /api
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
