"""Configuration and Environment Settings for ARGUMAP Backend."""

import os
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ARGUMAP"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database URL: Defaults to local SQLite for development if PostgreSQL is unconfigured
    DATABASE_URL: str = "sqlite:///./argumap_dev.db"

    # CORS Configuration
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"
    CORS_ORIGIN_REGEX: Optional[str] = None

    # Server binding: Default to 0.0.0.0 for container/Render hosting; bind to Render's PORT
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("PORT", "8000"))
    LOG_LEVEL: str = "info"

    @property
    def is_production(self) -> bool:
        return (
            self.APP_ENV.lower() in ("production", "prod")
            or bool(os.environ.get("RENDER"))
        )

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return [origin.strip().rstrip("/") for origin in self.CORS_ORIGINS if origin.strip()]
        val = self.CORS_ORIGINS.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                import json
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(o).strip().rstrip("/") for o in parsed if str(o).strip()]
            except Exception:
                pass
        return [origin.strip().rstrip("/") for origin in val.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
