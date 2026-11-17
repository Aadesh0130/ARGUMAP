"""Configuration and Environment Settings for ARGUMAP Backend."""

from typing import List, Union
from pydantic import field_validator
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
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://localhost:3000"

    # Server binding
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    @property
    def cors_origins_list(self) -> List[str]:
        if isinstance(self.CORS_ORIGINS, list):
            return self.CORS_ORIGINS
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
