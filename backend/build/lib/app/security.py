"""JWT (HS256) and invitation-token helpers. The token carries ONLY the subject id."""
from __future__ import annotations

import hashlib
import secrets
import time

import jwt

from .config import get_settings
from .errors import Forbidden


def issue_token(user_id: int) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + s.jwt_ttl_minutes * 60,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> int:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise Forbidden("invalid or expired token") from exc
    return int(payload["sub"])


def new_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
