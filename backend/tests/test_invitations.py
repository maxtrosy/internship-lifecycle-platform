"""T-22: invitation lifecycle (expired, reused, cross-organization)."""
from __future__ import annotations

import pytest

from app import db
from app.errors import BusinessError, NotFound
from app.modules import authz
from app.modules.identity import service as identity
from tests.conftest import make_opportunity, make_placement, seed_base


def test_t22_invitations(env):
    U = seed_base(env)
    with db.command(U["ec1"]) as ctx:
        token = identity.create_invitation(ctx, "ext@org-alfa.example", 1, "HOST_ORG_MEMBER")

    with db.command(None) as ctx:
        user_id, _ = identity.accept_invitation(
            ctx, token, "External Host Member", "external-host", "External-Host-2026!"
        )
    with db.read() as cur:
        subj = authz.subject(cur, user_id)
        assert [r["role"] for r in subj["roles"]] == ["HOST_ORG_MEMBER"]
        assert subj["roles"][0]["host_org_id"] == 1

    # reused
    with pytest.raises(BusinessError) as ei:
        with db.command(None) as ctx:
            identity.accept_invitation(ctx, token, "Second Attempt", "second-host", "Second-Host-2026!")
    assert ei.value.code == "INVITATION_USED"


def test_t22_invitation_expired(env):
    U = seed_base(env)
    with db.command(U["ec1"]) as ctx:
        token = identity.create_invitation(ctx, "exp@example.com", 1, "HOST_ORG_MEMBER")
    env.admin.execute("UPDATE invitation SET expires_at = now() - interval '1 day'")
    with pytest.raises(BusinessError) as ei:
        with db.command(None) as ctx:
            identity.accept_invitation(ctx, token, "Late", "late-host", "Late-Host-Password-2026!")
    assert ei.value.code == "INVITATION_EXPIRED"


def test_t22_invitation_cross_org_denied(env):
    U = seed_base(env)
    with db.command(U["ec1"]) as ctx:
        token = identity.create_invitation(ctx, "a@example.com", 1, "HOST_ORG_MEMBER")
    with db.command(None) as ctx:
        user_id, _ = identity.accept_invitation(
            ctx, token, "Host A", "host-a", "Host-A-Password-2026!"
        )
    opp_b = make_opportunity(env, 2, U["P"]["ADM"], "Beta")
    p_b = make_placement(env, U["s3"], opp_b)
    with db.read() as cur:
        subj = authz.subject(cur, user_id)
        assert authz.can_read(cur, subj, p_b) is False
        with pytest.raises(NotFound):
            authz.authorize(cur, subj, "placement:read", p_b)
