"""Application configuration from environment variables. Never hard-code secrets."""
from __future__ import annotations

import os
from dataclasses import dataclass

OPPORTUNITY_AUTHORITY_ROLES = {"PROGRAM_COORDINATOR", "EXPERIENTIAL_COORDINATOR"}
FACULTY_ASSIGNER_ROLES = {"PROGRAM_COORDINATOR", "EXPERIENTIAL_COORDINATOR"}

@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_ttl_minutes: int
    app_env: str
    allowed_origins: tuple[str, ...]
    password_reset_delivery: str
    app_role: str = "app_user"
    jwt_algorithm: str = "HS256"
    opportunity_reviewer_roles: tuple[str, ...] = ()
    opportunity_publisher_roles: tuple[str, ...] = ()
    faculty_assigner_roles: tuple[str, ...] = ()


def get_settings() -> Settings:
    app_env = os.environ.get("APP_ENV", "development").strip().lower()
    dev_secret = "local-only-dh05-secret-change-for-any-shared-environment-2026"
    jwt_secret = os.environ.get("JWT_SECRET", dev_secret)
    if len(jwt_secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 bytes")
    if app_env == "production" and ("JWT_SECRET" not in os.environ or jwt_secret == dev_secret):
        raise RuntimeError("Production requires a JWT_SECRET supplied by the deployment environment")

    origins_raw = os.environ.get(
        "APP_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    allowed_origins = tuple(origin.strip().rstrip("/") for origin in origins_raw.split(",") if origin.strip())
    if not allowed_origins:
        raise RuntimeError("APP_ALLOWED_ORIGINS must contain at least one origin")
    if app_env == "production" and "APP_ALLOWED_ORIGINS" not in os.environ:
        raise RuntimeError("Production requires APP_ALLOWED_ORIGINS")

    reset_default = "development-token" if app_env == "development" else "disabled"
    password_reset_delivery = os.environ.get("PASSWORD_RESET_DELIVERY", reset_default).strip().lower()
    if password_reset_delivery not in {"development-token", "disabled"}:
        raise RuntimeError("Unsupported PASSWORD_RESET_DELIVERY adapter")
    if app_env == "production" and password_reset_delivery == "development-token":
        raise RuntimeError("Development reset tokens cannot be enabled in production")

    ttl = int(os.environ.get("JWT_TTL_MINUTES", "15"))
    if ttl < 1 or ttl > 24 * 60:
        raise RuntimeError("JWT_TTL_MINUTES must be between 1 and 1440")
    def authority_roles(key: str) -> tuple[str, ...]:
        raw = os.environ.get(key, "")
        roles = tuple(dict.fromkeys(role.strip().upper() for role in raw.split(",") if role.strip()))
        invalid = set(roles) - OPPORTUNITY_AUTHORITY_ROLES
        if invalid:
            raise RuntimeError(f"{key} contains unsupported institutional role(s): {', '.join(sorted(invalid))}")
        return roles

    faculty_assigner_roles = tuple(dict.fromkeys(
        role.strip().upper() for role in os.environ.get("PLACEMENT_FACULTY_ASSIGNER_ROLES", "").split(",")
        if role.strip()
    ))
    invalid_faculty_roles = set(faculty_assigner_roles) - FACULTY_ASSIGNER_ROLES
    if invalid_faculty_roles:
        raise RuntimeError(
            "PLACEMENT_FACULTY_ASSIGNER_ROLES contains unsupported institutional role(s): "
            + ", ".join(sorted(invalid_faculty_roles))
        )

    return Settings(
        database_url=os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/postgres"),
        jwt_secret=jwt_secret,
        jwt_ttl_minutes=ttl,
        app_env=app_env,
        allowed_origins=allowed_origins,
        password_reset_delivery=password_reset_delivery,
        app_role=os.environ.get("APP_DB_ROLE", "app_user"),
        opportunity_reviewer_roles=authority_roles("OPPORTUNITY_REVIEWER_ROLES"),
        opportunity_publisher_roles=authority_roles("OPPORTUNITY_PUBLISHER_ROLES"),
        faculty_assigner_roles=faculty_assigner_roles,
    )


settings = get_settings()
