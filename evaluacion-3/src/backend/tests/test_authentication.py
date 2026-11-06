"""T-31: password authentication, cookie sessions and password recovery."""
from __future__ import annotations

import time

import jwt
import pytest
from fastapi.testclient import TestClient

from app import security
from app.config import get_settings
from app.errors import TooManyRequests
from app.main import app
from app.modules.identity.rate_limit import FailureRateLimiter
from tests.conftest import TEST_PASSWORD, seed_base

ORIGIN = "http://localhost:5173"


def _client():
    return TestClient(app, base_url=ORIGIN)


def _login(client, identifier="s1", password=TEST_PASSWORD, **extra):
    return client.post(
        "/auth/login",
        json={"identifier": identifier, "password": password, **extra},
        headers={"Origin": ORIGIN},
    )


def test_login_with_username_and_email_sets_http_only_cookie_and_me_roles(env):
    users = seed_base(env)
    with _client() as client:
        response = _login(client)
        assert response.status_code == 200
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=strict" in cookie and "max-age=900" in cookie
        assert "access_token" not in response.json()

        me = client.get("/auth/me")
        assert me.status_code == 200
        assert me.json()["id"] == users["s1"]
        assert me.json()["username"] == "s1"
        assert [role["role"] for role in me.json()["roles"]] == ["STUDENT"]

    with _client() as client:
        response = _login(client, "S1@tests.example")
        assert response.status_code == 200


def test_bad_password_and_unknown_account_have_the_same_generic_error(env):
    seed_base(env)
    with _client() as client:
        wrong_password = _login(client, "s1", "not-the-right-password")
        unknown_account = _login(client, "missing-user@tests.example", "not-the-right-password")
    assert wrong_password.status_code == unknown_account.status_code == 401
    assert wrong_password.json() == unknown_account.json() == {"error": "unauthorized"}


def test_disabled_account_and_missing_session_are_denied(env):
    users = seed_base(env)
    env.admin.execute("UPDATE user_account SET is_active=false WHERE id=%s", (users["s1"],))
    with _client() as client:
        assert _login(client).status_code == 401
        assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("expired", [False, True])
def test_invalid_or_expired_cookie_is_denied(env, expired):
    seed_base(env)
    settings = get_settings()
    now = int(time.time())
    claims = {
        "sub": "1", "jti": "unknown-session", "iat": now - (3600 if expired else 0),
        "exp": now - 1 if expired else now + 60, "iss": "dh05", "aud": "dh05-web",
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    with _client() as client:
        client.cookies.set(security.SESSION_COOKIE, token)
        assert client.get("/auth/me").status_code == 401


def test_logout_revokes_session_and_clears_cookie(env):
    seed_base(env)
    with _client() as client:
        assert _login(client).status_code == 200
        response = client.post("/auth/logout", headers={"Origin": ORIGIN})
        assert response.status_code == 204
        assert client.get("/auth/me").status_code == 401


def test_client_cannot_choose_role_or_authenticate_with_user_id(env):
    seed_base(env)
    with _client() as client:
        assert _login(client, role="EXPERIENTIAL_COORDINATOR").status_code == 422
        response = client.post(
            "/auth/login", json={"user_id": 1}, headers={"Origin": ORIGIN}
        )
        assert response.status_code == 422
        assert security.SESSION_COOKIE not in client.cookies


def test_password_reset_is_hashed_single_use_and_revokes_sessions(env):
    seed_base(env)
    with _client() as client:
        assert _login(client).status_code == 200
        request = client.post(
            "/auth/password-reset/request",
            json={"email": "s1@tests.example"}, headers={"Origin": ORIGIN},
        )
        assert request.status_code == 200
        payload = request.json()
        assert payload["delivery_mode"] == "local_development_only"
        token = payload["development_token"]
        stored = env.admin.execute("SELECT token_hash FROM auth_password_reset").fetchone()["token_hash"]
        assert stored == security.hash_password_reset_token(token)
        assert stored != token

        updated = client.post(
            "/auth/password-reset/complete",
            json={"token": token, "password": "New-Student-Password-2026!"},
        )
        assert updated.status_code == 200
        assert client.get("/auth/me").status_code == 401
        reused = client.post(
            "/auth/password-reset/complete",
            json={"token": token, "password": "Other-Student-Password-2026!"},
        )
        assert reused.status_code == 400

        assert _login(client, password=TEST_PASSWORD).status_code == 401
        assert _login(client, password="New-Student-Password-2026!").status_code == 200


def test_password_reset_request_does_not_disclose_unknown_email(env):
    seed_base(env)
    with _client() as client:
        known = client.post(
            "/auth/password-reset/request", json={"email": "nobody@tests.example"},
            headers={"Origin": ORIGIN},
        )
    assert known.status_code == 200
    assert "development_token" not in known.json()
    assert "nobody" not in known.text


def test_production_password_reset_does_not_return_a_token(env, monkeypatch):
    seed_base(env)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PASSWORD_RESET_DELIVERY", "disabled")
    monkeypatch.setenv("JWT_SECRET", "production-test-secret-with-at-least-32-bytes")
    monkeypatch.setenv("APP_ALLOWED_ORIGINS", ORIGIN)
    with _client() as client:
        response = client.post(
            "/auth/password-reset/request", json={"email": "s1@tests.example"},
            headers={"Origin": ORIGIN},
        )
    assert response.status_code == 200
    assert "development_token" not in response.json()
    assert "delivery_mode" not in response.json()


def test_password_reset_expiry_is_checked(env):
    users = seed_base(env)
    from app import db
    from app.modules.identity import service as identity

    with db.command(users["s1"]) as ctx:
        token = identity.create_password_reset(ctx, "s1@tests.example")
    env.admin.execute("UPDATE auth_password_reset SET expires_at=now() - interval '1 minute'")
    assert identity.password_reset_owner(env.admin, token) is None


def test_login_failure_limiter_caps_retries():
    limiter = FailureRateLimiter(window_seconds=60, per_identity=2, per_ip=5)
    limiter.check("login", "alice", "127.0.0.1")
    limiter.failed("login", "alice", "127.0.0.1")
    limiter.failed("login", "alice", "127.0.0.1")
    with pytest.raises(TooManyRequests):
        limiter.check("login", "alice", "127.0.0.1")
