"""Password-reset delivery seam.

No real mail provider is configured. Development can return a one-time token directly to the
local operator; production leaves delivery disabled until an institutional mail adapter exists.
"""
from __future__ import annotations

from typing import Protocol

from app.config import Settings, get_settings


class PasswordResetDelivery(Protocol):
    def deliver(self, email: str, token: str) -> dict[str, str] | None: ...


class DevelopmentTokenDelivery:
    def deliver(self, email: str, token: str) -> dict[str, str]:
        return {"development_token": token, "delivery_mode": "local_development_only"}


class DisabledPasswordResetDelivery:
    def deliver(self, email: str, token: str) -> None:
        return None


def get_password_reset_delivery(settings: Settings | None = None) -> PasswordResetDelivery:
    settings = settings or get_settings()
    if settings.app_env == "development" and settings.password_reset_delivery == "development-token":
        return DevelopmentTokenDelivery()
    return DisabledPasswordResetDelivery()
