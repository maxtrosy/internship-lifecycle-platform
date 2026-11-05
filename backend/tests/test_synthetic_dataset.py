from __future__ import annotations

import pytest

from app import db, security
from app.seed import seed
from app.synthetic_dataset import ORGANIZATIONS, populate_synthetic_dataset
from app.modules.opportunities import service as opportunities


def test_populated_synthetic_dataset_is_connected_and_idempotent(env, monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.setenv("OPPORTUNITY_PUBLISHER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.setenv("PLACEMENT_FACULTY_ASSIGNER_ROLES", "PROGRAM_COORDINATOR")
    seed(env.admin.cursor())

    issued_passwords: dict[str, str] = {}

    def password_hash_for(username: str) -> str:
        issued_passwords[username] = f"unique-test-secret-{username}"
        return security.hash_password(issued_passwords[username])

    with env.admin.transaction():
        for name in ORGANIZATIONS:
            env.admin.execute("INSERT INTO host_org(name) VALUES (%s)", (name,))
        env.admin.execute("SET LOCAL ROLE app_user")
        with db.shared_command_connection(env.admin):
            first = populate_synthetic_dataset(
                env.admin.cursor(), include_test_policy=True,
                password_hash_for=password_hash_for,
            )
            second = populate_synthetic_dataset(
                env.admin.cursor(), include_test_policy=True,
                password_hash_for=password_hash_for,
            )

    assert first == second
    assert len(issued_passwords) == 47
    assert all(username.startswith("demo_") for username in issued_passwords)
    student_hash = env.admin.execute(
        "SELECT password_hash FROM user_account WHERE username='demo_student_04'"
    ).fetchone()["password_hash"]
    assert security.verify_password(issued_passwords["demo_student_04"], student_hash)
    assert not security.verify_password(issued_passwords["demo_student_05"], student_hash)
    assert first["user_account"] >= 60
    assert first["host_org"] == 10
    assert first["opportunity"] == 16
    assert first["application"] == 24
    assert first["placement"] == 12
    assert first["document_submission"] >= 8
    assert first["placement_work_plan_item"] >= 6
    assert first["placement_progress_report"] >= 4
    assert first["placement_evaluation"] >= 3
    assert first["placement_incident"] == 2
    assert first["completion_evidence"] >= 2
    assert first["user_notification"] > 0
    assert first["placement_message"] > 0

    states = env.admin.execute(
        "SELECT state,count(*) AS n FROM placement GROUP BY state"
    ).fetchall()
    assert {row["state"]: row["n"] for row in states} == {
        "CLOSED": 1,
        "COMPLETED": 1,
        "ACTIVE": 4,
        "DOCUMENTATION_PENDING": 3,
        "PENDING_ACADEMIC_APPROVAL": 2,
        "REJECTED": 1,
    }

    # All operational records resolve to the scenario's placement and actors;
    # no standalone audit rows are manufactured by the dataset helper.
    assert env.admin.execute(
        """SELECT count(*) AS n FROM application a JOIN placement p ON p.application_id=a.id
           JOIN opportunity o ON o.id=a.opportunity_id JOIN role_assignment sr
             ON sr.user_id=a.student_id AND sr.role='STUDENT' AND sr.program_id=o.program_id"""
    ).fetchone()["n"] == 12
    assert env.admin.execute(
        """SELECT count(*) AS n FROM placement_evaluation e JOIN placement_version v
             ON v.placement_id=e.placement_id AND v.workplace_supervisor_id=e.evaluator_id"""
    ).fetchone()["n"] >= 3


def test_shared_command_batch_rolls_back_as_one_transaction(env):
    users = seed(env.admin.cursor())
    program_id = env.admin.execute(
        "SELECT id FROM academic_program WHERE code='ING-SIS'"
    ).fetchone()["id"]
    before = env.admin.execute("SELECT count(*) AS n FROM opportunity").fetchone()["n"]
    before_audit = env.admin.execute("SELECT count(*) AS n FROM audit_event").fetchone()["n"]

    with pytest.raises(RuntimeError, match="abort batch"):
        with env.admin.transaction():
            env.admin.execute("SET LOCAL ROLE app_user")
            with db.shared_command_connection(env.admin):
                with db.command(users["hm_alfa"]) as ctx:
                    opportunities.create_opportunity(
                        ctx, 1, program_id, "Atomic batch rollback",
                    )
                raise RuntimeError("abort batch")

    assert env.admin.execute("SELECT count(*) AS n FROM opportunity").fetchone()["n"] == before
    assert env.admin.execute("SELECT count(*) AS n FROM audit_event").fetchone()["n"] == before_audit

