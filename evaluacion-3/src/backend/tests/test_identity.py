"""T-21: the JWT carries ONLY the subject id; role changes take effect on the next request."""
from __future__ import annotations

from app import db, security
from app.modules import authz
from tests.conftest import seed_base


def test_token_has_no_roles(env):
    U = seed_base(env)
    token = security.issue_token(U["s1"], "test-session")
    payload = __import__("jwt").decode(token, options={"verify_signature": False})
    assert set(payload) == {"sub", "jti", "iat", "exp", "iss", "aud"}
    assert security.decode_token(token) == (U["s1"], "test-session")


def test_role_change_takes_effect_next_request(env):
    U = seed_base(env)
    with db.read() as cur:
        subj = authz.subject(cur, U["pc_sys"])
        assert [r["role"] for r in subj["roles"]] == ["PROGRAM_COORDINATOR"]
    env.admin.execute("DELETE FROM role_assignment WHERE user_id=%s", (U["pc_sys"],))
    env.admin.execute(
        "INSERT INTO role_assignment(user_id, role, program_id) VALUES (%s,'EXPERIENTIAL_COORDINATOR',NULL)",
        (U["pc_sys"],),
    )
    with db.read() as cur:
        subj = authz.subject(cur, U["pc_sys"])
        assert [r["role"] for r in subj["roles"]] == ["EXPERIENTIAL_COORDINATOR"]
