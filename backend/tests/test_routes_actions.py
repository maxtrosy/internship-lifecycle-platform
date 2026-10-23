"""T-20: every route must declare an authorization action (R-012).

Exempt: /health, /auth/login, /auth/accept-invitation (and FastAPI's built-in docs).
"""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.main import app

EXEMPT = {
    "/health", "/auth/login", "/auth/accept-invitation",
    "/auth/password-reset/request", "/auth/password-reset/complete",
}


def _declared_action(route: APIRoute) -> str | None:
    for dep in route.dependant.dependencies:
        action = getattr(dep.call, "requires_action", None)
        if action:
            return action
    return None


def test_all_routes_declare_action():
    missing = []
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        path = route.path
        if path in EXEMPT or path.startswith("/openapi") or path.startswith("/docs") or path.startswith("/redoc"):
            continue
        if _declared_action(route) is None:
            missing.append(f"{','.join(sorted(route.methods))} {path}")
    assert not missing, f"routes without a declared action: {missing}"
