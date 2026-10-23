"""Application configuration from environment variables. Never hard-code secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_ttl_minutes: int
    app_role: str = "app_user"
    jwt_algorithm: str = "HS256"


def get_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/postgres"),
        # A default exists only so the app can start in development; set JWT_SECRET in real runs.
        jwt_secret=os.environ.get("JWT_SECRET", "dev-insecure-secret-change-me"),
        jwt_ttl_minutes=int(os.environ.get("JWT_TTL_MINUTES", "15")),
        app_role=os.environ.get("APP_DB_ROLE", "app_user"),
    )


settings = get_settings()
