"""T-26/T-27: employer selection + academic approval/rejection (Sprint 2)."""
from __future__ import annotations

import datetime as dt

import pytest

from app import db
from app.errors import BusinessError, Forbidden
from app.modules import authz
from app.modules.applications import service as apps
from app.modules.lifecycle import service as lifecycle
from app.modules.opportunities import service as opps
from app.modules.policies import service as policies
from tests.conftest import seed_base


def _setup(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [{"type": "CREDITS_MIN", "value": 100}])
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Alfa")
    with db.command(U["s1"]) as ctx:
        apps.submit_application(ctx, oid)
    return U, oid


def _details():
    return {
        "start_date": dt.date(2026, 11, 2),
        "end_date": dt.date(2027, 2, 26),
        "location": "Site A",
        "responsibilities": "Synthetic",
    }


def _aid(env, oid):
    return env.admin.execute(
        "SELECT id FROM application WHERE opportunity_id=%s", (oid,)).fetchone()["id"]


def test_t26_employer_lists_and_selects(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.read() as cur:
        subj = authz.subject(cur, U["hm_alfa"])
        rows = apps.list_for_opportunity(cur, subj, oid)
        assert len(rows) == 1 and rows[0]["id"] == aid
        assert "inputs" not in rows[0]["eligibility_result"]

    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, _details())
    app = env.admin.execute("SELECT state FROM application WHERE id=%s", (aid,)).fetchone()
    assert app["state"] == "SELECTED"
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (pid,)).fetchone()["state"] == "PENDING_ACADEMIC_APPROVAL"
    actions = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='application' AND subject_id=%s", (aid,)).fetchall()]
    assert "application.selected" in actions


def test_t26_unrelated_employer_denied(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.read() as cur:
        subj = authz.subject(cur, U["hm_beta"])
        with pytest.raises(Forbidden):
            apps.list_for_opportunity(cur, subj, oid)
    with db.command(U["hm_beta"]) as ctx:
        with pytest.raises(Forbidden):
            apps.select_application(ctx, aid, _details())


def test_t26_repeated_selection_rejected(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.command(U["hm_alfa"]) as ctx:
        apps.select_application(ctx, aid, _details())
    with db.command(U["hm_alfa"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            apps.select_application(ctx, aid, _details())
    assert ei.value.code == "INVALID_TRANSITION"


def test_t27_academic_approve(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, _details())
    with db.read() as cur:
        subj = authz.subject(cur, U["pc_sys"])
        assert [r["id"] for r in lifecycle.list_pending_academic(cur, subj)] == [pid]
    with db.command(U["pc_sys"]) as ctx:
        lifecycle.academic_approve(ctx, pid)
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (pid,)).fetchone()["state"] == "DOCUMENTATION_PENDING"
    actions = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='placement' AND subject_id=%s", (pid,)).fetchall()]
    assert "placement.academic_approved" in actions


def test_t27_academic_reject(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, _details())
    with db.command(U["pc_sys"]) as ctx:
        lifecycle.academic_reject(ctx, pid, "no cumple requisitos")
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (pid,)).fetchone()["state"] == "REJECTED"
    assert env.admin.execute("SELECT state FROM application WHERE id=%s", (aid,)).fetchone()["state"] == "REJECTED"
    actions = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='placement' AND subject_id=%s", (pid,)).fetchall()]
    assert "placement.academic_rejected" in actions


def test_t27_unauthorized_academic_denied(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, _details())
    for actor in ("pc_adm", "s1", "hm_alfa"):
        with db.command(U[actor]) as ctx:
            with pytest.raises(Forbidden):
                lifecycle.academic_approve(ctx, pid)


def test_t27_student_sees_state(env):
    U, oid = _setup(env)
    aid = _aid(env, oid)
    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, _details())
    with db.read() as cur:
        subj = authz.subject(cur, U["s1"])
        rows = apps.list_my_applications(cur, subj)
        assert rows[0]["state"] == "SELECTED"
        assert rows[0]["placement_id"] == pid
        assert rows[0]["placement_state"] == "PENDING_ACADEMIC_APPROVAL"
