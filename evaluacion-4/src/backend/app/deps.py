"""FastAPI dependencies. Every route must declare its action via ``requires(action)`` (R-012)."""
from __future__ import annotations

from fastapi import Request

from app import db, security
from app.config import get_settings
from app.errors import Forbidden, Unauthorized
from app.modules.authz import service as authz


def _authenticate(request: Request) -> int:
    token = request.cookies.get(security.SESSION_COOKIE)
    if not token:
        raise Unauthorized()
    user_id, session_id = security.decode_token(token)
    with db.read() as cur:
        session = cur.execute(
            """SELECT s.user_id FROM auth_session s JOIN user_account u ON u.id=s.user_id
               WHERE s.jti=%s AND s.user_id=%s AND s.revoked_at IS NULL
                 AND s.expires_at>now() AND u.is_active=true""",
            (session_id, user_id),
        ).fetchone()
        if session is None:
            raise Unauthorized()
    if request.method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin", "").rstrip("/")
        if origin not in get_settings().allowed_origins:
            raise Forbidden("untrusted origin")
    request.state.auth_session_id = session_id
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
