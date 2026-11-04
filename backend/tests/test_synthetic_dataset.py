from __future__ import annotations

from app.seed import seed
from app.synthetic_dataset import populate_synthetic_dataset


def test_populated_synthetic_dataset_is_connected_and_idempotent(env, monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.setenv("OPPORTUNITY_PUBLISHER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.setenv("PLACEMENT_FACULTY_ASSIGNER_ROLES", "PROGRAM_COORDINATOR")
    seed(env.admin.cursor())

    first = populate_synthetic_dataset(env.admin.cursor(), include_test_policy=True)
    second = populate_synthetic_dataset(env.admin.cursor(), include_test_policy=True)

    assert first == second
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

