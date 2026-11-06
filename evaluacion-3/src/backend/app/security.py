"""Argon2id password hashing, short-lived session JWTs and one-time token helpers."""
from __future__ import annotations

import hashlib
import secrets
import time
import uuid

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from .config import get_settings
from .errors import Unauthorized

SESSION_COOKIE = "dh05_session"
PASSWORD_MIN_LENGTH = 12
_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2,
                                 hash_len=32, salt_len=16)
_dummy_password_hash = _password_hasher.hash("not-a-real-user-password")


def hash_password(password: str) -> str:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must contain at least {PASSWORD_MIN_LENGTH} characters")
    return _password_hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    candidate = stored_hash or _dummy_password_hash
    try:
        valid = _password_hasher.verify(candidate, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError, ValueError):
        valid = False
    return bool(valid and stored_hash)


def new_session_id() -> str:
    return uuid.uuid4().hex


def issue_token(user_id: int, session_id: str) -> str:
    s = get_settings()
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "jti": session_id,
        "iat": now,
        "exp": now + s.jwt_ttl_minutes * 60,
        "iss": "dh05",
        "aud": "dh05-web",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> tuple[int, str]:
    s = get_settings()
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm],
                             issuer="dh05", audience="dh05-web",
                             options={"require": ["sub", "jti", "iat", "exp", "iss", "aud"]})
        return int(payload["sub"]), str(payload["jti"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise Unauthorized() from exc


def new_invitation_token() -> str:
    return secrets.token_urlsafe(32)


def hash_invitation_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_password_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
