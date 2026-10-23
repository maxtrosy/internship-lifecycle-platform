"""C-06 lifecycle commands (ADR-003/005), ported from prototype/poc/lifecycle.py.

Each command runs inside ``db.command(actor_id)`` (ONE transaction under ``app_user``):
authorize -> lock placement -> evaluate guards from source rows -> mutate -> write audit.
``naive=True`` exists ONLY as a negative control (skips the placement row lock).
"""
from __future__ import annotations

import time

import psycopg

from app.db import CommandContext
from app.errors import BusinessError
from app.modules.audit import service as audit
from app.modules.authz import service as authz


def _placement(ctx: CommandContext, pid: int, lock: bool = True) -> dict:
    sql = "SELECT * FROM placement WHERE id=%s" + (" FOR UPDATE" if lock else "")
    return ctx.execute(sql, (pid,)).fetchone()


def activation_unmet(ctx: CommandContext, pid: int) -> list[str]:
    rows = ctx.execute(
        """SELECT kind, status FROM checklist_item
           WHERE placement_id=%s AND mandatory AND status<>'APPROVED' ORDER BY id""",
        (pid,),
    ).fetchall()
    return [f"{r['kind']}={r['status']}" for r in rows]


def activation_noncompliant(ctx: CommandContext, pid: int) -> bool:
    """BR-18 / OPEN-14 (proposal): DERIVED indicator, read from the SQL view (never stored)."""
    row = ctx.execute(
        "SELECT activation_noncompliant FROM v_placement_activation_compliance WHERE placement_id=%s",
        (pid,),
    ).fetchone()
    return bool(row["activation_noncompliant"]) if row else False


def completion_unmet(ctx: CommandContext, pid: int) -> list[str]:
    # Recompute hours from SOURCE rows, never from a cached flag (T-04).
    for r in ctx.execute(
        "SELECT * FROM completion_requirement WHERE placement_id=%s AND kind='MIN_HOURS'", (pid,)
    ).fetchall():
        total = ctx.execute(
            "SELECT coalesce(sum(hours),0) AS t FROM progress_entry WHERE placement_id=%s", (pid,)
        ).fetchone()["t"]
        ctx.execute("UPDATE completion_requirement SET satisfied=%s WHERE id=%s",
                    (total >= r["threshold"], r["id"]))
    rows = ctx.execute(
        """SELECT kind FROM completion_requirement
           WHERE placement_id=%s AND mandatory AND NOT satisfied ORDER BY id""",
        (pid,),
    ).fetchall()
    return [r["kind"] for r in rows]


def _gate(fn):
    try:
        return fn()
    except psycopg.errors.RaiseException as exc:  # DB safety net fired
        raise BusinessError("GATE_VIOLATION", str(exc).split("\n")[0]) from exc


def get_placement(ctx: CommandContext, pid: int) -> dict:
    return _placement(ctx, pid, lock=False)


def academic_approve(ctx: CommandContext, pid: int, required_kinds: list[str]) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:approve_academic", pid)
    p = _placement(ctx, pid)
    if p["state"] != "PENDING_ACADEMIC_APPROVAL":
        raise BusinessError("INVALID_TRANSITION", p["state"])
    for k in required_kinds:
        ctx.execute("INSERT INTO checklist_item(placement_id,kind) VALUES (%s,%s) ON CONFLICT DO NOTHING", (pid, k))
    ctx.execute(
        """INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,'COND_SUPERVISOR_ASSIGNED',
           CASE WHEN (SELECT workplace_supervisor_id FROM placement_version WHERE id=%s) IS NULL
           THEN 'REQUIRED' ELSE 'APPROVED' END) ON CONFLICT DO NOTHING""",
        (pid, p["current_version_id"]),
    )
    ctx.execute("UPDATE placement_version SET status='APPROVED', decided_by=%s WHERE id=%s",
                (ctx.actor_id, p["current_version_id"]))
    ctx.execute("UPDATE placement SET state='DOCUMENTATION_PENDING', activation_requirements_instantiated=true WHERE id=%s", (pid,))
    audit.write(ctx.cur, "placement.academic_approved", "placement", pid,
                 {"state": p["state"]},
                 {"state": "DOCUMENTATION_PENDING", "version_id": p["current_version_id"]})


def review_document(ctx: CommandContext, item_id: int, decision: str, naive: bool = False,
                    pause: float = 0.0) -> None:
    assert decision in ("APPROVED", "REJECTED")
    pid = ctx.execute("SELECT placement_id FROM checklist_item WHERE id=%s", (item_id,)).fetchone()["placement_id"]
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "document:review", pid)
    p = _placement(ctx, pid, lock=not naive)   # lock order: placement first, then item
    it = ctx.execute(
        "SELECT * FROM checklist_item WHERE id=%s" + (" FOR UPDATE" if not naive else ""),
        (item_id,),
    ).fetchone()
    status = it["status"]
    allowed = ((status == "SUBMITTED" and decision in ("APPROVED", "REJECTED"))
               or (status == "APPROVED" and decision == "REJECTED"))
    if not allowed:
        raise BusinessError("INVALID_TRANSITION", status)
    if pause:
        time.sleep(pause)
    ctx.execute("UPDATE checklist_item SET status=%s WHERE id=%s", (decision, item_id))
    action = f"checklist_item.{decision.lower()}"
    if decision == "REJECTED" and p["state"] == "ACTIVE":
        action = "checklist_item.rejected_after_activation"
    audit.write(ctx.cur, action, "checklist_item", item_id,
                 {"status": status}, {"status": decision, "placement_state": p["state"]})


def activate(ctx: CommandContext, pid: int, naive: bool = False, pause: float = 0.0) -> None:
    def run() -> None:
        subj = authz.subject(ctx.cur, ctx.actor_id)
        authz.authorize(ctx.cur, subj, "placement:activate", pid)
        p = _placement(ctx, pid, lock=not naive)
        if p["state"] != "DOCUMENTATION_PENDING":
            raise BusinessError("INVALID_TRANSITION", p["state"])
        unmet = activation_unmet(ctx, pid)
        if unmet:
            raise BusinessError("ACTIVATION_CONDITIONS_UNMET", unmet)
        if pause:
            time.sleep(pause)
        ctx.execute(
            """INSERT INTO completion_requirement(placement_id,kind,threshold) VALUES
               (%s,'FINAL_REPORT',NULL),(%s,'FINAL_EVALUATION',NULL),(%s,'MIN_HOURS',100)
               ON CONFLICT DO NOTHING""",
            (pid, pid, pid),
        )
        ctx.execute("UPDATE placement SET state='ACTIVE', completion_requirements_instantiated=true WHERE id=%s", (pid,))
        audit.write(ctx.cur, "placement.activated", "placement", pid,
                     {"state": p["state"]}, {"state": "ACTIVE"})
    _gate(run)


def submit_evidence(ctx: CommandContext, pid: int, kind: str) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "evidence:submit", pid)
    _placement(ctx, pid)
    ctx.execute("UPDATE completion_requirement SET satisfied=true WHERE placement_id=%s AND kind=%s", (pid, kind))
    audit.write(ctx.cur, "completion_requirement.satisfied", "placement", pid, None, {"kind": kind})


def record_hours(ctx: CommandContext, pid: int, hours: float) -> None:
    def run() -> None:
        subj = authz.subject(ctx.cur, ctx.actor_id)
        authz.authorize(ctx.cur, subj, "progress:create", pid)
        ctx.execute("INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,%s)",
                    (pid, ctx.actor_id, hours))
        audit.write(ctx.cur, "progress.hours_recorded", "placement", pid, None, {"hours": hours})
    try:
        _gate(run)
    except BusinessError as exc:
        raise BusinessError("PLACEMENT_NOT_ACTIVE", exc.detail) from exc


def confirm_completion(ctx: CommandContext, pid: int) -> None:
    def run() -> None:
        subj = authz.subject(ctx.cur, ctx.actor_id)
        authz.authorize(ctx.cur, subj, "placement:confirm_completion", pid)
        p = _placement(ctx, pid)
        if p["state"] != "ACTIVE":
            raise BusinessError("INVALID_TRANSITION", p["state"])
        if activation_noncompliant(ctx, pid):  # BR-18
            raise BusinessError("ACTIVATION_NONCOMPLIANT", activation_unmet(ctx, pid))
        unmet = completion_unmet(ctx, pid)
        if unmet:
            raise BusinessError("COMPLETION_EVIDENCE_MISSING", unmet)
        ctx.execute("UPDATE placement SET state='COMPLETED' WHERE id=%s", (pid,))
        audit.write(ctx.cur, "placement.completed", "placement", pid,
                     {"state": "ACTIVE"}, {"state": "COMPLETED"})
    _gate(run)


def close_placement(ctx: CommandContext, pid: int) -> None:
    def run() -> None:
        subj = authz.subject(ctx.cur, ctx.actor_id)
        authz.authorize(ctx.cur, subj, "placement:close", pid)
        p = _placement(ctx, pid)
        if p["state"] != "COMPLETED":
            raise BusinessError("INVALID_TRANSITION", p["state"])
        unmet_activation = activation_unmet(ctx, pid)  # BR-18
        if unmet_activation:
            raise BusinessError("ACTIVATION_NONCOMPLIANT", unmet_activation)
        unmet = completion_unmet(ctx, pid)
        if unmet:
            raise BusinessError("COMPLETION_EVIDENCE_MISSING", unmet)
        ctx.execute("UPDATE placement SET state='CLOSED' WHERE id=%s", (pid,))
        audit.write(ctx.cur, "placement.closed", "placement", pid,
                     {"state": "COMPLETED"}, {"state": "CLOSED"})
    _gate(run)


def propose_change(ctx: CommandContext, pid: int, **changes) -> int:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:propose_change", pid)
    p = _placement(ctx, pid)
    cur_v = ctx.execute("SELECT * FROM placement_version WHERE id=%s", (p["current_version_id"],)).fetchone()
    n = ctx.execute("SELECT max(version_no)+1 AS n FROM placement_version WHERE placement_id=%s", (pid,)).fetchone()["n"]
    new = {k: cur_v[k] for k in ("workplace_supervisor_id", "start_date", "end_date", "location", "responsibilities")}
    new.update(changes)
    v = ctx.execute(
        """INSERT INTO placement_version(placement_id,version_no,workplace_supervisor_id,start_date,end_date,
           location,responsibilities,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'PROPOSED') RETURNING id""",
        (pid, n, new["workplace_supervisor_id"], new["start_date"], new["end_date"],
         new["location"], new["responsibilities"]),
    ).fetchone()
    audit.write(ctx.cur, "placement.change_proposed", "placement_version", v["id"],
                 {"version_no": cur_v["version_no"], "location": cur_v["location"]},
                 {"version_no": n, "location": new["location"], "changed": sorted(changes)})
    return v["id"]


def approve_version(ctx: CommandContext, vid: int) -> None:
    v = ctx.execute("SELECT * FROM placement_version WHERE id=%s", (vid,)).fetchone()
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "version:approve", v["placement_id"])
    p = _placement(ctx, v["placement_id"])
    if v["status"] != "PROPOSED":
        raise BusinessError("INVALID_TRANSITION", v["status"])
    old = ctx.execute("SELECT * FROM placement_version WHERE id=%s", (p["current_version_id"],)).fetchone()
    ctx.execute("UPDATE placement_version SET status='APPROVED', decided_by=%s WHERE id=%s", (ctx.actor_id, vid))
    ctx.execute("UPDATE placement SET current_version_id=%s WHERE id=%s", (vid, p["id"]))
    audit.write(ctx.cur, "placement.version_approved", "placement", p["id"],
                 {"version_no": old["version_no"], "location": old["location"]},
                 {"version_no": v["version_no"], "location": v["location"]})
