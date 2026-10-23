"""T-25: eligibility-evaluated applications (C-04/C-05)."""
from __future__ import annotations

import pytest

from app import db
from app.errors import BusinessError, Forbidden
from app.modules.applications import service as apps
from app.modules.opportunities import service as opps
from app.modules.policies import service as policies
from tests.conftest import seed_base


def _setup(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [
            {"type": "CREDITS_MIN", "value": 100},
            {"type": "ACADEMIC_LEVEL_MIN", "value": 6},
        ])
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Alfa")
    return U, oid


def test_t25_eligible_and_ineligible(env):
    U, oid = _setup(env)
    with db.command(U["s1"]) as ctx:
        r1 = apps.submit_application(ctx, oid)
    assert r1["state"] == "SUBMITTED" and r1["eligibility"]["result"] == "ELIGIBLE"
    with db.command(U["s2"]) as ctx:
        r2 = apps.submit_application(ctx, oid)
    assert r2["state"] == "INELIGIBLE"
    assert any("credits 90 < 100" in reason for reason in r2["eligibility"]["reasons"])


def test_t25_non_published(env):
    U, oid = _setup(env)
    env.admin.execute("UPDATE opportunity SET state='DRAFT' WHERE id=%s", (oid,))
    with db.command(U["s1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            apps.submit_application(ctx, oid)
    assert ei.value.code == "OPPORTUNITY_NOT_PUBLISHED"


def test_t25_no_policy(env):
    U = seed_base(env)
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ADM"], "No policy")
    with db.command(U["s3"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            apps.submit_application(ctx, oid)
    assert ei.value.code == "NO_POLICY_IN_EFFECT"


def test_t25_non_student_denied(env):
    U, oid = _setup(env)
    with db.command(U["ec1"]) as ctx:
        with pytest.raises(Forbidden):
            apps.submit_application(ctx, oid)
