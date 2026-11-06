"""Configurable faculty assignment authority with append-only relationship history."""
from __future__ import annotations

import pytest
import psycopg

from app import db
from app.errors import BusinessError, Forbidden
from app.modules.authz import service as authz
from app.modules.lifecycle import service as lifecycle
from tests.conftest import make_opportunity, make_placement, seed_base


def test_assignment_history_is_persisted_and_scoped_to_configured_program(env, monkeypatch):
    users = seed_base(env)
    opportunity_id = make_opportunity(env, 1, users["P"]["ING-SIS"])
    placement_id = make_placement(env, users["s1"], opportunity_id)
    monkeypatch.setenv("PLACEMENT_FACULTY_ASSIGNER_ROLES", "PROGRAM_COORDINATOR")

    with db.read() as cur:
        options = lifecycle.faculty_assignment_options(cur, authz.subject(cur, users["pc_sys"]), placement_id)
    assert {row["id"] for row in options} == {users["f1"], users["dual1"]}

    with db.command(users["pc_adm"]) as ctx:
        with pytest.raises(Forbidden):
            lifecycle.assign_faculty_supervisor(ctx, placement_id, users["f1"])
    with db.command(users["hm_alfa"]) as ctx:
        with pytest.raises(Forbidden):
            lifecycle.assign_faculty_supervisor(ctx, placement_id, users["f1"])
    with db.command(users["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as error:
            lifecycle.assign_faculty_supervisor(ctx, placement_id, users["ws_alfa"])
    assert error.value.code == "FACULTY_SUPERVISOR_INVALID"

    with db.command(users["pc_sys"]) as ctx:
        lifecycle.assign_faculty_supervisor(ctx, placement_id, users["f1"])
    with pytest.raises(BusinessError) as error:
        with db.command(users["pc_sys"]) as ctx:
            lifecycle.assign_faculty_supervisor(ctx, placement_id, users["f1"])
    assert error.value.code == "FACULTY_ALREADY_ASSIGNED"
    with db.command(users["pc_sys"]) as ctx:
        lifecycle.unassign_faculty_supervisor(ctx, placement_id, users["f1"])

    with db.read() as cur:
        dossier = lifecycle.get_dossier(cur, authz.subject(cur, users["s1"]), placement_id)
        assert dossier["responsibles"]["faculty_supervisors"] == []
        history = dossier["responsibles"]["faculty_assignment_history"]
        assert [row["action"] for row in history] == ["ASSIGNED", "UNASSIGNED"]
        assert [row["actor_name"] for row in history] == ["Coord Sys", "Coord Sys"]
        assert all(row["faculty_name"] == "Faculty Sup 1" for row in history)
        external = lifecycle.get_dossier(cur, authz.subject(cur, users["hm_alfa"]), placement_id)
        assert external["responsibles"]["faculty_assignment_history"] == []
        assert external["capabilities"]["manage_faculty_assignments"] is False


def test_faculty_assignment_mutations_are_disabled_without_institution_configuration(env, monkeypatch):
    users = seed_base(env)
    opportunity_id = make_opportunity(env, 1, users["P"]["ING-SIS"])
    placement_id = make_placement(env, users["s1"], opportunity_id)
    monkeypatch.delenv("PLACEMENT_FACULTY_ASSIGNER_ROLES", raising=False)

    with db.command(users["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as error:
            lifecycle.assign_faculty_supervisor(ctx, placement_id, users["f1"])
    assert error.value.code == "FACULTY_ASSIGNMENT_AUTHORITY_UNCONFIGURED"
    with db.read() as cur:
        dossier = lifecycle.get_dossier(cur, authz.subject(cur, users["pc_sys"]), placement_id)
    assert dossier["capabilities"]["manage_faculty_assignments"] is False


def test_faculty_assignment_cannot_change_after_completion_or_close(env, monkeypatch):
    users = seed_base(env)
    opportunity_id = make_opportunity(env, 1, users["P"]["ING-SIS"])
    placement_id = make_placement(env, users["s1"], opportunity_id, faculty_id=users["f1"])
    with db.command(users["pc_sys"]) as ctx:
        lifecycle.academic_reject(ctx, placement_id, "Synthetic terminal-state fixture")
    monkeypatch.setenv("PLACEMENT_FACULTY_ASSIGNER_ROLES", "PROGRAM_COORDINATOR")

    with db.command(users["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as error:
            lifecycle.assign_faculty_supervisor(ctx, placement_id, users["dual1"])
    assert error.value.code == "FACULTY_ASSIGNMENT_PLACEMENT_TERMINAL"

    with db.command(users["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as error:
            lifecycle.unassign_faculty_supervisor(ctx, placement_id, users["f1"])
    assert error.value.code == "FACULTY_ASSIGNMENT_PLACEMENT_TERMINAL"

    with pytest.raises(psycopg.errors.RaiseException):
        with db.command(users["pc_sys"]) as ctx:
            ctx.execute(
                "INSERT INTO supervisor_assignment(placement_id,user_id,kind) VALUES (%s,%s,'FACULTY')",
                (placement_id, users["dual1"]),
            )
    with pytest.raises(psycopg.errors.RaiseException):
        with db.command(users["pc_sys"]) as ctx:
            ctx.execute(
                "DELETE FROM supervisor_assignment WHERE placement_id=%s AND user_id=%s AND kind='FACULTY'",
                (placement_id, users["f1"]),
            )
