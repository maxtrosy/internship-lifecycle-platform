from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from app import db, security
from app.seed import seed
from app.synthetic_dataset import (
    ORGANIZATIONS, _ensure_completion, populate_synthetic_partial, populate_synthetic_dataset,
)
from app.errors import BusinessError, Forbidden
from app.modules.opportunities import service as opportunities

_LOADER_PATH = Path(__file__).resolve().parents[2] / "scripts" / "persist_synthetic_dataset.py"
_LOADER_SPEC = importlib.util.spec_from_file_location("persist_synthetic_dataset_test", _LOADER_PATH)
_LOADER = importlib.util.module_from_spec(_LOADER_SPEC)
_LOADER_SPEC.loader.exec_module(_LOADER)


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
                allow_test_only_synthetic_evidence=True,
            )
            second = populate_synthetic_dataset(
                env.admin.cursor(), include_test_policy=True,
                password_hash_for=password_hash_for,
                allow_test_only_synthetic_evidence=True,
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


def _configure_partial_bootstrap_role(env):
    if not env.admin.execute(
        "SELECT 1 FROM pg_roles WHERE rolname='app_bootstrap'"
    ).fetchone():
        env.admin.execute("CREATE ROLE app_bootstrap NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS")
    grants = (
        "GRANT SELECT (id,code,name) ON academic_program TO app_bootstrap",
        "GRANT SELECT (id,name), INSERT (name) ON host_org TO app_bootstrap",
        "GRANT SELECT (id,username,email,display_name,is_active,credits,academic_level,completed_courses), "
        "INSERT (username,email,password_hash,is_active,display_name,credits,academic_level,completed_courses) "
        "ON user_account TO app_bootstrap",
        "GRANT SELECT (id,user_id,role,program_id,host_org_id), "
        "INSERT (user_id,role,program_id,host_org_id) ON role_assignment TO app_bootstrap",
        "GRANT SELECT ON opportunity TO app_bootstrap",
        "GRANT INSERT (host_org_id,program_id,title,state), UPDATE (state) ON opportunity TO app_bootstrap",
        "GRANT INSERT (actor_id,action,subject_type,subject_id,before_state,after_state,correlation_id), "
        "SELECT (id,occurred_at) ON audit_event TO app_bootstrap",
        "GRANT SELECT (recipient_id,source_event_id), "
        "INSERT (recipient_id,source_event_id,category,placement_id,opportunity_id,created_at) "
        "ON user_notification TO app_bootstrap",
        "GRANT USAGE ON SEQUENCE host_org_id_seq,user_account_id_seq,role_assignment_id_seq, "
        "opportunity_id_seq,audit_event_id_seq,user_notification_id_seq TO app_bootstrap",
    )
    for statement in grants:
        env.admin.execute(statement)


def _run_partial_as_bootstrap(env, password_hash_for):
    with env.admin.transaction():
        env.admin.execute("SET LOCAL ROLE app_bootstrap")
        with db.shared_command_connection(env.admin, required_role="app_bootstrap"):
            return populate_synthetic_partial(env.admin.cursor(), password_hash_for=password_hash_for)


def test_partial_dataset_is_idempotent_and_only_creates_pending_catalog(env, monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.delenv("OPPORTUNITY_PUBLISHER_ROLES", raising=False)
    users = seed(env.admin.cursor())
    _configure_partial_bootstrap_role(env)
    password_hashes = {}
    plaintexts = {}

    def unique_hash(username):
        password = f"isolated-partial-secret::{username}"
        plaintexts[username] = password
        password_hashes[username] = security.hash_password(password)
        return password_hashes[username]

    first = _run_partial_as_bootstrap(env, unique_hash)
    second = _run_partial_as_bootstrap(env, unique_hash)

    assert first["inserted"] == {
        "host_org": 8, "user_account": 47, "role_assignment": 47,
        "opportunity": 16, "audit_event": 24,
    }
    assert second["inserted"] == {table: 0 for table in first["inserted"]}
    assert first["omitted"]["applications_by_partial_scope"] == 24
    assert first["omitted"]["placements_by_partial_scope"] == 12
    assert first["omitted"]["published_opportunities_by_partial_scope"] == 12
    assert first["omitted"]["policy_writes"] == 0
    assert first["opportunity_states"] == {"DRAFT": 8, "IN_REVIEW": 8}
    assert first["applications_created"] == first["placements_created"] == first["policies_created"] == 0
    assert len(password_hashes) == 47 and len(set(password_hashes.values())) == 47
    assert len(plaintexts) == len(set(plaintexts.values())) == 47
    assert env.admin.execute("SELECT count(*) AS n FROM application").fetchone()["n"] == 0
    assert env.admin.execute("SELECT count(*) AS n FROM placement").fetchone()["n"] == 0
    notice_rows = env.admin.execute(
        "SELECT category,count(*) AS n FROM user_notification GROUP BY category"
    ).fetchall()
    assert [(row["category"], row["n"]) for row in notice_rows] == [("OPPORTUNITY_REVIEW", 8)]
    assert env.admin.execute(
        "SELECT count(DISTINCT recipient_id) AS n FROM user_notification"
    ).fetchone()["n"] == 1
    assert env.admin.execute(
        "SELECT recipient_id FROM user_notification LIMIT 1"
    ).fetchone()["recipient_id"] == users["ec1"]
    assert env.admin.execute(
        "SELECT count(*) AS n FROM policy_version WHERE policy_key LIKE 'ELIGIBILITY:%'"
    ).fetchone()["n"] == 0
    assert env.admin.execute(
        "SELECT count(*) AS n FROM opportunity WHERE state NOT IN ('DRAFT','IN_REVIEW')"
    ).fetchone()["n"] == 0
    assert env.admin.execute(
        "SELECT count(*) AS n FROM host_org"
    ).fetchone()["n"] == 10
    assert env.admin.execute(
        "SELECT count(*) AS n FROM user_account WHERE username LIKE 'demo_%'"
    ).fetchone()["n"] == 47
    assert not env.admin.execute(
        "SELECT has_table_privilege('app_bootstrap','public.application','INSERT') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT has_table_privilege('app_bootstrap','public.placement','INSERT') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT has_table_privilege('app_bootstrap','public.policy_version','INSERT') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT has_table_privilege('app_bootstrap','public.academic_program','INSERT') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT has_table_privilege('app_bootstrap','public.host_org','DELETE') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT has_schema_privilege('app_bootstrap','public','CREATE') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT pg_has_role('app_bootstrap','app_user','MEMBER') AS allowed"
    ).fetchone()["allowed"]
    assert not env.admin.execute(
        "SELECT has_column_privilege('app_bootstrap','public.user_account','password_hash','SELECT') AS allowed"
    ).fetchone()["allowed"]
    with env.admin.transaction():
        env.admin.execute("SET LOCAL ROLE app_bootstrap")
        assert _LOADER._unexpected_partial_privileges(env.admin) == []


def test_partial_dataset_preserves_existing_matching_account(env, monkeypatch):
    monkeypatch.delenv("OPPORTUNITY_REVIEWER_ROLES", raising=False)
    monkeypatch.delenv("OPPORTUNITY_PUBLISHER_ROLES", raising=False)
    users = seed(env.admin.cursor())
    _configure_partial_bootstrap_role(env)
    program_id = users["programs"]["ING-SIS"]
    original_hash = security.hash_password("pre-existing-account-password")
    account_id = env.admin.execute(
        """INSERT INTO user_account(username,email,password_hash,is_active,display_name,credits,
                                    academic_level,completed_courses)
           VALUES ('demo_student_04','demo_student_04@horizon.example.test',%s,true,
                   'Estudiante Demo 04',78,5,ARRAY['SYS-101']) RETURNING id""",
        (original_hash,),
    ).fetchone()["id"]
    env.admin.execute(
        "INSERT INTO role_assignment(user_id,role,program_id) VALUES (%s,'STUDENT',%s)",
        (account_id, program_id),
    )

    def unique_hash(username):
        if username == "demo_student_04":
            raise AssertionError("existing account credential must not be read or replaced")
        return security.hash_password(f"isolated-preservation-secret::{username}")

    report = _run_partial_as_bootstrap(env, unique_hash)
    assert report["inserted"]["user_account"] == 46
    assert report["omitted"]["accounts_reused"] == 1
    assert env.admin.execute(
        "SELECT password_hash FROM user_account WHERE id=%s", (account_id,)
    ).fetchone()["password_hash"] == original_hash


def test_partial_dataset_rolls_back_everything_on_domain_error(env, monkeypatch):
    monkeypatch.delenv("OPPORTUNITY_REVIEWER_ROLES", raising=False)
    monkeypatch.delenv("OPPORTUNITY_PUBLISHER_ROLES", raising=False)
    seed(env.admin.cursor())
    _configure_partial_bootstrap_role(env)
    original_submit = opportunities.submit_for_review
    calls = 0

    def fail_second_submit(ctx, opportunity_id):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected isolated failure")
        return original_submit(ctx, opportunity_id)

    monkeypatch.setattr(opportunities, "submit_for_review", fail_second_submit)
    baseline = {
        table: env.admin.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
        for table in ("host_org", "user_account", "role_assignment", "opportunity", "audit_event",
                      "user_notification", "application", "placement", "policy_version")
    }
    with pytest.raises(RuntimeError, match="injected isolated failure"):
        with env.admin.transaction():
            env.admin.execute("SET LOCAL ROLE app_bootstrap")
            with db.shared_command_connection(env.admin, required_role="app_bootstrap"):
                populate_synthetic_partial(
                    env.admin.cursor(),
                    password_hash_for=lambda username: security.hash_password(f"rollback-secret::{username}"),
                )

    for table, before in baseline.items():
        assert env.admin.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"] == before


def test_partial_acl_preflight_rejects_unexpected_effective_grants(env):
    seed(env.admin.cursor())
    _configure_partial_bootstrap_role(env)
    env.admin.execute("GRANT SELECT ON application TO app_bootstrap")
    try:
        with env.admin.transaction():
            env.admin.execute("SET LOCAL ROLE app_bootstrap")
            blockers = _LOADER._unexpected_partial_privileges(env.admin)
        assert any("Unexpected effective SELECT on public.application.id" in item for item in blockers)
    finally:
        env.admin.execute("REVOKE SELECT ON application FROM app_bootstrap")


def test_opportunity_publication_requires_configured_related_authority(env, monkeypatch):
    users = seed(env.admin.cursor())
    org_id = env.admin.execute(
        "SELECT host_org_id AS id FROM role_assignment WHERE user_id=%s AND role='HOST_ORG_MEMBER'",
        (users["hm_alfa"],),
    ).fetchone()["id"]
    program_id = users["programs"]["ING-SIS"]
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.delenv("OPPORTUNITY_PUBLISHER_ROLES", raising=False)
    with db.command(users["hm_alfa"]) as ctx:
        opportunity_id = opportunities.create_opportunity(ctx, org_id, program_id, "Authority check")
    with db.command(users["hm_alfa"]) as ctx:
        opportunities.submit_for_review(ctx, opportunity_id)
    with db.command(users["ec1"]) as ctx:
        opportunities.approve_for_publication(ctx, opportunity_id)

    with pytest.raises(BusinessError) as unconfigured:
        with db.command(users["ec1"]) as ctx:
            opportunities.publish_opportunity(ctx, opportunity_id)
    assert unconfigured.value.code == "OPPORTUNITY_PUBLISH_AUTHORITY_UNCONFIGURED"

    monkeypatch.setenv("OPPORTUNITY_PUBLISHER_ROLES", "EXPERIENTIAL_COORDINATOR")
    with pytest.raises(Forbidden):
        with db.command(users["hm_alfa"]) as ctx:
            opportunities.publish_opportunity(ctx, opportunity_id)
    assert env.admin.execute(
        "SELECT state FROM opportunity WHERE id=%s", (opportunity_id,)
    ).fetchone()["state"] == "APPROVED"


def test_production_completion_loader_does_not_invent_evidence_or_hours():
    class NoSQLAllowed:
        def execute(self, *args, **kwargs):
            raise AssertionError("production completion path must not fabricate evidence or hours")

    _ensure_completion(
        NoSQLAllowed(), placement_id=1, student_id=2, supervisor_id=3,
        coordinator_id=4, ec_id=5, allow_test_only_synthetic_evidence=False, close=True,
    )


def test_full_loader_without_test_evidence_opt_in_does_not_create_hours(env, monkeypatch):
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.setenv("OPPORTUNITY_PUBLISHER_ROLES", "EXPERIENTIAL_COORDINATOR")
    monkeypatch.delenv("PLACEMENT_FACULTY_ASSIGNER_ROLES", raising=False)
    seed(env.admin.cursor())
    for name in ORGANIZATIONS:
        env.admin.execute("INSERT INTO host_org(name) VALUES (%s)", (name,))

    with env.admin.transaction():
        env.admin.execute("SET LOCAL ROLE app_user")
        with db.shared_command_connection(env.admin):
            populate_synthetic_dataset(
                env.admin.cursor(), include_test_policy=True,
                password_hash_for=lambda username: security.hash_password(f"isolated-no-hours::{username}"),
            )

    assert env.admin.execute("SELECT count(*) AS n FROM progress_entry").fetchone()["n"] == 0
    assert env.admin.execute("SELECT count(*) AS n FROM completion_evidence").fetchone()["n"] == 0
    assert env.admin.execute(
        "SELECT count(*) AS n FROM placement WHERE state IN ('COMPLETED','CLOSED')"
    ).fetchone()["n"] == 0

