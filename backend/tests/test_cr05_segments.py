"""CR-05 (Evaluación 4): rotational placements and mid-placement transfers.

Each test names the CR-05 business rule(s) and the mandatory scenario it covers
(numbering follows the Evaluación 4 mission list, see
evaluacion-4/docs/diagramas-y-trazabilidad/traceability-matrix.md).
All data is synthetic; the database is the disposable pgserver of conftest.
"""
from __future__ import annotations

import datetime as dt

import psycopg
import pytest
from fastapi.testclient import TestClient

from app import db
from app.errors import BusinessError, Forbidden, NotFound
from app.main import app
from app.modules.authz import service as authz
from app.modules.lifecycle import segments as sg
from app.modules.lifecycle import service as lc
from app.modules.reports import service as reports
from tests.conftest import TEST_PASSWORD, make_active, make_opportunity, race, seed_base

TODAY = dt.date.today()
ORIGIN = "http://localhost:5173"


def cmd(actor_id, fn, *args, **kwargs):
    with db.command(actor_id) as ctx:
        return fn(ctx, *args, **kwargs)


def read(actor_id, fn, *args, **kwargs):
    with db.read() as cur:
        subj = authz.subject(cur, actor_id)
        return fn(cur, subj, *args, **kwargs)


def seg_data(org, supervisor, start=None, end=None, **extra):
    start = start or TODAY
    data = {"host_org_id": org, "unit": "Unidad sintética", "workplace_supervisor_id": supervisor,
            "start_date": start, "end_date": end or start + dt.timedelta(days=60), "modality": "HYBRID",
            "responsibilities": "Responsabilidades sintéticas de la rotación", "expected_hours": 60}
    data.update(extra)
    return data


def segments_of(env, pid):
    return env.admin.execute(
        "SELECT * FROM placement_segment WHERE placement_id=%s ORDER BY sequence_no", (pid,)
    ).fetchall()


def accepted(env, pid):
    return float(env.admin.execute("SELECT placement_accepted_hours(%s) AS h", (pid,)).fetchone()["h"])


def entry_ids(env, pid, segment_id=None):
    sql = "SELECT id FROM progress_entry WHERE placement_id=%s"
    args = [pid]
    if segment_id is not None:
        sql += " AND segment_id=%s"
        args.append(segment_id)
    return [r["id"] for r in env.admin.execute(sql + " ORDER BY id", args).fetchall()]


def accept_all(env, U, pid, reviewer="pc_sys"):
    for row in env.admin.execute(
        """SELECT pe.id FROM progress_entry pe WHERE pe.placement_id=%s AND NOT EXISTS
             (SELECT 1 FROM progress_entry_review r WHERE r.entry_id=pe.id) ORDER BY pe.id""", (pid,),
    ).fetchall():
        cmd(U[reviewer], sg.review_hours, pid, row["id"], decision="ACCEPTED",
            accepted_hours=None, reason_code=None, reason=None)


def confirm_doc_conditions(env, U, pid, sid):
    for cond in env.admin.execute(
        "SELECT id FROM placement_segment_condition WHERE segment_id=%s AND status='REQUIRED'", (sid,),
    ).fetchall():
        cmd(U["legal1"], sg.confirm_condition, pid, sid, cond["id"], "Póliza sintética POL-0001")


@pytest.fixture
def world(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"])
    pid = make_active(env, U, "s1", opp)
    return env, U, pid


def _final_report(U, pid):
    cmd(U["s1"], lc.submit_completion_evidence, pid, "FINAL_REPORT", "final.pdf",
        "application/pdf", b"%PDF-1.7 synthetic final report")


# ----------------------------------------------------------------- scenario 1

def test_s01_single_segment_practice_keeps_e3_flow(world):
    """BR-01/BR-10: activation creates segment 1 from the approved version and the
    E3 single-segment completion flow still works (no artificial rotation)."""
    env, U, pid = world
    rows = segments_of(env, pid)
    assert len(rows) == 1
    seg = rows[0]
    assert (seg["sequence_no"], seg["origin"], seg["status"]) == (1, "PLACEMENT_ACTIVATION", "ACTIVE")
    assert seg["workplace_supervisor_id"] == U["ws_alfa"] and seg["host_org_id"] == 1

    result = cmd(U["s1"], lc.record_hours, pid, 100)
    assert result["segment_id"] == seg["id"]
    cmd(U["ws_alfa"], lc.create_evaluation, pid, "FINAL", "Evaluación final sintética.")
    _final_report(U, pid)
    accept_all(env, U, pid)
    cmd(U["pc_sys"], lc.confirm_completion, pid)
    cmd(U["ec1"], lc.close_placement, pid)
    assert segments_of(env, pid)[0]["status"] == "COMPLETED"
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (pid,)).fetchone()["state"] == "CLOSED"


# ------------------------------------------------- scenarios 2, 3, 4, 7, 8, 9, 13, 14

def test_s02_multi_segment_rotation_end_to_end(world):
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    cmd(U["s1"], lc.record_hours, pid, 60)
    cmd(U["ws_alfa"], lc.create_evaluation, pid, "FINAL", "Cierre de la rotación 1.")

    # Scenario 2: a second rotation inside the SAME academic placement.
    created = cmd(U["ec1"], sg.create_segment, pid, seg_data(2, U["ws_beta"]))
    seg2 = created["segment_id"]
    assert created["sequence_no"] == 2 and created["status"] == "PLANNED"
    conditions = {c["kind"]: c["status"] for c in env.admin.execute(
        "SELECT kind,status FROM placement_segment_condition WHERE segment_id=%s", (seg2,)).fetchall()}
    assert conditions == {"DOC_INSURANCE": "REQUIRED", "SUPERVISOR_ASSIGNED": "SATISFIED"}

    # Scenario 3: no activation without enablement conditions (service + DB).
    cmd(U["ec1"], sg.complete_segment, pid, seg1)
    with pytest.raises(BusinessError) as unmet:
        cmd(U["ec1"], sg.activate_segment, pid, seg2)
    assert unmet.value.code == "SEGMENT_CONDITIONS_UNMET"
    with pytest.raises(psycopg.errors.RaiseException, match="condition"):
        env.admin.execute(
            "UPDATE placement_segment SET status='ACTIVE', activated_at=now() WHERE id=%s", (seg2,))

    # Scenario 4: completing segment 1 did not activate segment 2.
    assert [s["status"] for s in segments_of(env, pid)] == ["COMPLETED", "PLANNED"]
    with pytest.raises(BusinessError) as no_active:
        cmd(U["s1"], lc.record_hours, pid, 5)
    assert no_active.value.code == "NO_ACTIVE_SEGMENT"

    confirm_doc_conditions(env, U, pid, seg2)
    cmd(U["ec1"], sg.activate_segment, pid, seg2)
    assert [s["status"] for s in segments_of(env, pid)] == ["COMPLETED", "ACTIVE"]

    # Scenario 7: the previous supervisor has no access to the new segment.
    with pytest.raises(NotFound):
        cmd(U["ws_alfa"], lc.create_evaluation, pid, "MIDTERM", "No debe persistirse.")
    with pytest.raises(NotFound):
        read(U["ws_alfa"], lc.get_dossier, pid)
    cmd(U["s1"], lc.record_hours, pid, 50)
    cmd(U["ws_beta"], lc.create_evaluation, pid, "FINAL", "Cierre de la rotación 2.")
    # ...and the new supervisor sees only the records of their own segment.
    beta_evals = read(U["ws_beta"], lc.list_evaluations, pid)
    assert {e["segment_id"] for e in beta_evals} == {seg2}

    # Scenario 8: earlier evaluations stay attached to segment 1 for authorized internal readers.
    internal = read(U["pc_sys"], lc.list_evaluations, pid)
    assert {e["segment_id"] for e in internal} == {seg1, seg2}
    assert {e["segment_id"] for e in read(U["s1"], lc.list_evaluations, pid)} == {seg1, seg2}

    # Scenario 9: accepted hours of every recognized segment are consolidated.
    _final_report(U, pid)
    accept_all(env, U, pid)
    assert accepted(env, pid) == 110.0
    summary = read(U["pc_sys"], lambda cur, subj, p: sg.hours_summary(cur, p), pid)
    assert float(summary["accepted_total"]) == 110.0
    assert [float(s["accepted"]) for s in summary["segments"]] == [60.0, 50.0]

    # Scenario 14: closure blocked while a segment is still open.
    with pytest.raises(BusinessError) as open_segment:
        cmd(U["pc_sys"], lc.confirm_completion, pid)
    assert open_segment.value.code == "SEGMENT_REQUIREMENTS_PENDING"
    assert "SEGMENTS_OPEN" in open_segment.value.detail
    cmd(U["ec1"], sg.complete_segment, pid, seg2)

    # Scenario 14 (cont.): multi-segment practice needs the combined academic review.
    with pytest.raises(BusinessError) as review_missing:
        cmd(U["pc_sys"], lc.confirm_completion, pid)
    assert review_missing.value.detail == ["COMBINED_EXPERIENCE_REVIEW"]
    with pytest.raises(psycopg.errors.RaiseException, match="combined"):
        env.admin.execute("UPDATE placement SET state='COMPLETED' WHERE id=%s", (pid,))
    with pytest.raises(Forbidden):
        cmd(U["pc_adm"], sg.record_experience_review, pid, "APPROVED", "Otro programa.")
    cmd(U["pc_sys"], sg.record_experience_review, pid, "APPROVED",
        "La experiencia combinada cumple los resultados de aprendizaje (sintético).")
    cmd(U["pc_sys"], lc.confirm_completion, pid)
    cmd(U["ec1"], lc.close_placement, pid)
    actions = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='placement' AND subject_id=%s ORDER BY id",
        (pid,)).fetchall()]
    for action in ("segment.planned", "segment.condition_satisfied", "segment.activated",
                   "segment.completed", "progress.hours_reviewed", "placement.experience_reviewed"):
        assert action in actions


def test_s13_closure_blocked_by_pending_segment_evaluation(world):
    """BR-07 scenario 13: a segment cannot be completed (nor the practice closed)
    while its final evaluation is pending, even if hours are enough."""
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    cmd(U["s1"], lc.record_hours, pid, 120)
    accept_all(env, U, pid)
    _final_report(U, pid)
    with pytest.raises(BusinessError) as missing:
        cmd(U["ec1"], sg.complete_segment, pid, seg1)
    assert missing.value.code == "SEGMENT_FINAL_EVALUATION_MISSING"
    with pytest.raises(BusinessError) as gate:
        cmd(U["pc_sys"], lc.confirm_completion, pid)
    assert gate.value.code == "COMPLETION_EVIDENCE_MISSING"
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute(
            "UPDATE placement_segment SET status='COMPLETED', ended_at=now(), ended_on=%s WHERE id=%s",
            (TODAY, seg1))


# ----------------------------------------------------------- scenarios 5, 6, 15

def test_s05_transfer_preserves_origin_records_and_registers_decision(world):
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    cmd(U["s1"], lc.record_hours, pid, 30)
    cmd(U["ws_alfa"], lc.create_evaluation, pid, "MIDTERM", "Avance antes de la transferencia.")
    cmd(U["s1"], lc.create_incident, pid, "CHANGE", "Cambio de unidad", "La unidad cierra el proyecto.")
    accept_all(env, U, pid)
    before = env.admin.execute(
        "SELECT id, hours, segment_id FROM progress_entry WHERE placement_id=%s ORDER BY id", (pid,)).fetchall()

    result = cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY,
                 reason_shared="Reasignación por cierre del proyecto (sintético)",
                 reason_internal="Detalle confidencial sintético",
                 prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED",
                 destination=seg_data(2, U["ws_beta"]))
    rows = segments_of(env, pid)
    assert [(s["status"], s["origin"]) for s in rows] == [("TRANSFERRED", "PLACEMENT_ACTIVATION"),
                                                           ("PLANNED", "TRANSFER")]
    assert rows[0]["ended_on"] == TODAY and rows[1]["id"] == result["to_segment_id"]
    # Scenario 5: records of the origin segment are untouched.
    assert env.admin.execute(
        "SELECT id, hours, segment_id FROM progress_entry WHERE placement_id=%s ORDER BY id", (pid,)
    ).fetchall() == before
    assert env.admin.execute("SELECT segment_id FROM placement_evaluation WHERE placement_id=%s",
                             (pid,)).fetchone()["segment_id"] == seg1
    assert env.admin.execute("SELECT segment_id FROM placement_incident WHERE placement_id=%s",
                             (pid,)).fetchone()["segment_id"] == seg1
    assert accepted(env, pid) == 30.0

    # Scenario 6: date, reason, origin, destination, treatment and approver are recorded.
    record = env.admin.execute("SELECT * FROM placement_transfer WHERE placement_id=%s", (pid,)).fetchone()
    assert (record["from_segment_id"], record["to_segment_id"]) == (seg1, result["to_segment_id"])
    assert record["effective_date"] == TODAY and record["approved_by"] == U["ec1"]
    assert record["prior_work_treatment"] == "ACCEPTED_HOURS_RECOGNIZED"
    with pytest.raises(psycopg.errors.RaiseException, match="immutable|append-only"):
        env.admin.execute("UPDATE placement_transfer SET reason_shared='x' WHERE id=%s", (record["id"],))
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE placement_segment SET responsibilities='x' WHERE id=%s", (seg1,))
    # Destination still needs its own enablement (BR-02).
    with pytest.raises(BusinessError) as unmet:
        cmd(U["ec1"], sg.activate_segment, pid, result["to_segment_id"])
    assert unmet.value.code == "SEGMENT_CONDITIONS_UNMET"

    # Scenario 15: the confidential reason is hidden from student and externals,
    # visible to authorized internal roles, and never copied into the audit log.
    confirm_doc_conditions(env, U, pid, result["to_segment_id"])
    cmd(U["ec1"], sg.activate_segment, pid, result["to_segment_id"])
    for viewer in ("s1", "ws_beta"):
        transfers = read(U[viewer], sg.list_transfers, pid)
        assert transfers and all("reason_internal" not in t for t in transfers)
        assert all("end_reason_internal" not in s for s in read(U[viewer], sg.list_segments, pid))
    assert read(U["pc_sys"], sg.list_transfers, pid)[0]["reason_internal"] == "Detalle confidencial sintético"
    assert read(U["ec1"], sg.list_segments, pid)[0]["end_reason_internal"] == "Detalle confidencial sintético"
    audit_text = " ".join(str(r["after_state"]) for r in env.admin.execute(
        "SELECT after_state FROM audit_event WHERE subject_id=%s", (pid,)).fetchall())
    assert "confidencial" not in audit_text
    # The new supervisor does not see the origin segment or its records.
    assert [s["sequence_no"] for s in read(U["ws_beta"], sg.list_segments, pid)] == [2]
    assert read(U["ws_beta"], lc.list_evaluations, pid) == []
    assert read(U["ws_beta"], lc.list_incidents, pid) == []


# ----------------------------------------------------------- scenarios 10, 11

def test_s10_duplicate_entries_are_not_double_counted(world):
    env, U, pid = world
    day = max(segments_of(env, pid)[0]["start_date"], min(TODAY, segments_of(env, pid)[0]["end_date"]))
    first = cmd(U["s1"], lc.record_hours, pid, 8, work_date=day, description="Jornada")
    second = cmd(U["s1"], lc.record_hours, pid, 8, work_date=day, description="Jornada (duplicada)")
    with pytest.raises(BusinessError) as daily:
        cmd(U["s1"], lc.record_hours, pid, 9, work_date=day)
    assert daily.value.code == "HOURS_DAILY_LIMIT"
    cmd(U["pc_sys"], sg.review_hours, pid, first["entry_id"], decision="ACCEPTED",
        accepted_hours=None, reason_code=None, reason=None)
    with pytest.raises(BusinessError):
        cmd(U["pc_sys"], sg.review_hours, pid, second["entry_id"], decision="REJECTED",
            accepted_hours=None, reason_code="DUPLICATE", reason=None)  # reason required
    cmd(U["pc_sys"], sg.review_hours, pid, second["entry_id"], decision="REJECTED",
        accepted_hours=None, reason_code="DUPLICATE", reason="Misma jornada registrada dos veces")
    # Re-reviewing an already accepted entry replaces, never adds (latest review wins).
    cmd(U["dual1"], sg.review_hours, pid, first["entry_id"], decision="ACCEPTED",
        accepted_hours=None, reason_code=None, reason=None)
    assert accepted(env, pid) == 8.0
    summary = sg.hours_summary(env.admin, pid)
    assert float(summary["reported_total"]) == 16.0 and float(summary["accepted_total"]) == 8.0
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE progress_entry_review SET accepted_hours=16")
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("DELETE FROM progress_entry_review")


def test_s11_reported_hours_are_not_accepted_hours(world):
    env, U, pid = world
    entry = cmd(U["s1"], lc.record_hours, pid, 100)
    cmd(U["ws_alfa"], lc.create_evaluation, pid, "FINAL", "Evaluación final sintética.")
    _final_report(U, pid)
    with pytest.raises(BusinessError) as not_accepted:
        cmd(U["pc_sys"], lc.confirm_completion, pid)
    assert not_accepted.value.code == "COMPLETION_EVIDENCE_MISSING"
    with pytest.raises(BusinessError) as over:
        cmd(U["pc_sys"], sg.review_hours, pid, entry["entry_id"], decision="ACCEPTED",
            accepted_hours=120, reason_code=None, reason=None)
    assert over.value.code == "HOURS_REVIEW_INVALID"
    cmd(U["pc_sys"], sg.review_hours, pid, entry["entry_id"], decision="ACCEPTED",
        accepted_hours=70, reason_code="NOT_VERIFIABLE", reason="Solo 70 h verificables")
    assert accepted(env, pid) == 70.0
    listed = read(U["s1"], lc.list_hours, pid)[0]
    assert listed["review_status"] == "ACCEPTED" and float(listed["accepted_hours"]) == 70.0
    with pytest.raises(BusinessError):
        cmd(U["pc_sys"], lc.confirm_completion, pid)  # 70 < 100 accepted
    # The student cannot accept their own hours.
    with pytest.raises(Forbidden):
        cmd(U["s1"], sg.review_hours, pid, entry["entry_id"], decision="ACCEPTED",
            accepted_hours=None, reason_code=None, reason=None)


# ----------------------------------------------------------------- scenario 12

def test_s12_early_termination_keeps_history_and_recognition_decision(world):
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]
    cmd(U["s1"], lc.record_hours, pid, 40)
    accept_all(env, U, pid)
    end = max(seg1["start_date"], min(TODAY, seg1["end_date"]))
    cmd(U["ec1"], sg.terminate_segment, pid, seg1["id"], ended_on=end,
        reason_shared="La organización suspendió la rotación (sintético)", reason_internal=None,
        work_recognition="NOT_RECOGNIZED", recognition_note="Pendiente de decisión académica")
    row = segments_of(env, pid)[0]
    assert row["status"] == "TERMINATED_EARLY" and row["ended_on"] == end
    assert row["work_recognition"] == "NOT_RECOGNIZED"
    assert len(entry_ids(env, pid, seg1["id"])) == 1  # records kept
    assert accepted(env, pid) == 0.0  # not recognized -> not consolidated
    history = [(h["from_status"], h["to_status"]) for h in env.admin.execute(
        "SELECT from_status,to_status FROM placement_segment_status_history WHERE segment_id=%s ORDER BY id",
        (seg1["id"],)).fetchall()]
    assert history[-1] == ("ACTIVE", "TERMINATED_EARLY")
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE placement_segment SET status='ACTIVE' WHERE id=%s", (seg1["id"],))
    with pytest.raises(BusinessError) as gone:
        cmd(U["s1"], lc.record_hours, pid, 2)
    assert gone.value.code == "NO_ACTIVE_SEGMENT"


# ----------------------------------------------------------------- scenario 16

def test_s16_cross_access_is_rejected(world, monkeypatch):
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    with pytest.raises(Forbidden):
        cmd(U["pc_adm"], sg.create_segment, pid, seg_data(2, U["ws_beta"]))  # other program
    with pytest.raises(Forbidden):
        cmd(U["s1"], sg.create_segment, pid, seg_data(2, U["ws_beta"]))
    with pytest.raises(NotFound):
        cmd(U["hm_beta"], sg.create_segment, pid, seg_data(2, U["ws_beta"]))
    with pytest.raises(NotFound):
        read(U["ws_beta"], sg.list_segments, pid)
    with pytest.raises(Forbidden):  # internal user without relationship (E3 rule)
        read(U["s2"], sg.list_segments, pid)
    # The legal reviewer confirms conditions but cannot manage segments.
    with pytest.raises(Forbidden):
        cmd(U["legal1"], sg.activate_segment, pid, seg1)
    # Supervisor from another organization cannot be assigned to a segment of org 1.
    with pytest.raises(BusinessError) as invalid:
        cmd(U["ec1"], sg.create_segment, pid, seg_data(1, U["ws_beta"]))
    assert invalid.value.code == "SEGMENT_SUPERVISOR_INVALID"
    # Segment ids are scoped to their placement.
    other = make_active(env, U, "s2", make_opportunity(env, 1, U["P"]["ING-SIS"], "Otra"))
    with pytest.raises(NotFound):
        cmd(U["ec1"], sg.complete_segment, other, seg1)
    # Institutional authorities are configuration: unset -> nobody manages or reviews.
    monkeypatch.setenv("PLACEMENT_SEGMENT_MANAGER_ROLES", "")
    monkeypatch.setenv("PLACEMENT_HOURS_REVIEWER_ROLES", "")
    with pytest.raises(Forbidden):
        cmd(U["ec1"], sg.create_segment, pid, seg_data(2, U["ws_beta"]))
    entry = cmd(U["s1"], lc.record_hours, pid, 4)
    with pytest.raises(Forbidden):
        cmd(U["pc_sys"], sg.review_hours, pid, entry["entry_id"], decision="ACCEPTED",
            accepted_hours=None, reason_code=None, reason=None)


def test_s16b_workplace_reviewer_limited_to_current_segment(world, monkeypatch):
    env, U, pid = world
    monkeypatch.setenv("PLACEMENT_HOURS_REVIEWER_ROLES", "WORKPLACE_SUPERVISOR,PROGRAM_COORDINATOR")
    seg1 = segments_of(env, pid)[0]["id"]
    first = cmd(U["s1"], lc.record_hours, pid, 10)
    cmd(U["ws_alfa"], sg.review_hours, pid, first["entry_id"], decision="ACCEPTED",
        accepted_hours=None, reason_code=None, reason=None)
    with pytest.raises(NotFound):  # unrelated supervisor of the same organization
        cmd(U["ws_alfa2"], sg.review_hours, pid, first["entry_id"], decision="ACCEPTED",
            accepted_hours=None, reason_code=None, reason=None)
    second = cmd(U["s1"], lc.record_hours, pid, 6)
    cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY, reason_shared="Rotación sintética",
        reason_internal=None, prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED",
        destination=seg_data(2, U["ws_beta"]))
    with pytest.raises(NotFound):  # former supervisor: no access after the transfer
        cmd(U["ws_alfa"], sg.review_hours, pid, second["entry_id"], decision="ACCEPTED",
            accepted_hours=None, reason_code=None, reason=None)


# ----------------------------------------------------------------- scenario 17

def test_s17_concurrent_activation_and_transfer_stay_consistent(world):
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    # Two concurrent transfers of the same active segment: exactly one wins.
    out = race(
        lambda: cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY, reason_shared="A",
                    reason_internal=None, prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED",
                    destination=seg_data(2, U["ws_beta"])),
        lambda: cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY, reason_shared="B",
                    reason_internal=None, prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED",
                    destination=seg_data(2, U["ws_beta"])),
    )
    assert sorted(v[0] for v in out.values()) == ["BusinessError", "OK"]
    assert env.admin.execute("SELECT count(*) AS n FROM placement_transfer").fetchone()["n"] == 1
    assert len(segments_of(env, pid)) == 2

    # Two enabled planned segments activated concurrently: only one becomes ACTIVE.
    seg2 = segments_of(env, pid)[1]["id"]
    seg3 = cmd(U["ec1"], sg.create_segment, pid, seg_data(1, U["ws_alfa2"]))["segment_id"]
    confirm_doc_conditions(env, U, pid, seg2)
    confirm_doc_conditions(env, U, pid, seg3)
    for _ in range(3):
        out = race(lambda: cmd(U["ec1"], sg.activate_segment, pid, seg2),
                   lambda: cmd(U["ec1"], sg.activate_segment, pid, seg3))
        assert sorted(v[0] for v in out.values()) == ["BusinessError", "OK"]
        assert env.admin.execute(
            "SELECT count(*) AS n FROM placement_segment WHERE placement_id=%s AND status='ACTIVE'",
            (pid,)).fetchone()["n"] == 1
        break
    # The database index is the last line of defence even without the service lock.
    with pytest.raises(psycopg.errors.Error):
        env.admin.execute(
            "UPDATE placement_segment SET status='ACTIVE', activated_at=now() WHERE placement_id=%s "
            "AND status='PLANNED'", (pid,))


def test_s17b_concurrent_hour_reviews_do_not_double_count(world):
    env, U, pid = world
    entry = cmd(U["s1"], lc.record_hours, pid, 12)
    review = lambda who: cmd(U[who], sg.review_hours, pid, entry["entry_id"], decision="ACCEPTED",  # noqa: E731
                             accepted_hours=None, reason_code=None, reason=None)
    out = race(lambda: review("pc_sys"), lambda: review("dual1"))
    assert all(v[0] == "OK" for v in out.values())
    assert accepted(env, pid) == 12.0


# ----------------------------------------------------------------- HTTP surface

def _client(identifier: str) -> TestClient:
    client = TestClient(app, base_url=ORIGIN)
    assert client.post("/auth/login", json={"identifier": identifier, "password": TEST_PASSWORD},
                       headers={"Origin": ORIGIN}).status_code == 200
    return client


def test_http_segment_endpoints_enforce_permissions_and_privacy(world):
    env, U, pid = world
    clients = {name: _client(name) for name in ("ec1", "s1", "hm_beta", "pc_sys", "legal1", "ws_alfa")}
    try:
        body = {**seg_data(2, U["ws_beta"]), "start_date": TODAY.isoformat(),
                "end_date": (TODAY + dt.timedelta(days=30)).isoformat()}
        path = f"/placements/{pid}/segments"
        assert clients["s1"].post(path, json=body, headers={"Origin": ORIGIN}).status_code == 403
        assert clients["hm_beta"].post(path, json=body, headers={"Origin": ORIGIN}).status_code == 404
        created = clients["ec1"].post(path, json=body, headers={"Origin": ORIGIN})
        assert created.status_code == 201, created.text
        seg2 = created.json()["segment_id"]
        listed = clients["s1"].get(path).json()
        assert [s["status"] for s in listed] == ["ACTIVE", "PLANNED"]
        assert all("end_reason_internal" not in s for s in listed)
        assert clients["ws_alfa"].get(path).json()[0]["sequence_no"] == 1
        cond = next(c for c in listed[1]["conditions"] if c["status"] == "REQUIRED")
        confirm = f"{path}/{seg2}/conditions/{cond['id']}/confirm"
        assert clients["ec1"].post(confirm, json={"reference": "x"}, headers={"Origin": ORIGIN}).status_code == 403
        assert clients["legal1"].post(confirm, json={"reference": "Póliza POL-1"},
                                      headers={"Origin": ORIGIN}).status_code == 204
        activate = clients["ec1"].post(f"{path}/{seg2}/activate", headers={"Origin": ORIGIN})
        assert activate.status_code == 409 and activate.json()["error"] == "SEGMENT_ALREADY_ACTIVE"

        hours = clients["s1"].post(f"/placements/{pid}/hours", json={"hours": 6, "description": "Sesión"},
                                   headers={"Origin": ORIGIN})
        assert hours.status_code == 204, hours.text
        entry = entry_ids(env, pid)[0]
        review_path = f"/placements/{pid}/hours/{entry}/review"
        assert clients["s1"].post(review_path, json={"decision": "ACCEPTED"},
                                  headers={"Origin": ORIGIN}).status_code == 403
        reviewed = clients["pc_sys"].post(review_path, json={"decision": "ACCEPTED", "accepted_hours": 5},
                                          headers={"Origin": ORIGIN})
        assert reviewed.status_code == 201, reviewed.text
        summary = clients["s1"].get(f"/placements/{pid}/hours/summary").json()
        assert float(summary["accepted_total"]) == 5.0 and float(summary["reported_total"]) == 6.0
        options = clients["ec1"].get(f"/placements/{pid}/segment-options")
        assert options.status_code == 200
        assert {o["id"] for o in options.json()} == {1, 2}
        assert clients["s1"].get(f"/placements/{pid}/segment-options").status_code == 403
        dossier = clients["ec1"].get(f"/placements/{pid}/dossier").json()
        assert dossier["capabilities"]["manage_segments"] is True
        assert len(dossier["segments"]) == 2 and "hours_summary" in dossier
        assert clients["s1"].get(f"/placements/{pid}/dossier").json()["capabilities"]["manage_segments"] is False
    finally:
        for client in clients.values():
            client.close()


# ------------------------------------------------------------- CR-05 reports

def test_rotation_reports_aggregate_cr05_state_within_scope(world):
    """CR-05 requested reports: multi-segment placements, active rotations,
    transfers, interruptions, accepted hours, missing evaluations and pending
    consolidations. Aggregates only, scoped like the E3 operational report."""
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    cmd(U["s1"], lc.record_hours, pid, 30)
    accept_all(env, U, pid)
    moved = cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY,
                reason_shared="Rotación sintética", reason_internal="Nota interna sintética",
                prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED", destination=seg_data(2, U["ws_beta"]))
    seg2 = moved["to_segment_id"]

    def report(user, **filters):
        return read(U[user], lambda cur, subj: reports.rotations(cur, subj, **filters))

    planned = report("pc_sys")
    assert planned["multi_segment_placements"] == 1 and planned["transfers"] == 1
    # The organization filter also matches the segment's organization (destination org 2).
    assert report("ec1", organization_id=2)["transfers"] == 1
    assert report("ec1", organization_id=1)["transfers"] == 1
    assert report("ec1", organization_id=999_999)["multi_segment_placements"] == 0
    assert planned["active_rotations"] == 0 and planned["pending_consolidations"] == 0
    assert {r["status"]: r["count"] for r in planned["segments_by_status"]} == {"TRANSFERRED": 1, "PLANNED": 1}

    confirm_doc_conditions(env, U, pid, seg2)
    cmd(U["ec1"], sg.activate_segment, pid, seg2)
    cmd(U["s1"], lc.record_hours, pid, 10)
    active = report("ec1")
    assert active["active_rotations"] == 1
    assert active["active_segments_without_final_evaluation"] == 1
    assert active["hours"]["pending_entries"] == 1

    cmd(U["ec1"], sg.terminate_segment, pid, seg2, ended_on=TODAY,
        reason_shared="La organización suspendió la rotación (sintético)", reason_internal=None,
        work_recognition="NOT_RECOGNIZED", recognition_note=None)
    ended = report("pc_sys", program_id=U["P"]["ING-SIS"])
    assert ended["interruptions"] == 1
    assert ended["interruptions_by_recognition"] == [{"recognition": "NOT_RECOGNIZED", "count": 1}]
    assert ended["hours"] == {"reported": 40.0, "accepted": 30.0, "not_recognized": 10.0,
                              "pending_entries": 0, "disputed_entries": 0}
    assert ended["pending_consolidations"] == 1 and ended["active_rotations"] == 0
    assert ended["by_program"][0]["program_code"] == "ING-SIS"
    assert ended["by_program"][0]["pending_consolidations"] == 1

    cmd(U["pc_sys"], sg.record_experience_review, pid, "APPROVED", "Experiencia combinada revisada (sintético).")
    assert report("pc_sys")["pending_consolidations"] == 0

    # Scope: another program's coordinator sees nothing of this placement and cannot ask for it.
    other = report("pc_adm")
    assert other["multi_segment_placements"] == 0 and other["transfers"] == 0
    with pytest.raises(Forbidden):
        report("pc_adm", program_id=U["P"]["ING-SIS"])
    with pytest.raises(Forbidden):
        report("ws_beta")

    clients = {name: _client(name) for name in ("pc_sys", "hm_alfa", "s1")}
    try:
        response = clients["pc_sys"].get("/reports/rotations")
        assert response.status_code == 200, response.text
        assert response.json()["transfers"] == 1
        assert "Nota interna" not in response.text and "Student One" not in response.text
        assert "suspendió" not in response.text
        assert clients["hm_alfa"].get("/reports/rotations").status_code == 403
        assert clients["s1"].get("/reports/rotations").status_code == 403
    finally:
        for client in clients.values():
            client.close()


def test_segment_events_notify_related_people_but_not_the_previous_supervisor(world):
    """CR-05 notices: activation reaches the new supervisor; a transfer reaches the
    student and university roles but never the previous supervisor (BR-06)."""
    env, U, pid = world

    def notices(user):
        return [row["category"] for row in env.admin.execute(
            "SELECT category FROM user_notification WHERE recipient_id=%s AND placement_id=%s ORDER BY id",
            (U[user], pid)).fetchall()]

    seg1 = segments_of(env, pid)[0]["id"]
    before_alfa = notices("ws_alfa").count("SEGMENT_CHANGED")
    moved = cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY, reason_shared="Rotación sintética",
                reason_internal=None, prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED",
                destination=seg_data(2, U["ws_beta"]))
    assert notices("s1").count("SEGMENT_CHANGED") == 1
    assert notices("pc_sys").count("SEGMENT_CHANGED") == 1
    assert notices("ws_alfa").count("SEGMENT_CHANGED") == before_alfa  # previous supervisor: no notice
    assert notices("ec1").count("SEGMENT_CHANGED") == 0  # the actor is never notified of their own action
    assert "SEGMENT_CHANGED" not in notices("ws_beta")  # still PLANNED

    confirm_doc_conditions(env, U, pid, moved["to_segment_id"])
    cmd(U["ec1"], sg.activate_segment, pid, moved["to_segment_id"])
    assert notices("ws_beta").count("SEGMENT_CHANGED") == 1
    assert notices("ws_alfa").count("SEGMENT_CHANGED") == before_alfa
    assert notices("s1").count("SEGMENT_CHANGED") == 2
    payload = env.admin.execute(
        "SELECT to_jsonb(n) AS row FROM user_notification n WHERE recipient_id=%s ORDER BY id DESC LIMIT 1",
        (U["ws_beta"],)).fetchone()["row"]
    assert "reason" not in str(payload)  # a notice carries only its category and links


def _code(excinfo) -> str:
    return excinfo.value.code


def test_segment_schedule_changes_follow_explicit_rules_and_keep_history(world):
    """CR-05 §6.3 "Excepciones temporales": shorten/extend an open segment or move
    a planned one, with explicit rules and an append-only history (0018)."""
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]
    sid, start, end = seg1["id"], seg1["start_date"], seg1["end_date"]
    days = dt.timedelta

    def reschedule(user, segment_id, *, end_date, start_date=None, reason="Ajuste sintético del periodo"):
        return cmd(U[user], sg.reschedule_segment, pid, segment_id, start_date=start_date,
                   end_date=end_date, reason_shared=reason)

    # Only the configured segment authority may change dates.
    for user in ("ws_alfa", "s1", "f1"):
        with pytest.raises((Forbidden, NotFound)):
            reschedule(user, sid, end_date=end + days(7))
    # Explicit rules for an active segment.
    with pytest.raises(BusinessError) as exc:
        reschedule("ec1", sid, start_date=start - days(1), end_date=end)
    assert _code(exc) == "SEGMENT_START_LOCKED"
    with pytest.raises(BusinessError) as exc:
        reschedule("ec1", sid, end_date=TODAY - days(1))
    assert _code(exc) in {"SEGMENT_END_DATE_INVALID", "SEGMENT_DATES_INVALID"}
    with pytest.raises(BusinessError) as exc:
        reschedule("ec1", sid, end_date=end)
    assert _code(exc) == "SEGMENT_SCHEDULE_UNCHANGED"
    with pytest.raises(BusinessError) as exc:
        reschedule("ec1", sid, end_date=end + days(7), reason="   ")
    assert _code(exc) == "SEGMENT_FIELD_REQUIRED"

    extended = reschedule("ec1", sid, end_date=end + days(20), reason="Extensión sintética acordada")
    assert extended["change"] == "EXTENDED"
    # Hours cannot be dated in the future, so an active segment that ends today or later
    # always contains its dated hours; the conflict guard is a defensive check (service + trigger).
    cmd(U["s1"], lc.record_hours, pid, 4, work_date=TODAY, description="Trabajo sintético")
    shortened = reschedule("ec1", sid, end_date=end + days(16), reason="Acortamiento sintético")
    assert shortened["change"] == "SHORTENED"
    row = segments_of(env, pid)[0]
    assert (row["start_date"], row["end_date"], row["status"]) == (start, end + days(16), "ACTIVE")

    # History is append-only and visible with the shared reason only.
    history = read(U["s1"], sg.list_segments, pid)[0]["schedule_changes"]
    assert [(h["from_end_date"], h["to_end_date"]) for h in history] == [
        (end, end + days(20)), (end + days(20), end + days(16))]
    assert history[0]["reason_shared"] == "Extensión sintética acordada"
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE placement_segment_schedule_change SET reason_shared='x'")
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE placement_segment SET end_date=end_date + 1 WHERE id=%s", (sid,))
    actions = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_id=%s AND action='segment.rescheduled'", (pid,)).fetchall()]
    assert len(actions) == 2
    assert env.admin.execute(
        """SELECT count(*)::int AS n FROM user_notification WHERE recipient_id=%s AND placement_id=%s
           AND category='SEGMENT_CHANGED'""", (U["s1"], pid)).fetchone()["n"] == 2

    # A planned segment can be moved; a closed or cancelled one cannot change.
    planned = cmd(U["ec1"], sg.create_segment, pid, seg_data(2, U["ws_beta"], start=TODAY + days(30)))
    moved = reschedule("ec1", planned["segment_id"], start_date=TODAY + days(40), end_date=TODAY + days(90))
    assert moved["change"] == "MOVED"
    with pytest.raises(BusinessError) as exc:
        reschedule("ec1", planned["segment_id"], start_date=TODAY + days(50), end_date=TODAY + days(45))
    assert _code(exc) == "SEGMENT_DATES_INVALID"
    cmd(U["ec1"], sg.cancel_segment, pid, planned["segment_id"], "Rotación sintética descartada")
    with pytest.raises(BusinessError) as exc:
        reschedule("ec1", planned["segment_id"], end_date=TODAY + days(95))
    assert _code(exc) == "SEGMENT_NOT_OPEN"

    clients = {name: _client(name) for name in ("ec1", "ws_alfa")}
    try:
        body = {"end_date": (end + days(30)).isoformat(), "reason_shared": "Extensión HTTP sintética"}
        assert clients["ws_alfa"].post(f"/placements/{pid}/segments/{sid}/schedule", json=body,
                                       headers={"Origin": ORIGIN}).status_code in (403, 404)
        response = clients["ec1"].post(f"/placements/{pid}/segments/{sid}/schedule", json=body,
                                       headers={"Origin": ORIGIN})
        assert response.status_code == 200, response.text
        assert response.json()["change"] == "EXTENDED"
    finally:
        for client in clients.values():
            client.close()


# ------------------------------------------------ 0019: attribute revisions

def test_segment_attribute_changes_are_adjustments_not_transfers(world):
    """CR-05 §3.1: an administrative adjustment keeps the segment and its records,
    leaves an append-only revision, and never replaces a transfer."""
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]
    sid = seg1["id"]
    cmd(U["s1"], lc.record_hours, pid, 8, work_date=TODAY, description="Trabajo sintético")
    entries_before = entry_ids(env, pid, sid)

    def update(user, segment_id, reason="Ajuste administrativo sintético", **changes):
        return cmd(U[user], sg.update_segment, pid, segment_id, changes, reason)

    for user in ("ws_alfa", "s1", "f1", "legal1"):
        with pytest.raises((Forbidden, NotFound)):
            update(user, sid, modality="REMOTE")
    # Explicit rules for an active segment: organization, unit and supervisor need a transfer.
    for changes, code in (({"unit": "Otra unidad"}, "SEGMENT_CHANGE_REQUIRES_TRANSFER"),
                          ({"workplace_supervisor_id": U["ws_alfa2"]}, "SEGMENT_CHANGE_REQUIRES_TRANSFER"),
                          ({"host_org_id": 2}, "SEGMENT_ORGANIZATION_LOCKED"),
                          ({"end_date": TODAY + dt.timedelta(days=90)}, "SEGMENT_DATES_USE_SCHEDULE"),
                          ({"responsibilities": seg1["responsibilities"]}, "SEGMENT_UNCHANGED"),
                          ({"modality": "PRESENCIAL"}, "SEGMENT_MODALITY_INVALID"),
                          ({"expected_hours": -5}, "SEGMENT_EXPECTED_HOURS_INVALID")):
        with pytest.raises(BusinessError) as exc:
            update("ec1", sid, **changes)
        assert _code(exc) == code, changes
    with pytest.raises(BusinessError) as exc:
        update("ec1", sid, reason="  ", modality="REMOTE")
    assert _code(exc) == "SEGMENT_FIELD_REQUIRED"

    new_modality = "REMOTE" if seg1["modality"] != "REMOTE" else "ONSITE"
    result = update("ec1", sid, modality=new_modality, expected_hours=180,
                    responsibilities="Responsabilidades ajustadas (sintético)",
                    reason="Cambio acordado con la organización (sintético)")
    assert set(result["changed_fields"]) == {"modality", "expected_hours", "responsibilities"}
    row = segments_of(env, pid)[0]
    assert (row["id"], row["status"], row["host_org_id"], row["workplace_supervisor_id"]) == (
        sid, "ACTIVE", 1, U["ws_alfa"])
    assert row["modality"] == new_modality and float(row["expected_hours"]) == 180.0
    # Hours already recorded stay attached to the same segment, untouched.
    assert entry_ids(env, pid, sid) == entries_before

    # A planned segment may change unit and supervisor, but only within its organization.
    planned = cmd(U["ec1"], sg.create_segment, pid,
                  seg_data(1, U["ws_alfa2"], start=TODAY + dt.timedelta(days=70)))["segment_id"]
    with pytest.raises(BusinessError) as exc:
        update("ec1", planned, workplace_supervisor_id=U["ws_beta"])
    assert _code(exc) == "SEGMENT_SUPERVISOR_INVALID"
    changed = update("ec1", planned, unit="Unidad de destino ajustada", workplace_supervisor_id=U["ws_alfa"],
                     reason="Cambio de tutor antes del inicio (sintético)")
    assert set(changed["changed_fields"]) == {"unit", "workplace_supervisor_id"}

    # History: append-only, shared reason only, supervisor names instead of ids.
    listed = {s["id"]: s for s in read(U["s1"], sg.list_segments, pid)}
    revision = listed[planned]["revisions"][0]
    assert revision["previous"] == {"unit": "Unidad sintética", "workplace_supervisor": "Workplace Sup Alfa 2"}
    assert revision["new"] == {"unit": "Unidad de destino ajustada", "workplace_supervisor": "Workplace Sup Alfa"}
    assert revision["reason_shared"] == "Cambio de tutor antes del inicio (sintético)"
    assert listed[sid]["revisions"][0]["segment_status"] == "ACTIVE"
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE placement_segment_revision SET reason_shared='x'")
    with pytest.raises(psycopg.errors.RaiseException, match="recorded revision"):
        env.admin.execute("UPDATE placement_segment SET responsibilities='x' WHERE id=%s", (sid,))
    with pytest.raises(psycopg.errors.RaiseException, match="IMMUTABLE"):
        env.admin.execute("UPDATE placement_segment SET host_org_id=2 WHERE id=%s", (planned,))

    # Audit names the fields, never the free text; the student receives a notice.
    payloads = [r["after"] for r in env.admin.execute(
        "SELECT after_state AS after FROM audit_event WHERE subject_id=%s AND action='segment.updated' ORDER BY id",
        (pid,)).fetchall()]
    assert len(payloads) == 2 and "ajustadas" not in str(payloads)
    assert env.admin.execute(
        """SELECT count(*)::int AS n FROM user_notification WHERE recipient_id=%s AND placement_id=%s
           AND category='SEGMENT_CHANGED'""", (U["s1"], pid)).fetchone()["n"] >= 1

    clients = {name: _client(name) for name in ("ec1", "ws_alfa")}
    try:
        path = f"/placements/{pid}/segments/{planned}"
        body = {"responsibilities": "Responsabilidades HTTP (sintético)", "reason_shared": "Ajuste HTTP"}
        assert clients["ws_alfa"].patch(path, json=body, headers={"Origin": ORIGIN}).status_code in (403, 404)
        unknown = clients["ec1"].patch(path, json={**body, "status": "ACTIVE"}, headers={"Origin": ORIGIN})
        assert unknown.status_code == 422
        ok = clients["ec1"].patch(path, json=body, headers={"Origin": ORIGIN})
        assert ok.status_code == 200, ok.text
        assert ok.json()["changed_fields"] == ["responsibilities"]
        locked = clients["ec1"].patch(f"/placements/{pid}/segments/{sid}",
                                      json={"unit": "Otra", "reason_shared": "x"}, headers={"Origin": ORIGIN})
        assert locked.status_code == 409 and locked.json()["error"] == "SEGMENT_CHANGE_REQUIRES_TRANSFER"
    finally:
        for client in clients.values():
            client.close()


# ------------------------------------------------ 0019: documentary evidence

PDF = b"%PDF-1.7 synthetic segment evidence"


def _evidence_item(env, sid):
    return env.admin.execute(
        """SELECT ci.* FROM checklist_item ci JOIN placement_segment_condition c ON c.id=ci.segment_condition_id
           WHERE c.segment_id=%s""", (sid,)).fetchone()


def _condition(env, sid):
    return env.admin.execute(
        "SELECT * FROM placement_segment_condition WHERE segment_id=%s AND kind='DOC_INSURANCE'", (sid,)).fetchone()


def test_segment_condition_evidence_reuses_the_document_module(world):
    """CR-05 §3.2: real documents satisfy a segment condition through upload,
    revision and review of the existing document module; ownership and scope
    are enforced and placement-level E3 gates are unaffected."""
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    seg2 = cmd(U["ec1"], sg.create_segment, pid, seg_data(2, U["ws_beta"]))["segment_id"]
    item = _evidence_item(env, seg2)
    assert (item["kind"], item["mandatory"], item["status"]) == ("DOC_SEG2_INSURANCE", False, "REQUIRED")
    assert item["segment_condition_id"] == _condition(env, seg2)["id"]
    # The checklist names the segment; the previous supervisor does not see the other segment's item.
    listed = {r["id"]: r for r in read(U["s1"], lc.list_checklist, pid)}
    assert listed[item["id"]]["segment_sequence_no"] == 2
    assert listed[item["id"]]["condition_kind"] == "DOC_INSURANCE"
    assert item["id"] not in {r["id"] for r in read(U["ws_alfa"], lc.list_checklist, pid)}

    # Ownership: another student, or an item from another placement, is refused.
    other_pid = make_active(env, U, "s2", make_opportunity(env, 1, U["P"]["ING-SIS"], "Otra oportunidad"))
    with pytest.raises((Forbidden, NotFound)):
        cmd(U["s2"], lc.submit_document, pid, item["id"], "poliza.pdf", "application/pdf", PDF)
    with pytest.raises(NotFound):
        cmd(U["s2"], lc.submit_document, other_pid, item["id"], "poliza.pdf", "application/pdf", PDF)
    with pytest.raises((Forbidden, NotFound)):
        cmd(U["ec1"], lc.submit_document, pid, item["id"], "poliza.pdf", "application/pdf", PDF)

    cmd(U["s1"], lc.submit_document, pid, item["id"], "poliza-v1.pdf", "application/pdf", PDF)
    assert _condition(env, seg2)["status"] == "REQUIRED"  # submission alone satisfies nothing
    with pytest.raises((Forbidden, NotFound)):
        cmd(U["ec1"], lc.review_document, pid, item["id"], "APPROVED", "No es revisor")
    cmd(U["legal1"], lc.review_document, pid, item["id"], "REJECTED", "Falta la vigencia de la póliza")
    assert _condition(env, seg2)["status"] == "REQUIRED"
    assert read(U["s1"], sg.list_segments, pid)[1]["conditions"][0]["evidence_status"] in {"REJECTED", None}

    cmd(U["s1"], lc.submit_document, pid, item["id"], "poliza-v2.pdf", "application/pdf", PDF + b" v2")
    cmd(U["legal1"], lc.review_document, pid, item["id"], "APPROVED", "Póliza vigente")
    cond = _condition(env, seg2)
    assert cond["status"] == "SATISFIED" and cond["confirmed_by"] == U["legal1"]
    assert cond["reference"] == "Documento aprobado: poliza-v2.pdf (revisión 2)"
    with db.read() as cur:
        assert sg.segment_unmet_conditions(cur, seg2) == []
    seg_view = next(s for s in read(U["s1"], sg.list_segments, pid) if s["id"] == seg2)
    doc_cond = next(c for c in seg_view["conditions"] if c["kind"] == "DOC_INSURANCE")
    assert (doc_cond["evidence_item_id"], doc_cond["evidence_status"]) == (item["id"], "APPROVED")

    # Withdrawing the approval while the segment is planned reopens the condition.
    cmd(U["legal1"], lc.review_document, pid, item["id"], "REJECTED", "La póliza fue anulada")
    assert _condition(env, seg2)["status"] == "REQUIRED"
    actions = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_id=%s AND action LIKE 'segment.condition_%%' ORDER BY id",
        (pid,)).fetchall()]
    assert actions == ["segment.condition_satisfied", "segment.condition_reopened"]
    with pytest.raises(BusinessError) as exc:
        cmd(U["ec1"], sg.activate_segment, pid, seg2)
    assert _code(exc) in {"SEGMENT_CONDITIONS_UNMET", "SEGMENT_ALREADY_ACTIVE"}
    cmd(U["s1"], lc.submit_document, pid, item["id"], "poliza-v3.pdf", "application/pdf", PDF + b" v3")
    cmd(U["legal1"], lc.review_document, pid, item["id"], "APPROVED", "Póliza nueva vigente")
    assert _condition(env, seg2)["status"] == "SATISFIED"

    # A condition cannot be reopened by hand, only by rejecting its evidence.
    with pytest.raises(psycopg.errors.RaiseException, match="IMMUTABLE"):
        env.admin.execute(
            """UPDATE placement_segment_condition SET status='REQUIRED', confirmed_by=NULL, confirmed_at=NULL,
               reference=NULL WHERE id=%s""", (cond["id"],))

    # Placement-level gates ignore the optional evidence item.
    assert env.admin.execute("SELECT mandatory FROM checklist_item WHERE id=%s", (item["id"],)).fetchone()[
        "mandatory"] is False
    with pytest.raises(psycopg.errors.CheckViolation):
        env.admin.execute("UPDATE checklist_item SET mandatory=true WHERE id=%s", (item["id"],))

    # Once the segment is active the evidence is closed, and later reviews do not touch the condition.
    cmd(U["ws_alfa"], lc.create_evaluation, pid, "FINAL", "Cierre de la rotación 1 (sintético).")
    cmd(U["ec1"], sg.complete_segment, pid, seg1)
    cmd(U["ec1"], sg.activate_segment, pid, seg2)
    cmd(U["legal1"], lc.review_document, pid, item["id"], "REJECTED", "Revisión posterior (sintético)")
    assert _condition(env, seg2)["status"] == "SATISFIED"
    with pytest.raises(BusinessError) as exc:
        cmd(U["s1"], lc.submit_document, pid, item["id"], "poliza-v4.pdf", "application/pdf", PDF)
    assert _code(exc) == "SEGMENT_EVIDENCE_CLOSED"

    # Downloads stay private and authenticated.
    submission = env.admin.execute(
        "SELECT id FROM document_submission WHERE checklist_item_id=%s ORDER BY revision LIMIT 1",
        (item["id"],)).fetchone()["id"]
    path = f"/placements/{pid}/items/{item['id']}/submissions/{submission}/download"
    anonymous = TestClient(app, base_url=ORIGIN)
    clients = {name: _client(name) for name in ("s1", "s2", "hm_beta", "legal1")}
    try:
        assert anonymous.get(path).status_code == 401
        assert clients["s2"].get(path).status_code in (403, 404)
        assert clients["hm_beta"].get(path).status_code in (403, 404)
        assert clients["legal1"].get(path).status_code == 200
        own = clients["s1"].get(path)
        assert own.status_code == 200 and own.content == PDF
        pending = clients["legal1"].get("/placements/documents-pending")
        assert pending.status_code == 200
    finally:
        anonymous.close()
        for client in clients.values():
            client.close()


def test_rotation_report_filters_and_scope_regression(world):
    """Every filter of /reports/rotations (program, organization including the
    segment organization, placement state, combinations) and every role's scope."""
    from tests.conftest import make_doc_pending
    env, U, pid = world
    seg1 = segments_of(env, pid)[0]["id"]
    cmd(U["s1"], lc.record_hours, pid, 20)
    accept_all(env, U, pid)
    cmd(U["ec1"], sg.transfer, pid, seg1, effective_date=TODAY, reason_shared="Rotación sintética",
        reason_internal="Nota interna sintética", prior_work_treatment="ACCEPTED_HOURS_RECOGNIZED",
        destination=seg_data(2, U["ws_beta"]))
    adm_pid = make_active(env, U, "s3", make_opportunity(env, 1, U["P"]["ADM"], "Oportunidad ADM"))
    cmd(U["s3"], lc.record_hours, adm_pid, 5)
    make_doc_pending(env, U, "s2", make_opportunity(env, 2, U["P"]["ING-SIS"], "Oportunidad Beta"))

    def report(user, **filters):
        return read(U[user], lambda cur, subj: reports.rotations(cur, subj, **filters))

    def shape(r):
        return (r["multi_segment_placements"], r["single_segment_placements"], r["transfers"],
                float(r["hours"]["reported"]), float(r["hours"]["accepted"]), r["hours"]["pending_entries"])

    everything = (1, 1, 1, 25.0, 20.0, 1)
    assert shape(report("ec1")) == everything
    assert shape(report("ec1", program_id=U["P"]["ING-SIS"])) == (1, 0, 1, 20.0, 20.0, 0)
    assert shape(report("ec1", program_id=U["P"]["ADM"])) == (0, 1, 0, 5.0, 0.0, 1)
    assert shape(report("ec1", organization_id=1)) == everything
    assert shape(report("ec1", organization_id=2)) == (1, 0, 1, 20.0, 20.0, 0)  # via the segment
    assert shape(report("ec1", placement_state="ACTIVE")) == everything
    assert shape(report("ec1", placement_state="DOCUMENTATION_PENDING")) == (0, 0, 0, 0.0, 0.0, 0)
    assert shape(report("ec1", organization_id=2, program_id=U["P"]["ADM"])) == (0, 0, 0, 0.0, 0.0, 0)
    assert shape(report("ec1", organization_id=1, placement_state="ACTIVE",
                        program_id=U["P"]["ADM"])) == (0, 1, 0, 5.0, 0.0, 1)
    with pytest.raises(BusinessError) as exc:
        report("ec1", placement_state="ACTIVE' OR '1'='1")
    assert _code(exc) == "REPORT_FILTER_INVALID"

    # Coordinator scope: own programs only, and an explicit foreign program is refused.
    assert shape(report("pc_sys")) == (1, 0, 1, 20.0, 20.0, 0)
    assert shape(report("dual1")) == (1, 0, 1, 20.0, 20.0, 0)
    assert shape(report("pc_adm")) == (0, 1, 0, 5.0, 0.0, 1)
    assert shape(report("pc_adm", organization_id=2)) == (0, 0, 0, 0.0, 0.0, 0)
    for user, program in (("pc_sys", "ADM"), ("pc_adm", "ING-SIS")):
        with pytest.raises(Forbidden):
            report(user, program_id=U["P"][program])
    for user in ("s1", "f1", "legal1", "ws_alfa", "hm_alfa"):
        with pytest.raises((Forbidden, NotFound)):
            report(user)

    names = ("ec1", "pc_adm", "s1", "f1", "legal1", "ws_beta", "hm_beta")
    clients = {name: _client(name) for name in names}
    try:
        ok = clients["ec1"].get("/reports/rotations", params={"organization_id": 2, "placement_state": "ACTIVE"})
        assert ok.status_code == 200 and ok.json()["transfers"] == 1
        for leak in ("Student", "Nota interna", "Rotación sintética", "Oportunidad", "Sup "):
            assert leak not in ok.text
        bad = clients["ec1"].get("/reports/rotations", params={"placement_state": "NOPE"})
        assert bad.status_code in (400, 409, 422)
        assert clients["ec1"].get("/reports/rotations", params={"organization_id": 0}).status_code == 422
        assert clients["pc_adm"].get("/reports/rotations",
                                     params={"program_id": U["P"]["ING-SIS"]}).status_code == 403
        for name in ("s1", "f1", "legal1", "ws_beta", "hm_beta"):
            assert clients[name].get("/reports/rotations").status_code == 403, name
    finally:
        for client in clients.values():
            client.close()
