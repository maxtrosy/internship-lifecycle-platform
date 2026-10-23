"""FastAPI dependencies. Every route must declare its action via ``requires(action)`` (R-012)."""
from __future__ import annotations

from fastapi import Request

from app import db, security
from app.errors import Forbidden, NotFound
from app.modules.authz import service as authz


def _authenticate(request: Request) -> int:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        raise Forbidden("missing bearer token")
    user_id = security.decode_token(header[7:].strip())
    with db.read() as cur:
        if authz.subject(cur, user_id) is None:
            raise NotFound()
    return user_id


def requires(action: str):
    """Declare an authorization action for a route and authenticate the caller.

    Roles are NOT in the token; they are evaluated in the DB on every request.
    """

    def dependency(request: Request) -> int:
        request.state.declared_action = action
        return _authenticate(request)

    dependency.requires_action = action  # inspected by tests/test_routes_actions.py (T-20)
    return dependency
