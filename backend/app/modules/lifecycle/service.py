"""C-06 lifecycle commands (ADR-003/005), ported from prototype/poc/lifecycle.py.

Each command runs inside ``db.command(actor_id)`` (ONE transaction under ``app_user``):
authorize -> lock placement -> evaluate guards from source rows -> mutate -> write audit.
``naive=True`` exists ONLY as a negative control (skips the placement row lock).
"""
from __future__ import annotations

import time
import hashlib
from pathlib import PurePosixPath
import re

import psycopg

from app.db import CommandContext
from app.errors import BusinessError, NotFound
from app.modules.audit import service as audit
from app.modules.authz import service as authz
from app.modules.policies import service as policies

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
_DOCUMENT_TYPES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", b"PK\x03\x04"),
}


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


def academic_approve(ctx: CommandContext, pid: int) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:approve_academic", pid)
    p = _placement(ctx, pid)
    if p["state"] != "PENDING_ACADEMIC_APPROVAL":
        raise BusinessError("INVALID_TRANSITION", p["state"])
    program_code = ctx.execute(
        """SELECT p.code FROM academic_program p
           JOIN role_assignment ra ON ra.program_id = p.id AND ra.role = 'STUDENT'
           JOIN application a ON a.student_id = ra.user_id
           WHERE a.id = %s LIMIT 1""",
        (p["application_id"],),
    ).fetchone()["code"]
    activation_policy = policies.latest_policy(ctx.cur, program_code, "ACTIVATION")
    completion_policy = policies.latest_policy(ctx.cur, program_code, "COMPLETION")
    if activation_policy is None:
        raise BusinessError("ACTIVATION_POLICY_MISSING", program_code)
    if completion_policy is None:
        raise BusinessError("COMPLETION_POLICY_MISSING", program_code)

    activation_conditions = activation_policy["conditions"]
    kinds = [kind for condition in activation_conditions if condition["type"] == "REQUIRE_DOCUMENTS"
             for kind in condition["value"]]
    for k in kinds:
        ctx.execute("INSERT INTO checklist_item(placement_id,kind) VALUES (%s,%s) ON CONFLICT DO NOTHING", (pid, k))
    if any(c["type"] == "SUPERVISORS_ASSIGNED" and c["value"] for c in activation_conditions):
        ctx.execute(
            """INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,'COND_SUPERVISOR_ASSIGNED',
               CASE WHEN (SELECT workplace_supervisor_id FROM placement_version WHERE id=%s) IS NULL
               THEN 'REQUIRED' ELSE 'APPROVED' END) ON CONFLICT DO NOTHING""",
            (pid, p["current_version_id"]),
        )
    for requirement in policies.completion_requirements(ctx.cur, completion_policy["id"]):
        ctx.execute(
            """INSERT INTO completion_requirement(placement_id,kind,threshold)
               VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
            (pid, requirement["kind"], requirement["threshold"]),
        )
    ctx.execute("UPDATE placement_version SET status='APPROVED', decided_by=%s WHERE id=%s",
                (ctx.actor_id, p["current_version_id"]))
    ctx.execute(
        """UPDATE placement SET state='DOCUMENTATION_PENDING', activation_requirements_instantiated=true,
           completion_requirements_instantiated=true, activation_policy_version_id=%s,
           completion_policy_version_id=%s WHERE id=%s""",
        (activation_policy["id"], completion_policy["id"], pid),
    )
    audit.write(ctx.cur, "placement.academic_approved", "placement", pid,
                 {"state": p["state"]},
                 {"state": "DOCUMENTATION_PENDING", "version_id": p["current_version_id"],
                  "activation_policy_version_id": activation_policy["id"],
                  "completion_policy_version_id": completion_policy["id"]})


def academic_reject(ctx: CommandContext, pid: int, reason: str) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:reject_academic", pid)
    p = _placement(ctx, pid)
    if p["state"] != "PENDING_ACADEMIC_APPROVAL":
        raise BusinessError("INVALID_TRANSITION", p["state"])
    ctx.execute("UPDATE placement SET state='REJECTED' WHERE id=%s", (pid,))
    ctx.execute("UPDATE application SET state='REJECTED' WHERE id=%s", (p["application_id"],))
    audit.write(ctx.cur, "placement.academic_rejected", "placement", pid,
                {"state": p["state"]}, {"state": "REJECTED", "reason": reason})


def list_pending_academic(cur, subj: dict) -> list[dict]:
    """Placements awaiting academic review, scoped to the coordinator's programs."""
    prog_ids = [r["program_id"] for r in subj["roles"]
                if r["role"] == "PROGRAM_COORDINATOR" and r["program_id"] is not None]
    if not prog_ids:
        return []
    return cur.execute(
        """SELECT pl.id, pl.state, a.id AS application_id, a.student_id,
                  u.display_name, p.code AS program_code, o.title AS opportunity_title
           FROM placement pl
           JOIN application a ON a.id = pl.application_id
           JOIN user_account u ON u.id = a.student_id
           JOIN role_assignment ra ON ra.user_id = a.student_id AND ra.role = 'STUDENT'
           JOIN academic_program p ON p.id = ra.program_id
           JOIN opportunity o ON o.id = a.opportunity_id
           WHERE pl.state = 'PENDING_ACADEMIC_APPROVAL' AND p.id = ANY(%s)
           ORDER BY pl.id""",
        (prog_ids,),
    ).fetchall()


def _item_placement(ctx: CommandContext, item_id: int) -> int:
    row = ctx.execute("SELECT placement_id FROM checklist_item WHERE id=%s", (item_id,)).fetchone()
    if row is None:
        raise NotFound()
    return row["placement_id"]


def _safe_upload(filename: str, content_type: str, content: bytes) -> tuple[str, str]:
    normalized = filename.replace("\\", "/")
    safe_name = PurePosixPath(normalized).name.strip()
    if not safe_name or len(safe_name) > 255 or re.search(r"[\x00-\x1f\x7f]", safe_name):
        raise BusinessError("DOCUMENT_FILENAME_INVALID")
    if not content:
        raise BusinessError("DOCUMENT_EMPTY")
    if len(content) > MAX_DOCUMENT_BYTES:
        raise BusinessError("DOCUMENT_TOO_LARGE", {"max_bytes": MAX_DOCUMENT_BYTES})
    extension = PurePosixPath(safe_name).suffix.lower()
    supported = _DOCUMENT_TYPES.get(extension)
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    if supported is None or normalized_type != supported[0] or not content.startswith(supported[1]):
        raise BusinessError("DOCUMENT_TYPE_UNSUPPORTED", "Supported files: PDF, PNG, JPG, DOCX")
    return safe_name, normalized_type


def submit_document(ctx: CommandContext, pid: int, item_id: int, filename: str,
                    content_type: str, content: bytes) -> dict:
    """Store a real document revision and mark it as the current submission (BR-14)."""
    actual_pid = _item_placement(ctx, item_id)
    if actual_pid != pid:
        raise NotFound()
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "document:submit", pid)
    placement = _placement(ctx, pid)
    if placement["state"] not in ("DOCUMENTATION_PENDING", "ACTIVE"):
        raise BusinessError("INVALID_TRANSITION", placement["state"])
    it = ctx.execute("SELECT * FROM checklist_item WHERE id=%s FOR UPDATE", (item_id,)).fetchone()
    if not it["kind"].startswith("DOC_"):
        raise BusinessError("DOCUMENT_NOT_UPLOADABLE", it["kind"])
    if it["status"] not in ("REQUIRED", "REJECTED"):
        raise BusinessError("INVALID_TRANSITION", it["status"])
    safe_name, normalized_type = _safe_upload(filename, content_type, content)
    revision = ctx.execute(
        "SELECT coalesce(max(revision),0)+1 AS revision FROM document_submission WHERE checklist_item_id=%s",
        (item_id,),
    ).fetchone()["revision"]
    submission = ctx.execute(
        """INSERT INTO document_submission(checklist_item_id,revision,submitted_by,original_filename,
           content_type,content,byte_size,sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
           RETURNING id, submitted_at""",
        (item_id, revision, ctx.actor_id, safe_name, normalized_type, content, len(content),
         hashlib.sha256(content).hexdigest()),
    ).fetchone()
    ctx.execute(
        """UPDATE checklist_item SET status='SUBMITTED', current_submission_id=%s,
           current_review_reason=NULL WHERE id=%s""",
        (submission["id"], item_id),
    )
    audit.write(ctx.cur, "checklist_item.submitted", "checklist_item", item_id,
                {"status": it["status"], "submission_id": it["current_submission_id"]},
                {"status": "SUBMITTED", "submission_id": submission["id"], "revision": revision,
                 "filename": safe_name, "content_type": normalized_type, "byte_size": len(content),
                 "sha256": hashlib.sha256(content).hexdigest()})
    return {"id": submission["id"], "revision": revision, "submitted_at": submission["submitted_at"]}


def list_checklist(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "placement:read", pid)
    return cur.execute(
        "SELECT id, kind, mandatory, status FROM checklist_item WHERE placement_id=%s ORDER BY id",
        (pid,),
    ).fetchall()


def list_submissions(cur, subj: dict, pid: int, item_id: int) -> list[dict]:
    authz.authorize(cur, subj, "document:read", pid)
    item = cur.execute("SELECT placement_id FROM checklist_item WHERE id=%s", (item_id,)).fetchone()
    if item is None or item["placement_id"] != pid:
        raise NotFound()
    return cur.execute(
        """SELECT ds.id, ds.revision, ds.original_filename, ds.content_type, ds.byte_size,
                  ds.sha256, ds.submitted_at, u.display_name AS submitted_by,
                  dr.decision, dr.reason, dr.reviewed_at, reviewer.display_name AS reviewer
           FROM document_submission ds
           JOIN user_account u ON u.id=ds.submitted_by
           LEFT JOIN LATERAL (
             SELECT decision, reason, reviewed_at, reviewer_id FROM document_review
             WHERE submission_id=ds.id ORDER BY id DESC LIMIT 1
           ) dr ON true
           LEFT JOIN user_account reviewer ON reviewer.id=dr.reviewer_id
           WHERE ds.checklist_item_id=%s ORDER BY ds.revision DESC""",
        (item_id,),
    ).fetchall()


def get_submission(cur, subj: dict, pid: int, item_id: int, submission_id: int) -> dict:
    authz.authorize(cur, subj, "document:read", pid)
    row = cur.execute(
        """SELECT original_filename, content_type, content FROM document_submission
           WHERE id=%s AND checklist_item_id=%s AND checklist_item_id IN
             (SELECT id FROM checklist_item WHERE id=%s AND placement_id=%s)""",
        (submission_id, item_id, item_id, pid),
    ).fetchone()
    if row is None:
        raise NotFound()
    return row


def activation_status(cur, subj: dict, pid: int) -> dict:
    authz.authorize(cur, subj, "placement:read", pid)
    p = cur.execute("SELECT * FROM placement WHERE id=%s", (pid,)).fetchone()
    items = cur.execute(
        "SELECT id, kind, mandatory, status FROM checklist_item WHERE placement_id=%s ORDER BY id",
        (pid,),
    ).fetchall()
    unmet = [f"{r['kind']}={r['status']}" for r in items if r["mandatory"] and r["status"] != "APPROVED"]
    row = cur.execute(
        "SELECT activation_noncompliant FROM v_placement_activation_compliance WHERE placement_id=%s",
        (pid,),
    ).fetchone()
    return {
        "placement_id": pid,
        "state": p["state"],
        "activation_requirements_instantiated": p["activation_requirements_instantiated"],
        "activation_noncompliant": bool(row["activation_noncompliant"]) if row else False,
        "ready_to_activate": p["state"] == "DOCUMENTATION_PENDING" and not unmet,
        "unmet": unmet,
        "items": items,
    }


def list_documents_pending(cur, subj: dict) -> list[dict]:
    if not any(r["role"] == "LEGAL_REVIEWER" for r in subj["roles"]):
        raise BusinessError("FORBIDDEN")
    return cur.execute(
        """SELECT DISTINCT pl.id, pl.state, u.display_name, p.code AS program_code, o.title AS opportunity_title
           FROM checklist_item ci JOIN placement pl ON pl.id = ci.placement_id
           JOIN application a ON a.id = pl.application_id
           JOIN user_account u ON u.id = a.student_id
           JOIN role_assignment ra ON ra.user_id = a.student_id AND ra.role = 'STUDENT'
           JOIN academic_program p ON p.id = ra.program_id
           JOIN opportunity o ON o.id = a.opportunity_id
           WHERE left(ci.kind,4) = 'DOC_' AND
             (ci.status = 'SUBMITTED' OR (pl.state = 'ACTIVE' AND ci.status = 'APPROVED'))
           ORDER BY pl.id""",
    ).fetchall()


def list_pending_activation(cur, subj: dict) -> list[dict]:
    if not any(r["role"] == "EXPERIENTIAL_COORDINATOR" for r in subj["roles"]):
        raise BusinessError("FORBIDDEN")
    return cur.execute(
        """SELECT pl.id, pl.state, u.display_name, p.code AS program_code, o.title AS opportunity_title
           FROM placement pl JOIN application a ON a.id = pl.application_id
           JOIN user_account u ON u.id = a.student_id
           JOIN role_assignment ra ON ra.user_id = a.student_id AND ra.role = 'STUDENT'
           JOIN academic_program p ON p.id = ra.program_id
           JOIN opportunity o ON o.id = a.opportunity_id
           WHERE pl.state = 'DOCUMENTATION_PENDING' ORDER BY pl.id""",
    ).fetchall()


def review_document(ctx: CommandContext, pid: int, item_id: int, decision: str, reason: str,
                    naive: bool = False, pause: float = 0.0) -> None:
    if decision not in ("APPROVED", "REJECTED"):
        raise BusinessError("DOCUMENT_DECISION_INVALID")
    actual_pid = _item_placement(ctx, item_id)
    if actual_pid != pid:
        raise NotFound()
    clean_reason = reason.strip()
    if not clean_reason or len(clean_reason) > 1000:
        raise BusinessError("DOCUMENT_REVIEW_REASON_REQUIRED")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "document:review", pid)
    p = _placement(ctx, pid, lock=not naive)   # lock order: placement first, then item
    it = ctx.execute(
        "SELECT * FROM checklist_item WHERE id=%s" + (" FOR UPDATE" if not naive else ""),
        (item_id,),
    ).fetchone()
    if not it["kind"].startswith("DOC_"):
        raise BusinessError("DOCUMENT_NOT_REVIEWABLE", it["kind"])
    status = it["status"]
    allowed = ((status == "SUBMITTED" and decision in ("APPROVED", "REJECTED"))
               or (status == "APPROVED" and decision == "REJECTED"))
    if not allowed:
        raise BusinessError("INVALID_TRANSITION", status)
    if status == "SUBMITTED" and it["current_submission_id"] is None:
        raise BusinessError("DOCUMENT_SUBMISSION_MISSING")
    if pause:
        time.sleep(pause)
    ctx.execute(
        """INSERT INTO document_review(checklist_item_id,submission_id,reviewer_id,decision,reason)
           VALUES (%s,%s,%s,%s,%s)""",
        (item_id, it["current_submission_id"], ctx.actor_id, decision, clean_reason),
    )
    ctx.execute("UPDATE checklist_item SET status=%s WHERE id=%s", (decision, item_id))
    ctx.execute("UPDATE checklist_item SET current_review_reason=%s WHERE id=%s", (clean_reason, item_id))
    action = f"checklist_item.{decision.lower()}"
    if decision == "REJECTED" and p["state"] == "ACTIVE":
        action = "checklist_item.rejected_after_activation"
    audit.write(ctx.cur, action, "checklist_item", item_id,
                 {"status": status}, {"status": decision, "placement_state": p["state"],
                  "reason": clean_reason, "submission_id": it["current_submission_id"]})


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
        if not p["completion_requirements_instantiated"] or p["completion_policy_version_id"] is None:
            raise BusinessError("COMPLETION_POLICY_MISSING")
        ctx.execute("UPDATE placement SET state='ACTIVE' WHERE id=%s", (pid,))
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
