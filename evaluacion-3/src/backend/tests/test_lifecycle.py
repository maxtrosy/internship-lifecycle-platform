"""PostgreSQL lifecycle tests (T-01, T-02, T-02b, T-04, T-08, T-16a..e)."""
from __future__ import annotations

import os
import random
import threading
import time

import psycopg
import pytest

from app import db
from app.errors import BusinessError
from app.modules.lifecycle import service as lc
from tests.conftest import make_active, make_doc_pending, make_opportunity, make_placement, race, seed_base

TRIALS = int(os.environ.get("POC_TRIALS", "100"))


def cmd(actor_id, fn, *args, **kwargs):
    with db.command(actor_id) as ctx:
        return fn(ctx, *args, **kwargs)


def audit_actions(env, pid):
    return [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='placement' AND subject_id=%s ORDER BY id", (pid,)).fetchall()]


def test_t01_activation_concurrency(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")

    def trial(naive):
        p = make_doc_pending(env, U, "s1", opp)
        out = race(
            lambda: cmd(U["ec1"], lc.activate, p, naive=naive, pause=0.05 if naive else 0.0),
            lambda: cmd(U["ec1"], lc.activate, p, naive=naive, pause=0.05 if naive else 0.0),
        )
        n_ok = sum(1 for v in out.values() if v[0] == "OK")
        n_audit = audit_actions(env, p).count("placement.activated")
        state = env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"]
        return n_ok, n_audit, state, sorted(v[0] for v in out.values())

    good = [trial(False) for _ in range(TRIALS)]
    assert all(g[0] == 1 and g[1] == 1 and g[2] == "ACTIVE" and g[3] == ["BusinessError", "OK"] for g in good)
    ctrl = [trial(True) for _ in range(30)]
    assert sum(1 for g in ctrl if g[0] == 2 or g[1] == 2) > 0  # control detects the violation


def test_t02_reject_vs_activate(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")

    def trial(variant):
        naive = variant != "A"
        p = make_doc_pending(env, U, "s1", opp)
        item = env.admin.execute(
            "SELECT id FROM checklist_item WHERE placement_id=%s AND kind='DOC_INSURANCE'", (p,)).fetchone()["id"]
        act_first = random.random() < 0.5
        out = race(
            lambda: cmd(U["ec1"], lc.activate, p, naive=naive, pause=0.05),
            lambda: cmd(U["legal1"], lc.review_document, p, item, "REJECTED", "Documento no válido", naive=naive),
            delay_a=0.0 if act_first else 0.02,
            delay_b=0.02 if act_first else 0.0,
        )
        a_ids = [r["id"] for r in env.admin.execute(
            "SELECT id FROM audit_event WHERE action='placement.activated' AND subject_id=%s", (p,)).fetchall()]
        r_ids = [r["id"] for r in env.admin.execute(
            """SELECT id FROM audit_event WHERE subject_id=%s
               AND action IN ('checklist_item.rejected','checklist_item.rejected_after_activation')""",
            (item,)).fetchall()]
        forbidden = bool(a_ids and r_ids and r_ids[0] < a_ids[0])
        return forbidden, out["a"][0]

    summary = {}
    for variant, n in (("A", TRIALS), ("B", 40), ("C", 40)):
        if variant == "B":
            env.admin.execute("ALTER TABLE placement DISABLE TRIGGER trg_placement_gate")
        res = [trial(variant) for _ in range(n)]
        if variant == "B":
            env.admin.execute("ALTER TABLE placement ENABLE TRIGGER trg_placement_gate")
        summary[variant] = sum(1 for r in res if r[0])

    assert summary["A"] == 0 and summary["C"] == 0 and summary["B"] > 0


def test_t02b_bypass_and_denied_atomicity(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_doc_pending(env, U, "s1", opp, docs_approved=False)
    c = env.conn()
    with pytest.raises(psycopg.errors.RaiseException):
        c.execute("UPDATE placement SET state='ACTIVE' WHERE id=%s", (p,))
    before = len(env.admin.execute("SELECT 1 FROM audit_event").fetchall())
    with pytest.raises(BusinessError):
        cmd(U["ec1"], lc.activate, p)
    after = len(env.admin.execute("SELECT 1 FROM audit_event").fetchall())
    assert before == after
    c.close()


def test_t04_closure_integrity(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)

    with pytest.raises(BusinessError):
        cmd(U["pc_sys"], lc.confirm_completion, p)
    cmd(U["s1"], lc.submit_completion_evidence, p, "FINAL_REPORT", "informe-final.pdf",
        "application/pdf", b"%PDF-1.7 synthetic final report")
    with pytest.raises(BusinessError):
        cmd(U["pc_sys"], lc.confirm_completion, p)
    cmd(U["s1"], lc.record_hours, p, 40)
    cmd(U["ws_alfa"], lc.create_evaluation, p, "FINAL", "Evaluación narrativa documentada.")
    with pytest.raises(BusinessError):
        cmd(U["pc_sys"], lc.confirm_completion, p)
    with pytest.raises(BusinessError):
        cmd(U["ec1"], lc.close_placement, p)
    cmd(U["s1"], lc.record_hours, p, 70)  # 110h total
    cmd(U["pc_sys"], lc.confirm_completion, p)
    cmd(U["ec1"], lc.close_placement, p)
    state = env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"]
    assert state == "CLOSED"
    evidence_before = env.admin.execute(
        "SELECT count(*) AS n FROM completion_evidence WHERE placement_id=%s", (p,),
    ).fetchone()["n"]
    with pytest.raises(BusinessError) as closed_evidence:
        cmd(U["s1"], lc.submit_completion_evidence, p, "FINAL_REPORT", "informe-final-v2.pdf",
            "application/pdf", b"%PDF-1.7 late report")
    assert closed_evidence.value.code == "PLACEMENT_NOT_ACTIVE"
    with pytest.raises(BusinessError) as closed_evaluation:
        cmd(U["ws_alfa"], lc.create_evaluation, p, "FINAL", "Evaluación tardía.")
    assert closed_evaluation.value.code == "PLACEMENT_NOT_ACTIVE"
    assert env.admin.execute(
        "SELECT count(*) AS n FROM completion_evidence WHERE placement_id=%s", (p,),
    ).fetchone()["n"] == evidence_before


def test_t04_persisted_sources_not_cached_flags_control_closure(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)
    raw = env.conn()
    try:
        raw.execute("UPDATE completion_requirement SET satisfied=true WHERE placement_id=%s", (p,))
        raw.execute("INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,100)",
                    (p, U["s1"]))
        with pytest.raises(psycopg.errors.RaiseException, match="unsatisfied"):
            raw.execute("UPDATE placement SET state='COMPLETED' WHERE id=%s", (p,))
        assert raw.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == "ACTIVE"
    finally:
        raw.close()


def test_t04_concurrent_hours_insert_waits_for_completion_commit(env, monkeypatch):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)
    _satisfy_closure(env, U, "s1", p, hours=100)

    completion_update_reached = threading.Event()
    release_completion = threading.Event()
    hours_done = threading.Event()
    outcomes = {}
    original_audit_write = lc.audit.write

    def pause_completion_audit(cur, action, *args, **kwargs):
        if action == "placement.completed":
            completion_update_reached.set()
            if not release_completion.wait(timeout=5):
                raise TimeoutError("test did not release the completion transaction")
        return original_audit_write(cur, action, *args, **kwargs)

    monkeypatch.setattr(lc.audit, "write", pause_completion_audit)

    def complete():
        try:
            cmd(U["pc_sys"], lc.confirm_completion, p)
            outcomes["completion"] = ("OK", None)
        except Exception as exc:  # noqa: BLE001 - capture thread outcome for assertion
            outcomes["completion"] = (type(exc).__name__, getattr(exc, "code", str(exc)))

    def insert_hours_directly():
        raw = env.conn()
        try:
            raw.execute("SET application_name = 't04-race-hours'")
            raw.execute(
                "INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,%s)",
                (p, U["s1"], 1),
            )
            outcomes["hours"] = ("OK", None)
        except Exception as exc:  # noqa: BLE001 - capture trigger outcome for assertion
            outcomes["hours"] = (type(exc).__name__, str(exc))
        finally:
            raw.close()
            hours_done.set()

    completion_thread = threading.Thread(target=complete)
    hours_thread = threading.Thread(target=insert_hours_directly)
    completion_thread.start()
    assert completion_update_reached.wait(timeout=5), "completion did not reach its persisted state update"
    hours_thread.start()
    try:
        deadline = time.monotonic() + 5
        waiting_on_row_lock = False
        while time.monotonic() < deadline:
            assert not hours_done.is_set(), "hours insert bypassed the placement row lock"
            activity = env.admin.execute(
                """SELECT wait_event_type FROM pg_stat_activity
                   WHERE application_name='t04-race-hours' AND state='active'""",
            ).fetchone()
            if activity and activity["wait_event_type"] == "Lock":
                waiting_on_row_lock = True
                break
            time.sleep(0.01)
        assert waiting_on_row_lock, "hours insert did not wait for the completion transaction"
    finally:
        release_completion.set()
        completion_thread.join(timeout=5)
        hours_thread.join(timeout=5)

    assert not completion_thread.is_alive()
    assert not hours_thread.is_alive()
    assert outcomes["completion"] == ("OK", None)
    assert outcomes["hours"][0] == "RaiseException"
    assert "ACTIVE placement" in outcomes["hours"][1]
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == "COMPLETED"
    assert env.admin.execute(
        "SELECT coalesce(sum(hours),0) AS total FROM progress_entry WHERE placement_id=%s", (p,),
    ).fetchone()["total"] == 100


def test_lifecycle_record_database_guards_reject_unrelated_authors(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)

    raw = env.conn()
    try:
        with pytest.raises(psycopg.errors.RaiseException, match="authorized participant"):
            raw.execute(
                """INSERT INTO placement_incident(placement_id,kind,revision,reporter_id,summary,description)
                   VALUES (%s,'INCIDENT',1,%s,'Intento no autorizado','Debe ser rechazado por el trigger')""",
                (p, U["ws_alfa2"]),
            )
    finally:
        raw.close()

    raw = env.conn()
    try:
        with pytest.raises(psycopg.errors.RaiseException, match="currently assigned workplace supervisor"):
            raw.execute(
                """INSERT INTO placement_evaluation(placement_id,kind,revision,evaluator_id,narrative)
                   VALUES (%s,'MIDTERM',1,%s,'No es la persona supervisora vigente')""",
                (p, U["pc_sys"]),
            )
    finally:
        raw.close()


def test_incident_reports_keep_only_the_factual_immutable_reported_status(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)

    submitted = cmd(U["s1"], lc.create_incident, p, "INCIDENT", "Cambio reportado",
                    "Se registra la situación para consulta de participantes autorizados.")
    assert submitted["status"] == "REPORTED"
    with db.read() as cur:
        subject = lc.authz.subject(cur, U["s1"])
        incident = lc.list_incidents(cur, subject, p)[0]
    assert incident["status"] == "REPORTED"
    assert incident["reporter"] == "Student One"

    # Resolution/review statuses are deliberately not a workflow until approved.
    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        env.admin.execute(
            "UPDATE placement_incident SET status='RESOLVED' WHERE placement_id=%s", (p,),
        )


def test_work_plan_database_guard_enforces_assignment_revision_and_immutability(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)
    state_before = env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"]
    requirements_before = env.admin.execute(
        "SELECT kind,mandatory,satisfied,threshold FROM completion_requirement WHERE placement_id=%s ORDER BY kind",
        (p,),
    ).fetchall()
    assigned = cmd(U["ws_alfa"], lc.assign_work_plan_item, p, "Preparar informe", "Recopilar observaciones.")
    assert assigned["revision"] == 1
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == state_before
    assert env.admin.execute(
        "SELECT kind,mandatory,satisfied,threshold FROM completion_requirement WHERE placement_id=%s ORDER BY kind",
        (p,),
    ).fetchall() == requirements_before

    raw = env.conn()
    try:
        with pytest.raises(psycopg.errors.RaiseException, match="currently assigned workplace supervisor"):
            raw.execute(
                """INSERT INTO placement_work_plan_item(placement_id,revision,assigned_by,title,description)
                   VALUES (%s,2,%s,'Actividad ajena','No debe persistirse')""",
                (p, U["ws_alfa2"]),
            )
    finally:
        raw.close()

    raw = env.conn()
    try:
        with pytest.raises(psycopg.errors.RaiseException, match="revision must be sequential"):
            raw.execute(
                """INSERT INTO placement_work_plan_item(placement_id,revision,assigned_by,title,description)
                   VALUES (%s,3,%s,'Salto de revisión','Debe rechazarse')""",
                (p, U["ws_alfa"]),
            )
    finally:
        raw.close()

    with pytest.raises(psycopg.errors.RaiseException, match="append-only"):
        env.admin.execute(
            "UPDATE placement_work_plan_item SET title='Alterada' WHERE placement_id=%s", (p,),
        )

    assert env.admin.execute(
        "SELECT count(*) AS n FROM placement_work_plan_item WHERE placement_id=%s", (p,),
    ).fetchone()["n"] == 1

    cmd(U["s1"], lc.submit_completion_evidence, p, "FINAL_REPORT", "final.pdf",
        "application/pdf", b"%PDF-1.7 synthetic final report")
    cmd(U["ws_alfa"], lc.create_evaluation, p, "FINAL", "Evaluación narrativa sintética.")
    cmd(U["s1"], lc.record_hours, p, 100)
    cmd(U["pc_sys"], lc.confirm_completion, p)
    cmd(U["ec1"], lc.close_placement, p)

    with pytest.raises(BusinessError) as closed_assignment:
        cmd(U["ws_alfa"], lc.assign_work_plan_item, p, "Actividad posterior", "No debe persistirse.")
    assert closed_assignment.value.code == "PLACEMENT_CLOSED"
    raw = env.conn()
    try:
        with pytest.raises(psycopg.errors.RaiseException, match="after placement closure"):
            raw.execute(
                """INSERT INTO placement_work_plan_item(placement_id,revision,assigned_by,title,description)
                   VALUES (%s,2,%s,'Actividad posterior','No debe persistirse.')""",
                (p, U["ws_alfa"]),
            )
    finally:
        raw.close()
    assert env.admin.execute(
        "SELECT count(*) AS n FROM placement_work_plan_item WHERE placement_id=%s", (p,),
    ).fetchone()["n"] == 1


def test_t08_no_hours_before_activation(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_doc_pending(env, U, "s1", opp)
    with pytest.raises(BusinessError) as invalid:
        cmd(U["s1"], lc.record_hours, p, float("nan"))
    assert invalid.value.code == "INVALID_HOURS"
    with pytest.raises(BusinessError):
        cmd(U["s1"], lc.record_hours, p, 5)
    n = env.admin.execute("SELECT count(*) AS n FROM progress_entry WHERE placement_id=%s", (p,)).fetchone()["n"]
    assert n == 0


def _item_id(env, pid, kind="DOC_INSURANCE"):
    return env.admin.execute("SELECT id FROM checklist_item WHERE placement_id=%s AND kind=%s", (pid, kind)).fetchone()["id"]


def _satisfy_closure(env, U, student, p, hours=100):
    cmd(U[student], lc.submit_completion_evidence, p, "FINAL_REPORT", "informe-final.pdf",
        "application/pdf", b"%PDF-1.7 synthetic final report")
    cmd(U["ws_alfa"], lc.create_evaluation, p, "FINAL", "Evaluación narrativa documentada.")
    cmd(U[student], lc.record_hours, p, hours)


def test_t16a_reject_after_activation(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)
    item = _item_id(env, p)
    with db.read() as cur:
        assert lc.activation_noncompliant(cur, p) is False
    cmd(U["legal1"], lc.review_document, p, item, "REJECTED", "Documento vencido.")
    with db.read() as cur:
        assert lc.activation_noncompliant(cur, p) is True
    events = [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='checklist_item' AND subject_id=%s ORDER BY id", (item,)).fetchall()]
    assert events.count("checklist_item.rejected_after_activation") == 1
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == "ACTIVE"


def test_t16b_confirm_completion_noncompliant(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p_ok = make_active(env, U, "s2", opp)
    _satisfy_closure(env, U, "s2", p_ok)
    cmd(U["pc_sys"], lc.confirm_completion, p_ok)  # negative control passes

    p = make_active(env, U, "s1", opp)
    _satisfy_closure(env, U, "s1", p)
    cmd(U["legal1"], lc.review_document, p, _item_id(env, p), "REJECTED", "Documento vencido.")
    with pytest.raises(BusinessError) as ei:
        cmd(U["pc_sys"], lc.confirm_completion, p)
    assert ei.value.code == "ACTIVATION_NONCOMPLIANT"
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == "ACTIVE"


def test_t16c_direct_update_completed(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)
    cmd(U["legal1"], lc.review_document, p, _item_id(env, p), "REJECTED", "Documento vencido.")
    raw = env.conn()
    with pytest.raises(psycopg.errors.RaiseException):
        raw.execute("UPDATE placement SET state='COMPLETED' WHERE id=%s", (p,))
    raw.close()
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == "ACTIVE"


def test_t16d_redeliver_approve_close(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_active(env, U, "s1", opp)
    item = _item_id(env, p)
    _satisfy_closure(env, U, "s1", p)
    cmd(U["legal1"], lc.review_document, p, item, "REJECTED", "Documento vencido.")
    with pytest.raises(BusinessError):
        cmd(U["pc_sys"], lc.confirm_completion, p)
    cmd(U["s1"], lc.submit_document, p, item, "insurance.pdf", "application/pdf", b"%PDF-1.7 corrected synthetic document")
    cmd(U["legal1"], lc.review_document, p, item, "APPROVED", "Nueva versión vigente.")
    cmd(U["pc_sys"], lc.confirm_completion, p)
    cmd(U["ec1"], lc.close_placement, p)
    assert env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"] == "CLOSED"


def test_t16e_review_required(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_doc_pending(env, U, "s1", opp, docs_approved=False)
    item = _item_id(env, p)
    with pytest.raises(BusinessError) as ei:
        cmd(U["legal1"], lc.review_document, p, item, "APPROVED", "Documento revisado.")
    assert ei.value.code == "INVALID_TRANSITION"
    assert env.admin.execute("SELECT status FROM checklist_item WHERE id=%s", (item,)).fetchone()["status"] == "REQUIRED"
