"""C-06 lifecycle commands (ADR-003/005), ported from prototype/poc/lifecycle.py.

Each command runs inside ``db.command(actor_id)`` (ONE transaction under ``app_user``):
authorize -> lock placement -> evaluate guards from source rows -> mutate -> write audit.
``naive=True`` exists ONLY as a negative control (skips the placement row lock).
"""
from __future__ import annotations

import time
import hashlib
import math
from pathlib import PurePosixPath
import re

import psycopg

from app.db import CommandContext
from app.config import get_settings
from app.errors import BusinessError, Forbidden, NotFound
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


def _faculty_assignment_authorized(cur, subj: dict, pid: int, *, require_config: bool = True) -> bool:
    configured = get_settings().faculty_assigner_roles
    if require_config and not configured:
        raise BusinessError("FACULTY_ASSIGNMENT_AUTHORITY_UNCONFIGURED")
    return bool(configured) and authz.can_perform(cur, subj, "faculty_assignment:manage", pid) and any(
        role["role"] in configured for role in subj["roles"]
    )


def _lock_faculty_assignment_placement(ctx: CommandContext, pid: int) -> None:
    placement = ctx.execute("SELECT state FROM placement WHERE id=%s FOR UPDATE", (pid,)).fetchone()
    if placement is None:
        raise NotFound()
    if placement["state"] in {"COMPLETED", "CLOSED", "REJECTED", "CANCELLED"}:
        raise BusinessError("FACULTY_ASSIGNMENT_PLACEMENT_TERMINAL")


def faculty_assignment_options(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "placement:read", pid)
    if not _faculty_assignment_authorized(cur, subj, pid):
        raise Forbidden("the caller is not configured to manage faculty assignments for this practice")
    return cur.execute(
        """SELECT DISTINCT u.id, u.display_name FROM user_account u
           JOIN role_assignment ra ON ra.user_id=u.id
           WHERE ra.role='FACULTY_SUPERVISOR' AND u.is_active=true
           ORDER BY u.display_name, u.id""",
    ).fetchall()


def assign_faculty_supervisor(ctx: CommandContext, pid: int, faculty_user_id: int) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:read", pid)
    if not _faculty_assignment_authorized(ctx.cur, subj, pid):
        raise Forbidden("the caller is not configured to manage faculty assignments for this practice")
    _lock_faculty_assignment_placement(ctx, pid)
    target = ctx.execute(
        """SELECT 1 FROM user_account u JOIN role_assignment ra ON ra.user_id=u.id
           WHERE u.id=%s AND u.is_active=true AND ra.role='FACULTY_SUPERVISOR' LIMIT 1""",
        (faculty_user_id,),
    ).fetchone()
    if target is None:
        raise BusinessError("FACULTY_SUPERVISOR_INVALID")
    inserted = ctx.execute(
        """INSERT INTO supervisor_assignment(placement_id,user_id,kind)
           VALUES (%s,%s,'FACULTY') ON CONFLICT DO NOTHING RETURNING user_id""",
        (pid, faculty_user_id),
    ).fetchone()
    if inserted is None:
        raise BusinessError("FACULTY_ALREADY_ASSIGNED")
    audit.write(ctx.cur, "placement.faculty_supervisor_assigned", "placement", pid,
                None, {"faculty_user_id": faculty_user_id})


def unassign_faculty_supervisor(ctx: CommandContext, pid: int, faculty_user_id: int) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:read", pid)
    if not _faculty_assignment_authorized(ctx.cur, subj, pid):
        raise Forbidden("the caller is not configured to manage faculty assignments for this practice")
    _lock_faculty_assignment_placement(ctx, pid)
    deleted = ctx.execute(
        """DELETE FROM supervisor_assignment WHERE placement_id=%s AND user_id=%s AND kind='FACULTY'
           RETURNING user_id""",
        (pid, faculty_user_id),
    ).fetchone()
    if deleted is None:
        raise BusinessError("FACULTY_ASSIGNMENT_NOT_FOUND")
    audit.write(ctx.cur, "placement.faculty_supervisor_unassigned", "placement", pid,
                {"faculty_user_id": faculty_user_id}, None)


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
    # Recompute requirements from their persisted source rows, never from a client-set flag.
    requirements = ctx.execute(
        "SELECT id, kind, threshold, satisfied FROM completion_requirement WHERE placement_id=%s",
        (pid,),
    ).fetchall()
    hours_total = None
    for requirement in requirements:
        kind = requirement["kind"]
        satisfied = requirement["satisfied"]
        if kind == "MIN_HOURS":
            if hours_total is None:
                hours_total = ctx.execute(
                    "SELECT coalesce(sum(hours),0) AS total FROM progress_entry WHERE placement_id=%s",
                    (pid,),
                ).fetchone()["total"]
            satisfied = requirement["threshold"] is not None and hours_total >= requirement["threshold"]
        elif kind == "FINAL_REPORT":
            satisfied = ctx.execute(
                "SELECT EXISTS (SELECT 1 FROM completion_evidence WHERE placement_id=%s AND kind='FINAL_REPORT') AS present",
                (pid,),
            ).fetchone()["present"]
        elif kind == "FINAL_EVALUATION":
            satisfied = ctx.execute(
                "SELECT EXISTS (SELECT 1 FROM placement_evaluation WHERE placement_id=%s AND kind='FINAL') AS present",
                (pid,),
            ).fetchone()["present"]
        if satisfied != requirement["satisfied"]:
            ctx.execute("UPDATE completion_requirement SET satisfied=%s WHERE id=%s",
                        (satisfied, requirement["id"]))
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


def list_visible_placements(cur, subj: dict) -> list[dict]:
    """List only placements visible through the caller's current role relations."""
    ids = authz.visible_placement_ids(cur, subj)
    if not ids:
        return []
    return cur.execute(
        """SELECT pl.id, pl.state, a.state AS application_state, o.title AS opportunity_title,
                  o.state AS opportunity_state, org.name AS host_org_name, pr.code AS program_code,
                  pv.start_date, pv.end_date
           FROM placement pl
           JOIN application a ON a.id = pl.application_id
           JOIN opportunity o ON o.id = a.opportunity_id
           JOIN host_org org ON org.id = o.host_org_id
           JOIN academic_program pr ON pr.id = o.program_id
           LEFT JOIN placement_version pv ON pv.id = pl.current_version_id
           WHERE pl.id = ANY(%s)
           ORDER BY pl.id DESC""",
        (ids,),
    ).fetchall()


def _completion_requirement_status(cur, pid: int) -> list[dict]:
    """Read requirement state from its persisted source record, not its cached flag."""
    return cur.execute(
        """SELECT cr.kind, cr.mandatory, cr.threshold,
                  CASE
                    WHEN cr.kind = 'MIN_HOURS' THEN
                      cr.threshold IS NOT NULL AND
                      (SELECT coalesce(sum(pe.hours),0) FROM progress_entry pe
                       WHERE pe.placement_id=cr.placement_id) >= cr.threshold
                    WHEN cr.kind = 'FINAL_REPORT' THEN EXISTS (
                      SELECT 1 FROM completion_evidence ce
                      WHERE ce.placement_id=cr.placement_id AND ce.kind='FINAL_REPORT')
                    WHEN cr.kind = 'FINAL_EVALUATION' THEN EXISTS (
                      SELECT 1 FROM placement_evaluation ev
                      WHERE ev.placement_id=cr.placement_id AND ev.kind='FINAL')
                    ELSE cr.satisfied
                  END AS satisfied
           FROM completion_requirement cr WHERE cr.placement_id=%s ORDER BY cr.id""",
        (pid,),
    ).fetchall()


def get_dossier(cur, subj: dict, pid: int) -> dict:
    """Build a read-only dossier from persisted lifecycle records and existing gates."""
    ctx = authz.authorize(cur, subj, "placement:read", pid)
    row = cur.execute(
        """SELECT pl.id, pl.state, pl.application_id, pl.current_version_id,
                  pl.activation_requirements_instantiated, pl.completion_requirements_instantiated,
                  pl.activation_policy_version_id, pl.completion_policy_version_id,
                  a.state AS application_state, a.eligibility_result, a.policy_version_id AS eligibility_policy_version_id,
                  a.student_id,
                  student.display_name AS student_name, pr.code AS program_code, pr.name AS program_name,
                  o.id AS opportunity_id, o.title AS opportunity_title, o.state AS opportunity_state,
                  org.name AS host_org_name, pv.version_no AS current_version_no,
                  pv.start_date, pv.end_date, pv.location, pv.responsibilities,
                  pv.workplace_supervisor_id AS current_workplace_supervisor_id,
                  pv.status AS version_status, workplace.display_name AS workplace_supervisor_name
           FROM placement pl
           JOIN application a ON a.id = pl.application_id
           JOIN user_account student ON student.id = a.student_id
           LEFT JOIN LATERAL (
               SELECT ra.program_id FROM role_assignment ra
               WHERE ra.user_id = student.id AND ra.role = 'STUDENT' ORDER BY ra.id LIMIT 1
           ) student_role ON true
           LEFT JOIN academic_program pr ON pr.id = student_role.program_id
           JOIN opportunity o ON o.id = a.opportunity_id
           JOIN host_org org ON org.id = o.host_org_id
           LEFT JOIN placement_version pv ON pv.id = pl.current_version_id
           LEFT JOIN user_account workplace ON workplace.id = pv.workplace_supervisor_id
           WHERE pl.id = %s LIMIT 1""",
        (pid,),
    ).fetchone()
    if row is None:
        raise NotFound()

    external_only = bool(subj["roles"]) and all(
        role["role"] in authz.EXTERNAL for role in subj["roles"]
    )
    student = authz.external_student_view(cur, row["student_id"]) if external_only else {
        "display_name": row["student_name"], "program_code": row["program_code"],
        "program_name": row["program_name"],
    }
    eligibility = row["eligibility_result"]
    eligibility_result = eligibility.get("result") if isinstance(eligibility, dict) else None
    if eligibility_result not in {"ELIGIBLE", "INELIGIBLE", "NOT_ELIGIBLE"}:
        eligibility_result = None
    eligibility_policy = None
    if row["eligibility_policy_version_id"] is not None:
        eligibility_policy = cur.execute(
            "SELECT version_no FROM policy_version WHERE id=%s",
            (row["eligibility_policy_version_id"],),
        ).fetchone()

    versions = cur.execute(
        """SELECT v.version_no, v.start_date, v.end_date, v.location, v.responsibilities,
                  v.status, u.display_name AS workplace_supervisor_name
           FROM placement_version v LEFT JOIN user_account u ON u.id = v.workplace_supervisor_id
           WHERE v.placement_id = %s ORDER BY v.version_no""",
        (pid,),
    ).fetchall()
    faculty = cur.execute(
        """SELECT u.id, u.display_name FROM supervisor_assignment sa
           JOIN user_account u ON u.id = sa.user_id
           WHERE sa.placement_id = %s AND sa.kind = 'FACULTY' ORDER BY u.display_name""",
        (pid,),
    ).fetchall()
    can_read_faculty_history = authz.can_perform(cur, subj, "faculty_assignment:read_history", pid)
    faculty_assignment_history = cur.execute(
        """SELECT h.action, h.occurred_at, actor.display_name AS actor_name,
                  faculty.display_name AS faculty_name
           FROM placement_faculty_assignment_history h
           JOIN user_account actor ON actor.id=h.actor_id
           JOIN user_account faculty ON faculty.id=h.faculty_user_id
           WHERE h.placement_id=%s ORDER BY h.id""",
        (pid,),
    ).fetchall() if can_read_faculty_history else []
    can_manage_faculty_assignments = _faculty_assignment_authorized(cur, subj, pid, require_config=False)
    faculty_assignment_authority_configured = bool(get_settings().faculty_assigner_roles)
    may_configure_faculty_assignment = authz.can_perform(cur, subj, "faculty_assignment:manage", pid)
    coordinators = cur.execute(
        """SELECT DISTINCT u.display_name FROM role_assignment ra
           JOIN user_account u ON u.id = ra.user_id
           WHERE ra.role = 'PROGRAM_COORDINATOR' AND ra.program_id = %s ORDER BY u.display_name""",
        (ctx["student_program"],),
    ).fetchall()
    items = cur.execute(
        "SELECT id, kind, mandatory, status FROM checklist_item WHERE placement_id=%s ORDER BY id",
        (pid,),
    ).fetchall()
    activation_unmet_items = [
        item for item in items if item["mandatory"] and item["status"] != "APPROVED"
    ]
    activation_ready = (
        row["state"] == "DOCUMENTATION_PENDING"
        and row["activation_requirements_instantiated"]
        and not activation_unmet_items
    )

    can_read_documents = authz.can_perform(cur, subj, "document:read", pid)
    can_submit_documents = (
        authz.can_perform(cur, subj, "document:submit", pid)
        and row["state"] in ("DOCUMENTATION_PENDING", "ACTIVE")
        and any(item["kind"].startswith("DOC_") and item["status"] in ("REQUIRED", "REJECTED")
                for item in items)
    )
    can_read_hours = authz.can_perform(cur, subj, "progress:read", pid)
    can_record_hours = (
        authz.can_perform(cur, subj, "progress:create", pid) and row["state"] == "ACTIVE"
    )
    can_read_evidence = authz.can_perform(cur, subj, "evidence:read", pid)
    can_read_completion = can_read_hours or can_read_evidence or authz.can_perform(
        cur, subj, "placement:confirm_completion", pid
    ) or authz.can_perform(cur, subj, "placement:close", pid)
    can_read_progress_reports = authz.can_perform(cur, subj, "progress_report:read", pid)
    can_submit_progress_report = (
        authz.can_perform(cur, subj, "progress_report:create", pid) and row["state"] == "ACTIVE"
    )
    can_read_evaluations = authz.can_perform(cur, subj, "evaluation:read", pid)
    can_submit_evaluation = (
        authz.can_perform(cur, subj, "evaluation:create", pid)
        and row["state"] == "ACTIVE"
        and row["current_workplace_supervisor_id"] == subj["id"]
    )
    can_read_incidents = authz.can_perform(cur, subj, "incident:read", pid)
    can_report_incident = (
        authz.can_perform(cur, subj, "incident:create", pid) and row["state"] == "ACTIVE"
    )
    can_submit_completion_evidence = (
        authz.can_perform(cur, subj, "evidence:submit", pid)
        and row["state"] == "ACTIVE"
        and any(item["kind"] == "FINAL_REPORT" for item in cur.execute(
            "SELECT kind FROM completion_requirement WHERE placement_id=%s", (pid,)
        ).fetchall())
    )
    documents = None
    if can_read_documents:
        documents = []
        for item in items:
            submissions = list_submissions(cur, subj, pid, item["id"])
            documents.append({**item, "versions": submissions})

    hours = None
    hours_total = None
    if can_read_hours:
        hours = list_hours(cur, subj, pid)
        hours_total = sum((entry["hours"] for entry in hours), start=0)

    completion_requirements = None
    if can_read_completion:
        completion_requirements = _completion_requirement_status(cur, pid)

    progress_reports = list_progress_reports(cur, subj, pid) if can_read_progress_reports else None
    evaluations = list_evaluations(cur, subj, pid) if can_read_evaluations else None
    incidents = list_incidents(cur, subj, pid) if can_read_incidents else None
    completion_evidence = list_completion_evidence(cur, subj, pid) if can_read_evidence else None
    can_read_work_plan = authz.can_perform(cur, subj, "work_plan:read", pid)
    can_assign_work_plan = (
        authz.can_perform(cur, subj, "work_plan:assign", pid) and row["state"] != "CLOSED"
    )
    work_plan = list_work_plan(cur, subj, pid) if can_read_work_plan else None

    activation_policy = None
    completion_policy = None
    if row["activation_policy_version_id"] is not None:
        activation_policy = cur.execute(
            "SELECT version_no FROM policy_version WHERE id=%s",
            (row["activation_policy_version_id"],),
        ).fetchone()
    if row["completion_policy_version_id"] is not None:
        completion_policy = cur.execute(
            "SELECT version_no FROM policy_version WHERE id=%s",
            (row["completion_policy_version_id"],),
        ).fetchone()

    return {
        "placement": {
            "id": row["id"], "state": row["state"],
            "activation_requirements_instantiated": row["activation_requirements_instantiated"],
            "activation_ready": activation_ready,
            "activation_unmet": [item["kind"] for item in activation_unmet_items],
        },
        "application": {
            "id": row["application_id"], "state": row["application_state"],
            "eligibility_result": eligibility_result,
            "eligibility_policy_version": eligibility_policy["version_no"] if eligibility_policy else None,
        },
        "opportunity": {
            "id": row["opportunity_id"], "title": row["opportunity_title"],
            "state": row["opportunity_state"], "host_org_name": row["host_org_name"],
            "program_code": row["program_code"], "program_name": row["program_name"],
        },
        "student": student,
        "current_version": {
            "version_no": row["current_version_no"], "start_date": row["start_date"],
            "end_date": row["end_date"], "location": row["location"],
            "responsibilities": row["responsibilities"], "status": row["version_status"],
            "workplace_supervisor_name": row["workplace_supervisor_name"],
        } if row["current_version_id"] is not None else None,
        "versions": versions,
        "responsibles": {
            "program_coordinators": [person["display_name"] for person in coordinators],
            "faculty_supervisors": [person["display_name"] for person in faculty],
            "faculty_assignments": faculty,
            "faculty_assignment_history": faculty_assignment_history,
        },
        "activation_requirements": items,
        "completion_requirements": completion_requirements,
        "completion_requirements_configured": row["completion_requirements_instantiated"],
        "completion_policy_version": completion_policy["version_no"] if completion_policy else None,
        "activation_policy_version": activation_policy["version_no"] if activation_policy else None,
        "documents": documents,
        "hours": hours,
        "hours_total": hours_total,
        "progress_reports": progress_reports,
        "evaluations": evaluations,
        "incidents": incidents,
        "completion_evidence": completion_evidence,
        "work_plan": work_plan,
        "capabilities": {
            "read_documents": can_read_documents,
            "submit_documents": can_submit_documents,
            "read_hours": can_read_hours,
            "review_documents": (
                authz.can_perform(cur, subj, "document:review", pid)
                and any(item["status"] == "SUBMITTED" or
                        (row["state"] == "ACTIVE" and item["status"] == "APPROVED")
                        for item in items if item["kind"].startswith("DOC_"))
            ),
            "decide_academically": (
                authz.can_perform(cur, subj, "placement:approve_academic", pid)
                and row["state"] == "PENDING_ACADEMIC_APPROVAL"
            ),
            "record_hours": can_record_hours,
            "read_progress_reports": can_read_progress_reports,
            "submit_progress_report": can_submit_progress_report,
            "read_evaluations": can_read_evaluations,
            "submit_evaluation": can_submit_evaluation,
            "read_incidents": can_read_incidents,
            "report_incident": can_report_incident,
            "read_completion_evidence": can_read_evidence,
            "submit_completion_evidence": can_submit_completion_evidence,
            "read_joint_messages": authz.can_perform(cur, subj, "message:joint:read", pid),
            "read_academic_messages": authz.can_perform(cur, subj, "message:academic:read", pid),
            "manage_faculty_assignments": can_manage_faculty_assignments,
            "may_configure_faculty_assignments": may_configure_faculty_assignment,
            "faculty_assignment_authority_configured": faculty_assignment_authority_configured,
            "read_faculty_assignment_history": can_read_faculty_history,
            "read_work_plan": can_read_work_plan,
            "assign_work_plan_item": can_assign_work_plan,
            "activate": authz.can_perform(cur, subj, "placement:activate", pid) and activation_ready,
            "confirm_completion": (
                authz.can_perform(cur, subj, "placement:confirm_completion", pid)
                and row["state"] == "ACTIVE"
            ),
            "close_placement": (
                authz.can_perform(cur, subj, "placement:close", pid)
                and row["state"] == "COMPLETED"
            ),
        },
        "activity": audit.list_history(cur, pid),
    }


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


def submit_completion_evidence(ctx: CommandContext, pid: int, kind: str, filename: str,
                               content_type: str, content: bytes) -> dict:
    if kind != "FINAL_REPORT":
        raise BusinessError("COMPLETION_EVIDENCE_KIND_UNSUPPORTED")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "evidence:submit", pid)
    placement = _placement(ctx, pid)
    if placement is None:
        raise NotFound()
    if placement["state"] != "ACTIVE":
        raise BusinessError("PLACEMENT_NOT_ACTIVE", placement["state"])
    requirement = ctx.execute(
        "SELECT id FROM completion_requirement WHERE placement_id=%s AND kind=%s FOR UPDATE",
        (pid, kind),
    ).fetchone()
    if requirement is None:
        raise BusinessError("COMPLETION_REQUIREMENT_NOT_CONFIGURED", kind)
    safe_name, normalized_type = _safe_upload(filename, content_type, content)
    revision = ctx.execute(
        """SELECT coalesce(max(revision),0)+1 AS revision FROM completion_evidence
           WHERE placement_id=%s AND kind=%s""",
        (pid, kind),
    ).fetchone()["revision"]
    digest = hashlib.sha256(content).hexdigest()
    submission = ctx.execute(
        """INSERT INTO completion_evidence(placement_id,kind,revision,submitted_by,original_filename,
           content_type,content,byte_size,sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
           RETURNING submitted_at""",
        (pid, kind, revision, ctx.actor_id, safe_name, normalized_type, content, len(content), digest),
    ).fetchone()
    ctx.execute("UPDATE completion_requirement SET satisfied=true WHERE id=%s", (requirement["id"],))
    audit.write(ctx.cur, "completion_evidence.submitted", "placement", pid, None,
                {"kind": kind, "revision": revision, "content_type": normalized_type,
                 "byte_size": len(content), "sha256": digest})
    return {"kind": kind, "revision": revision, "submitted_at": submission["submitted_at"]}


def list_completion_evidence(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "evidence:read", pid)
    return cur.execute(
        """SELECT ce.kind, ce.revision, ce.original_filename, ce.content_type, ce.byte_size,
                  ce.sha256, ce.submitted_at, submitter.display_name AS submitted_by
           FROM completion_evidence ce JOIN user_account submitter ON submitter.id=ce.submitted_by
           WHERE ce.placement_id=%s ORDER BY ce.kind, ce.revision DESC""",
        (pid,),
    ).fetchall()


def get_completion_evidence(cur, subj: dict, pid: int, kind: str, revision: int) -> dict:
    authz.authorize(cur, subj, "evidence:read", pid)
    row = cur.execute(
        """SELECT original_filename, content_type, content FROM completion_evidence
           WHERE placement_id=%s AND kind=%s AND revision=%s""",
        (pid, kind, revision),
    ).fetchone()
    if row is None:
        raise NotFound()
    return row


def create_progress_report(ctx: CommandContext, pid: int, content: str) -> dict:
    clean_content = content.strip()
    if not clean_content or len(clean_content) > 5000:
        raise BusinessError("PROGRESS_REPORT_INVALID")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "progress_report:create", pid)
    placement = _placement(ctx, pid)
    if placement is None:
        raise NotFound()
    if placement["state"] != "ACTIVE":
        raise BusinessError("PLACEMENT_NOT_ACTIVE", placement["state"])
    revision = ctx.execute(
        "SELECT coalesce(max(revision),0)+1 AS revision FROM placement_progress_report WHERE placement_id=%s",
        (pid,),
    ).fetchone()["revision"]
    record = ctx.execute(
        """INSERT INTO placement_progress_report(placement_id,revision,author_id,content)
           VALUES (%s,%s,%s,%s) RETURNING created_at""",
        (pid, revision, ctx.actor_id, clean_content),
    ).fetchone()
    audit.write(ctx.cur, "progress.report_submitted", "placement", pid, None, {"revision": revision})
    return {"revision": revision, "created_at": record["created_at"]}


def list_progress_reports(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "progress_report:read", pid)
    return cur.execute(
        """SELECT r.revision, r.content, r.created_at, author.display_name AS author
           FROM placement_progress_report r JOIN user_account author ON author.id=r.author_id
           WHERE r.placement_id=%s ORDER BY r.revision DESC""",
        (pid,),
    ).fetchall()


def assign_work_plan_item(ctx: CommandContext, pid: int, title: str, description: str) -> dict:
    clean_title = title.strip()
    clean_description = description.strip()
    if not clean_title or len(clean_title) > 160 or not clean_description or len(clean_description) > 3000:
        raise BusinessError("WORK_PLAN_ITEM_INVALID")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "work_plan:assign", pid)
    placement = _placement(ctx, pid)
    if placement is None:
        raise NotFound()
    if placement["state"] == "CLOSED":
        raise BusinessError("PLACEMENT_CLOSED", placement["state"])
    current = ctx.execute(
        "SELECT workplace_supervisor_id FROM placement_version WHERE id=%s",
        (placement["current_version_id"],),
    ).fetchone()
    if current is None or current["workplace_supervisor_id"] != ctx.actor_id:
        raise Forbidden("only the currently assigned workplace supervisor may assign work-plan activities")
    revision = ctx.execute(
        "SELECT coalesce(max(revision),0)+1 AS revision FROM placement_work_plan_item WHERE placement_id=%s",
        (pid,),
    ).fetchone()["revision"]
    record = ctx.execute(
        """INSERT INTO placement_work_plan_item(placement_id,revision,assigned_by,title,description)
           VALUES (%s,%s,%s,%s,%s) RETURNING assigned_at""",
        (pid, revision, ctx.actor_id, clean_title, clean_description),
    ).fetchone()
    audit.write(ctx.cur, "work_plan.activity_assigned", "placement", pid, None, {"revision": revision})
    return {"revision": revision, "assigned_at": record["assigned_at"]}


def list_work_plan(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "work_plan:read", pid)
    return cur.execute(
        """SELECT w.revision, w.title, w.description, w.assigned_at,
                  u.display_name AS assigned_by
           FROM placement_work_plan_item w
           JOIN user_account u ON u.id=w.assigned_by
           WHERE w.placement_id=%s ORDER BY w.revision""",
        (pid,),
    ).fetchall()


def create_evaluation(ctx: CommandContext, pid: int, kind: str, narrative: str) -> dict:
    if kind not in {"MIDTERM", "FINAL"}:
        raise BusinessError("EVALUATION_KIND_INVALID")
    clean_narrative = narrative.strip()
    if not clean_narrative or len(clean_narrative) > 8000:
        raise BusinessError("EVALUATION_NARRATIVE_INVALID")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "evaluation:create", pid)
    placement = _placement(ctx, pid)
    if placement is None:
        raise NotFound()
    if placement["state"] != "ACTIVE":
        raise BusinessError("PLACEMENT_NOT_ACTIVE", placement["state"])
    current_supervisor = ctx.execute(
        "SELECT workplace_supervisor_id FROM placement_version WHERE id=%s",
        (placement["current_version_id"],),
    ).fetchone()
    if current_supervisor is None or current_supervisor["workplace_supervisor_id"] != ctx.actor_id:
        raise Forbidden("only the currently assigned workplace supervisor may submit an evaluation")
    revision = ctx.execute(
        "SELECT coalesce(max(revision),0)+1 AS revision FROM placement_evaluation WHERE placement_id=%s AND kind=%s",
        (pid, kind),
    ).fetchone()["revision"]
    record = ctx.execute(
        """INSERT INTO placement_evaluation(placement_id,kind,revision,evaluator_id,narrative)
           VALUES (%s,%s,%s,%s,%s) RETURNING submitted_at""",
        (pid, kind, revision, ctx.actor_id, clean_narrative),
    ).fetchone()
    if kind == "FINAL":
        ctx.execute(
            "UPDATE completion_requirement SET satisfied=true WHERE placement_id=%s AND kind='FINAL_EVALUATION'",
            (pid,),
        )
    audit.write(ctx.cur, "evaluation.submitted", "placement", pid, None,
                {"kind": kind, "revision": revision})
    return {"kind": kind, "revision": revision, "submitted_at": record["submitted_at"]}


def list_evaluations(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "evaluation:read", pid)
    return cur.execute(
        """SELECT e.kind, e.revision, e.narrative, e.submitted_at, evaluator.display_name AS evaluator
           FROM placement_evaluation e JOIN user_account evaluator ON evaluator.id=e.evaluator_id
           WHERE e.placement_id=%s ORDER BY e.submitted_at DESC, e.revision DESC""",
        (pid,),
    ).fetchall()


def create_incident(ctx: CommandContext, pid: int, kind: str, summary: str, description: str) -> dict:
    if kind not in {"INCIDENT", "CHANGE"}:
        raise BusinessError("INCIDENT_KIND_INVALID")
    clean_summary = summary.strip()
    clean_description = description.strip()
    if not clean_summary or len(clean_summary) > 160 or not clean_description or len(clean_description) > 5000:
        raise BusinessError("INCIDENT_REPORT_INVALID")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "incident:create", pid)
    placement = _placement(ctx, pid)
    if placement is None:
        raise NotFound()
    if placement["state"] != "ACTIVE":
        raise BusinessError("PLACEMENT_NOT_ACTIVE", placement["state"])
    revision = ctx.execute(
        "SELECT coalesce(max(revision),0)+1 AS revision FROM placement_incident WHERE placement_id=%s",
        (pid,),
    ).fetchone()["revision"]
    record = ctx.execute(
        """INSERT INTO placement_incident(placement_id,kind,revision,reporter_id,summary,description)
           VALUES (%s,%s,%s,%s,%s,%s) RETURNING status, reported_at""",
        (pid, kind, revision, ctx.actor_id, clean_summary, clean_description),
    ).fetchone()
    audit.write(ctx.cur, "placement.incident_reported" if kind == "INCIDENT" else "placement.change_reported",
                "placement", pid, None, {"kind": kind, "revision": revision})
    return {"kind": kind, "revision": revision, "status": record["status"],
            "reported_at": record["reported_at"]}


def list_incidents(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "incident:read", pid)
    return cur.execute(
        """SELECT i.kind, i.revision, i.status, i.summary, i.description, i.reported_at,
                  reporter.display_name AS reporter
           FROM placement_incident i JOIN user_account reporter ON reporter.id=i.reporter_id
           WHERE i.placement_id=%s ORDER BY i.revision DESC""",
        (pid,),
    ).fetchall()


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
        raise Forbidden("only legal reviewers may list pending documents")
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
        raise Forbidden("only experiential coordinators may list pending activation")
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


def record_hours(ctx: CommandContext, pid: int, hours: float) -> None:
    if not math.isfinite(hours) or hours <= 0:
        raise BusinessError("INVALID_HOURS")

    def run() -> None:
        subj = authz.subject(ctx.cur, ctx.actor_id)
        authz.authorize(ctx.cur, subj, "progress:create", pid)
        placement = _placement(ctx, pid)
        if placement["state"] != "ACTIVE":
            raise BusinessError("PLACEMENT_NOT_ACTIVE", placement["state"])
        ctx.execute("INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,%s)",
                    (pid, ctx.actor_id, hours))
        audit.write(ctx.cur, "progress.hours_recorded", "placement", pid, None, {"hours": hours})
    try:
        _gate(run)
    except BusinessError as exc:
        raise BusinessError("PLACEMENT_NOT_ACTIVE", exc.detail) from exc


def list_hours(cur: psycopg.Cursor, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "progress:read", pid)
    return cur.execute(
        "SELECT id, hours, created_at FROM progress_entry WHERE placement_id=%s ORDER BY id DESC",
        (pid,),
    ).fetchall()


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
