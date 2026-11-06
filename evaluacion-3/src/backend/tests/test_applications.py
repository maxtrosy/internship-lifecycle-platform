"""T-25: eligibility-evaluated applications (C-04/C-05)."""
from __future__ import annotations

import pytest

from app import db
from app.errors import BusinessError, Forbidden
from app.modules import authz
from app.modules.applications import service as apps
from app.modules.opportunities import service as opps
from app.modules.policies import service as policies
from tests.conftest import publish_test_opportunity, seed_base


def _setup(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [
            {"type": "CREDITS_MIN", "value": 100},
            {"type": "ACADEMIC_LEVEL_MIN", "value": 6},
        ], reason="Fixture policy for eligibility tests.")
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Alfa")
    publish_test_opportunity(env, oid)
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
    env.admin.execute("UPDATE opportunity SET state='CLOSED' WHERE id=%s", (oid,))
    with db.command(U["s1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            apps.submit_application(ctx, oid)
    assert ei.value.code == "OPPORTUNITY_NOT_PUBLISHED"


def test_t25_no_policy(env):
    U = seed_base(env)
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ADM"], "No policy")
    publish_test_opportunity(env, oid)
    with db.command(U["s3"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            apps.submit_application(ctx, oid)
    assert ei.value.code == "NO_POLICY_IN_EFFECT"


def test_t25_non_student_denied(env):
    U, oid = _setup(env)
    with db.command(U["ec1"]) as ctx:
        with pytest.raises(Forbidden):
            apps.submit_application(ctx, oid)


def test_manual_eligibility_review_is_scoped_and_blocks_employer_until_decision(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [
            {"type": "MANUAL_REVIEW", "value": True},
        ], reason="Synthetic manual-review test policy.")
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Manual review opportunity")
    publish_test_opportunity(env, oid)

    with db.command(U["s1"]) as ctx:
        submitted = apps.submit_application(ctx, oid)
    aid = submitted["application_id"]
    assert submitted["state"] == "PENDING_ELIGIBILITY_REVIEW"
    assert submitted["eligibility"]["result"] == "REQUIRES_REVIEW"
    with db.read() as cur:
        coordinator = authz.subject(cur, U["pc_sys"])
        other_coordinator = authz.subject(cur, U["pc_adm"])
        employer = authz.subject(cur, U["hm_alfa"])
        assert [row["id"] for row in apps.list_pending_eligibility(cur, coordinator)] == [aid]
        assert apps.list_pending_eligibility(cur, other_coordinator) == []
        assert apps.list_for_opportunity(cur, employer, oid) == []
    with db.command(U["pc_adm"]) as ctx:
        with pytest.raises(Forbidden):
            apps.review_eligibility(ctx, aid, "ELIGIBLE", "Cross-program attempt")
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as missing_reason:
            apps.review_eligibility(ctx, aid, "ELIGIBLE", " ")
    assert missing_reason.value.code == "ELIGIBILITY_REVIEW_RATIONALE_REQUIRED"

    with db.command(U["pc_sys"]) as ctx:
        result = apps.review_eligibility(ctx, aid, "ELIGIBLE", "Revisión sintética de demostración")
    assert result["state"] == "SUBMITTED"
    assert result["eligibility"]["manual_review"] == {
        "decision": "ELIGIBLE", "rationale": "Revisión sintética de demostración",
    }
    review_audit = env.admin.execute(
        "SELECT actor_id FROM audit_event WHERE action='application.eligibility_reviewed' AND subject_id=%s",
        (aid,),
    ).fetchone()
    assert review_audit["actor_id"] == U["pc_sys"]
    assert env.admin.execute("SELECT state, eligibility_result->>'result' AS result FROM application WHERE id=%s", (aid,)).fetchone() == {
        "state": "SUBMITTED", "result": "ELIGIBLE",
    }
    with db.read() as cur:
        employer = authz.subject(cur, U["hm_alfa"])
        assert [row["id"] for row in apps.list_for_opportunity(cur, employer, oid)] == [aid]

    notices = env.admin.execute(
        """SELECT n.recipient_id, n.category FROM user_notification n
           JOIN audit_event e ON e.id=n.source_event_id
           WHERE e.subject_type='application' AND e.subject_id=%s ORDER BY e.id, n.recipient_id""",
        (aid,),
    ).fetchall()
    assert (U["pc_sys"], "ELIGIBILITY_REVIEW") in [(n["recipient_id"], n["category"]) for n in notices]
    assert (U["s1"], "ELIGIBILITY_REVIEW") in [(n["recipient_id"], n["category"]) for n in notices]
    assert (U["hm_alfa"], "ELIGIBILITY_REVIEW") in [(n["recipient_id"], n["category"]) for n in notices]
    actions = [row["action"] for row in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='application' AND subject_id=%s ORDER BY id", (aid,)
    ).fetchall()]
    assert actions == ["application.eligibility_review_requested", "application.eligibility_reviewed"]


def test_manual_eligibility_review_rejects_invalid_decision_and_cannot_be_repeated(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(
            ctx, "ING-SIS", [{"type": "MANUAL_REVIEW", "value": True}],
            reason="Synthetic rejection-path test policy.",
        )
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Manual review rejection")
    publish_test_opportunity(env, oid)
    with db.command(U["s1"]) as ctx:
        aid = apps.submit_application(ctx, oid)["application_id"]

    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as invalid:
            apps.review_eligibility(ctx, aid, "SELECTED", "Invalid decision")
    assert invalid.value.code == "INVALID_ELIGIBILITY_DECISION"
    with db.command(U["pc_sys"]) as ctx:
        result = apps.review_eligibility(ctx, aid, "INELIGIBLE", "Requisitos no acreditados en revisión")
    assert result["state"] == "INELIGIBLE"
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as repeated:
            apps.review_eligibility(ctx, aid, "ELIGIBLE", "Intento repetido")
    assert repeated.value.code == "INVALID_TRANSITION"


def test_manual_review_policy_is_boolean_and_eligibility_can_require_review():
    profile = {"credits": None, "academic_level": None, "completed_courses": []}
    result = policies.evaluate(profile, "ING-SIS", [{"type": "MANUAL_REVIEW", "value": True}])
    assert result == {"result": "REQUIRES_REVIEW", "reasons": []}
    with pytest.raises(policies.PolicyValidationError):
        policies.validate([{"type": "MANUAL_REVIEW", "value": 1}])
    incomplete = policies.evaluate(
        {"credits": None, "academic_level": 6, "completed_courses": None},
        "ING-SIS",
        [{"type": "CREDITS_MIN", "value": 20}, {"type": "PREREQUISITE_COMPLETED", "value": ["CS101"]}],
    )
    assert incomplete == {"result": "REQUIRES_REVIEW", "reasons": []}


def test_policy_versions_require_reason_and_expose_audited_provenance(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(policies.PolicyValidationError):
            policies.create_policy_version(
                ctx, "ING-SIS", [{"type": "MANUAL_REVIEW", "value": True}], reason="  ",
            )

    reason = "Demostración sintética: revisión manual sin umbrales institucionales asumidos."
    with db.command(U["pc_sys"]) as ctx:
        version_id = policies.create_policy_version(
            ctx, "ING-SIS", [{"type": "MANUAL_REVIEW", "value": True}], reason=reason,
        )

    with db.read() as cur:
        subject = authz.subject(cur, U["pc_sys"])
        program = next(row for row in policies.policies_for_subject(cur, subject) if row["code"] == "ING-SIS")
    version = program["policies"]["ELIGIBILITY"]
    assert version["id"] == version_id
    assert version["created_reason"] == reason
    assert version["created_by_name"]

    event = env.admin.execute(
        "SELECT actor_id, after_state->>'reason' AS reason FROM audit_event "
        "WHERE action='policy.version_created' AND subject_id=%s",
        (version_id,),
    ).fetchone()
    assert event == {"actor_id": U["pc_sys"], "reason": reason}
