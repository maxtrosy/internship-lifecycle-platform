"""T-28: document delivery, review/re-delivery and activation gate (Sprint 3)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import db
from app.errors import BusinessError, Forbidden
from app.main import app
from app.modules import authz
from app.modules.applications import service as apps
from app.modules.lifecycle import service as lifecycle
from app.modules.opportunities import service as opps
from app.modules.policies import service as policies
from tests.conftest import TEST_PASSWORD, seed_base


def _setup(env, kinds=("DOC_INSURANCE",)):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [{"type": "CREDITS_MIN", "value": 100}])
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Alfa")
    with db.command(U["s1"]) as ctx:
        apps.submit_application(ctx, oid)
    aid = env.admin.execute("SELECT id FROM application WHERE opportunity_id=%s", (oid,)).fetchone()["id"]
    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, {
            "workplace_supervisor_id": U["ws_alfa"],
            "start_date": "2026-11-02", "end_date": "2027-02-26",
            "location": "Site A", "responsibilities": "Synthetic",
        })
    with db.command(U["pc_sys"]) as ctx:
        lifecycle.academic_approve(ctx, pid)
    return U, pid


def _item(env, pid, kind):
    return env.admin.execute("SELECT id FROM checklist_item WHERE placement_id=%s AND kind=%s",
                             (pid, kind)).fetchone()["id"]


def _submit(ctx, pid, item, content=b"%PDF-1.7 synthetic document"):
    return lifecycle.submit_document(ctx, pid, item, "insurance.pdf", "application/pdf", content)


def test_t28_document_flow(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")

    with db.read() as cur:
        subj = authz.subject(cur, U["s1"])
        items = lifecycle.list_checklist(cur, subj, pid)
        assert [i["status"] for i in items if i["kind"] == "DOC_INSURANCE"] == ["REQUIRED"]

    with db.command(U["s1"]) as ctx:
        first = _submit(ctx, pid, item)
    assert first["revision"] == 1
    with db.command(U["legal1"]) as ctx:
        lifecycle.review_document(ctx, pid, item, "REJECTED", "La póliza está vencida.")
    with db.command(U["s1"]) as ctx:
        second = _submit(ctx, pid, item, b"%PDF-1.7 synthetic corrected document")
    assert second["revision"] == 2
    with db.command(U["legal1"]) as ctx:
        lifecycle.review_document(ctx, pid, item, "APPROVED", "Documento vigente y legible.")

    with db.read() as cur:
        subj = authz.subject(cur, U["s1"])
        status = lifecycle.activation_status(cur, subj, pid)
        assert status["ready_to_activate"] is True
        revisions = lifecycle.list_submissions(cur, subj, pid, item)
        assert [row["revision"] for row in revisions] == [2, 1]
        assert revisions[0]["decision"] == "APPROVED"
        assert revisions[0]["reason"] == "Documento vigente y legible."

    with db.command(U["ec1"]) as ctx:
        lifecycle.activate(ctx, pid)
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (pid,)).fetchone()["state"] == "ACTIVE"


def test_t28_submit_from_approved_denied(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")
    with db.command(U["s1"]) as ctx:
        _submit(ctx, pid, item)
    with db.command(U["legal1"]) as ctx:
        lifecycle.review_document(ctx, pid, item, "APPROVED", "Archivo revisado.")
    with db.command(U["s1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            _submit(ctx, pid, item)
    assert ei.value.code == "INVALID_TRANSITION"


def test_t28_non_student_cannot_submit(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")
    with db.command(U["ec1"]) as ctx:
        with pytest.raises(Forbidden):
            _submit(ctx, pid, item)


def test_t28_activation_blocked_when_pending(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")
    with db.command(U["s1"]) as ctx:
        _submit(ctx, pid, item)  # SUBMITTED, not APPROVED
    with db.command(U["ec1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            lifecycle.activate(ctx, pid)
    assert ei.value.code == "ACTIVATION_CONDITIONS_UNMET"


def test_t28_activation_policy_derives_requirements(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [{"type": "CREDITS_MIN", "value": 100}])
        policies.create_policy_version(ctx, "ING-SIS",
                                       [{"type": "REQUIRE_DOCUMENTS", "value": ["DOC_A", "DOC_B"]}],
                                       kind="ACTIVATION")
    with db.command(U["hm_alfa"]) as ctx:
        oid = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Alfa")
    with db.command(U["s1"]) as ctx:
        apps.submit_application(ctx, oid)
    aid = env.admin.execute("SELECT id FROM application WHERE opportunity_id=%s", (oid,)).fetchone()["id"]
    with db.command(U["hm_alfa"]) as ctx:
        pid = apps.select_application(ctx, aid, {"workplace_supervisor_id": U["ws_alfa"],
                                                 "start_date": "2026-11-02", "end_date": "2027-02-26",
                                                 "location": "Site A", "responsibilities": "Synthetic"})
    with db.command(U["pc_sys"]) as ctx:
        lifecycle.academic_approve(ctx, pid)  # policy is fixed when academic approval is recorded
    kinds = {r["kind"] for r in env.admin.execute(
        "SELECT kind FROM checklist_item WHERE placement_id=%s", (pid,)).fetchall()}
    assert {"DOC_A", "DOC_B"} <= kinds


def test_document_submission_requires_valid_file_and_review_reason(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")
    with db.command(U["s1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            lifecycle.submit_document(ctx, pid, item, "insurance.txt", "text/plain", b"not a document")
    assert ei.value.code == "DOCUMENT_TYPE_UNSUPPORTED"
    assert env.admin.execute("SELECT count(*) AS n FROM document_submission WHERE checklist_item_id=%s",
                             (item,)).fetchone()["n"] == 0

    with db.command(U["s1"]) as ctx:
        _submit(ctx, pid, item)
    with db.command(U["legal1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            lifecycle.review_document(ctx, pid, item, "REJECTED", "  ")
    assert ei.value.code == "DOCUMENT_REVIEW_REASON_REQUIRED"


def test_http_upload_rejects_oversized_declared_and_streamed_bodies(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")
    origin = "http://localhost:5173"

    with TestClient(app, base_url=origin) as client:
        login = client.post("/auth/login", json={"identifier": "s1", "password": TEST_PASSWORD},
                            headers={"Origin": origin})
        assert login.status_code == 200

        response = client.post(
            f"/placements/{pid}/items/{item}/submit?filename=large.pdf",
            content=b"%PDF-" + b"x" * lifecycle.MAX_DOCUMENT_BYTES,
            headers={"Origin": origin, "Content-Type": "application/pdf"},
        )
        streamed_response = client.post(
            f"/placements/{pid}/items/{item}/submit?filename=streamed-large.pdf",
            content=iter((b"%PDF-", b"x" * lifecycle.MAX_DOCUMENT_BYTES)),
            headers={"Origin": origin, "Content-Type": "application/pdf"},
        )

    assert response.status_code == 409
    assert response.json()["error"] == "DOCUMENT_TOO_LARGE"
    assert streamed_response.status_code == 409
    assert streamed_response.json()["error"] == "DOCUMENT_TOO_LARGE"
    assert env.admin.execute(
        "SELECT count(*) AS n FROM document_submission WHERE checklist_item_id=%s", (item,)
    ).fetchone()["n"] == 0
    assert env.admin.execute("SELECT status FROM checklist_item WHERE id=%s", (item,)).fetchone()["status"] == "REQUIRED"


def test_document_download_is_limited_to_student_and_legal(env):
    U, pid = _setup(env)
    item = _item(env, pid, "DOC_INSURANCE")
    with db.command(U["s1"]) as ctx:
        submission = _submit(ctx, pid, item)
    with db.read() as cur:
        legal = authz.subject(cur, U["legal1"])
        document = lifecycle.get_submission(cur, legal, pid, item, submission["id"])
        assert bytes(document["content"]).startswith(b"%PDF-")
        employer = authz.subject(cur, U["hm_alfa"])
        with pytest.raises(Forbidden):
            lifecycle.get_submission(cur, employer, pid, item, submission["id"])


def test_activation_and_completion_policies_are_pinned_to_approval(env):
    U, pid = _setup(env)
    original = env.admin.execute(
        "SELECT activation_policy_version_id, completion_policy_version_id FROM placement WHERE id=%s",
        (pid,),
    ).fetchone()

    with db.command(U["pc_sys"]) as ctx:
        policies.create_policy_version(ctx, "ING-SIS", [
            {"type": "REQUIRE_DOCUMENTS", "value": ["DOC_NEW"]},
        ], kind="ACTIVATION")
        policies.create_policy_version(ctx, "ING-SIS", [
            {"type": "FINAL_REPORT", "value": True},
            {"type": "MIN_HOURS", "value": 200},
        ], kind="COMPLETION")

    checklist_kinds = {row["kind"] for row in env.admin.execute(
        "SELECT kind FROM checklist_item WHERE placement_id=%s", (pid,)).fetchall()}
    thresholds = {row["kind"]: row["threshold"] for row in env.admin.execute(
        "SELECT kind,threshold FROM completion_requirement WHERE placement_id=%s", (pid,)).fetchall()}
    latest = env.admin.execute(
        """SELECT
             (SELECT id FROM policy_version WHERE policy_key='ACTIVATION:ING-SIS' ORDER BY version_no DESC LIMIT 1) AS activation,
             (SELECT id FROM policy_version WHERE policy_key='COMPLETION:ING-SIS' ORDER BY version_no DESC LIMIT 1) AS completion""",
    ).fetchone()
    assert "DOC_INSURANCE" in checklist_kinds and "DOC_NEW" not in checklist_kinds
    assert thresholds["MIN_HOURS"] == 100 and "FINAL_EVALUATION" in thresholds
    assert original["activation_policy_version_id"] != latest["activation"]
    assert original["completion_policy_version_id"] != latest["completion"]


def test_policy_vocabulary_is_scoped_by_kind(env):
    U = seed_base(env)
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            policies.create_policy_version(ctx, "ING-SIS", [
                {"type": "MIN_HOURS", "value": 40},
            ], kind="ACTIVATION")
    assert ei.value.code == "POLICY_INVALID"
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            policies.create_policy_version(ctx, "ING-SIS", [
                {"type": "REQUIRE_DOCUMENTS", "value": ["COND_SUPERVISOR_ASSIGNED"]},
            ], kind="ACTIVATION")
    assert ei.value.code == "POLICY_INVALID"

    with db.read() as cur:
        subj = authz.subject(cur, U["pc_sys"])
        visible = policies.policies_for_subject(cur, subj)
        assert [program["code"] for program in visible] == ["ING-SIS"]


def test_non_document_conditions_cannot_be_uploaded_or_reviewed(env):
    U, pid = _setup(env)
    item = _item(env, pid, "COND_SUPERVISOR_ASSIGNED")
    with db.command(U["s1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            _submit(ctx, pid, item)
    assert ei.value.code == "DOCUMENT_NOT_UPLOADABLE"

    with db.command(U["legal1"]) as ctx:
        with pytest.raises(BusinessError) as ei:
            lifecycle.review_document(ctx, pid, item, "REJECTED", "No es un documento.")
    assert ei.value.code == "DOCUMENT_NOT_REVIEWABLE"
