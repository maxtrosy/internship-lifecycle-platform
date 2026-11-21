"""C-02 authorization (ADR-004): role AND relationship, with multiple role assignments.

External roles receive `NotFound` (no existence disclosure) when there is no relationship;
internal roles receive `Forbidden`. A subject may hold several roles; access is granted when
ANY of its role assignments allows it.
"""
from __future__ import annotations

from typing import Any

import psycopg

from app.config import get_settings
from app.errors import Forbidden, NotFound

EXTERNAL = {"HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR"}
GLOBAL_ROLES = {"EXPERIENTIAL_COORDINATOR", "LEGAL_REVIEWER"}


def subject(cur: psycopg.Cursor, user_id: int) -> dict | None:
    # Password hashes are never needed by authorization or response projections.
    # Naming the columns also lets the isolated catalog bootstrap role omit access
    # to credential material while still using the normal opportunity services.
    u = cur.execute(
        """SELECT id, username, email, is_active, display_name, credits, academic_level
           FROM user_account WHERE id = %s""",
        (user_id,),
    ).fetchone()
    if u is None:
        return None
    u["roles"] = cur.execute(
        "SELECT role, program_id, host_org_id FROM role_assignment WHERE user_id = %s ORDER BY id",
        (user_id,),
    ).fetchall()
    return u


def _ctx(cur: psycopg.Cursor, subj: dict, pid: int) -> dict | None:
    """Relationship context. CR-05: once a practice has segments, workplace
    supervision follows the segment (open = PLANNED/ACTIVE, operational = ACTIVE);
    a supervisor whose segment ended keeps no current relationship (CR-05-BR-06)."""
    return cur.execute(
        """SELECT p.id, p.state, a.student_id,
                  (SELECT ra.program_id FROM role_assignment ra
                   WHERE ra.user_id = a.student_id AND ra.role = 'STUDENT' LIMIT 1) AS student_program,
                  o.host_org_id,
                  EXISTS (SELECT 1 FROM placement_segment s WHERE s.placement_id = p.id) AS has_segments,
                  EXISTS (SELECT 1 FROM placement_version v WHERE v.placement_id = p.id
                          AND v.workplace_supervisor_id = %(u)s) AS is_version_sup,
                  EXISTS (SELECT 1 FROM placement_version v WHERE v.id = p.current_version_id
                          AND v.workplace_supervisor_id = %(u)s) AS is_current_version_sup,
                  ARRAY(SELECT s.host_org_id FROM placement_segment s WHERE s.placement_id = p.id
                        AND s.workplace_supervisor_id = %(u)s
                        AND s.status IN ('PLANNED','ACTIVE')) AS open_sup_orgs,
                  ARRAY(SELECT s.host_org_id FROM placement_segment s WHERE s.placement_id = p.id
                        AND s.workplace_supervisor_id = %(u)s AND s.status = 'ACTIVE') AS active_sup_orgs,
                  ARRAY(SELECT DISTINCT s.host_org_id FROM placement_segment s
                        WHERE s.placement_id = p.id AND s.status <> 'CANCELLED') AS segment_orgs,
                  EXISTS (SELECT 1 FROM supervisor_assignment sa WHERE sa.placement_id = p.id
                          AND sa.user_id = %(u)s AND sa.kind = 'FACULTY') AS is_faculty_sup
           FROM placement p JOIN application a ON a.id = p.application_id
           JOIN user_account s ON s.id = a.student_id
           JOIN opportunity o ON o.id = a.opportunity_id
           WHERE p.id = %(p)s""",
        {"u": subj["id"], "p": pid},
    ).fetchone()


def _ws_relation(role: dict, c: dict) -> bool:
    """Workplace supervisor with an open (planned/active) relationship."""
    if role["role"] != "WORKPLACE_SUPERVISOR":
        return False
    if c["has_segments"]:
        return role["host_org_id"] in c["open_sup_orgs"]
    return c["host_org_id"] == role["host_org_id"] and c["is_version_sup"]


def _ws_operational(role: dict, c: dict) -> bool:
    """Workplace supervisor of the ACTIVE segment (or current version before activation)."""
    if role["role"] != "WORKPLACE_SUPERVISOR":
        return False
    if c["has_segments"]:
        return role["host_org_id"] in c["active_sup_orgs"]
    return c["host_org_id"] == role["host_org_id"] and c["is_current_version_sup"]


def _role_read(role: dict, c: dict, subj: dict) -> bool:
    r = role["role"]
    if r == "STUDENT":
        return c["student_id"] == subj["id"]
    if r == "HOST_ORG_MEMBER":
        return c["host_org_id"] == role["host_org_id"] or role["host_org_id"] in c["segment_orgs"]
    if r == "WORKPLACE_SUPERVISOR":
        return _ws_relation(role, c)
    if r == "FACULTY_SUPERVISOR":
        return c["is_faculty_sup"]
    if r == "PROGRAM_COORDINATOR":
        return c["student_program"] == role["program_id"]
    return r in GLOBAL_ROLES


def can_read(cur: psycopg.Cursor, subj: dict, pid: int) -> bool:
    c = _ctx(cur, subj, pid)
    if c is None:
        return False
    return any(_role_read(r, c, subj) for r in subj["roles"])


def can_perform(cur: psycopg.Cursor, subj: dict, action: str, pid: int) -> bool:
    """Return whether an already authenticated subject may perform an action.

    This is used only to shape optional sections/capabilities in a read projection;
    mutations and resource endpoints still call ``authorize`` independently.
    """
    c = _ctx(cur, subj, pid)
    return bool(
        c is not None
        and any(_role_read(r, c, subj) for r in subj["roles"])
        and any(_role_action(r, c, subj, action) for r in subj["roles"])
    )


def _role_action(role: dict, c: dict, subj: dict, action: str) -> bool:
    r = role["role"]
    own_program = r == "PROGRAM_COORDINATOR" and c["student_program"] == role["program_id"]
    student_owner = r == "STUDENT" and c["student_id"] == subj["id"]
    workplace_supervisor = _ws_relation(role, c)
    current_workplace_supervisor = _ws_operational(role, c)
    faculty_supervisor = r == "FACULTY_SUPERVISOR" and c["is_faculty_sup"]
    if action in {"segment:manage", "hours:review", "progress:read"}:
        settings = get_settings()
        # CR-05: authority is relationship AND an institutionally configured role.
        segment_manager = r in settings.segment_manager_roles and (
            own_program or r == "EXPERIENTIAL_COORDINATOR")
        hours_reviewer = r in settings.hours_reviewer_roles and (
            current_workplace_supervisor or faculty_supervisor or own_program
            or r == "EXPERIENTIAL_COORDINATOR")
        if action == "segment:manage":
            return segment_manager
        if action == "hours:review":
            return hours_reviewer
        return (r == "STUDENT" and c["student_id"] == subj["id"]) or hours_reviewer
    return {
        "placement:read": True,
        "placement:approve_academic": own_program,
        "placement:reject_academic": own_program,
        "version:approve": own_program,
        "placement:confirm_completion": own_program,
        "placement:activate": r == "EXPERIENTIAL_COORDINATOR",
        "placement:close": r == "EXPERIENTIAL_COORDINATOR",
        "document:review": r == "LEGAL_REVIEWER",
        "document:read": r == "LEGAL_REVIEWER"
                          or (r == "STUDENT" and c["student_id"] == subj["id"]),
        "placement:propose_change": r == "EXPERIENTIAL_COORDINATOR" or workplace_supervisor,
        "progress:create": r == "STUDENT" and c["student_id"] == subj["id"],
        "progress_report:create": student_owner,
        "progress_report:read": student_owner or workplace_supervisor or faculty_supervisor
                                or own_program or r == "EXPERIENTIAL_COORDINATOR",
        "evaluation:create": current_workplace_supervisor,
        "evaluation:read": student_owner or workplace_supervisor or faculty_supervisor
                           or own_program or r == "EXPERIENTIAL_COORDINATOR",
        "incident:create": student_owner or workplace_supervisor or faculty_supervisor
                          or own_program or r == "EXPERIENTIAL_COORDINATOR",
        "incident:read": student_owner or workplace_supervisor or faculty_supervisor
                         or own_program or r == "EXPERIENTIAL_COORDINATOR",
        "evidence:read": student_owner or faculty_supervisor or own_program
                         or r == "EXPERIENTIAL_COORDINATOR",
        "evidence:submit": student_owner,
        "document:submit": r == "STUDENT" and c["student_id"] == subj["id"],
        "work_plan:read": student_owner or workplace_supervisor or faculty_supervisor or own_program
                          or r == "EXPERIENTIAL_COORDINATOR",
        "work_plan:assign": current_workplace_supervisor,
        # CR-05 segments and transfers. Relationship checks here; the configured
        # institutional authority (settings) is checked by the lifecycle service.
        "segment_condition:confirm": r == "LEGAL_REVIEWER",
        "segment:read_internal": own_program or faculty_supervisor or r == "EXPERIENTIAL_COORDINATOR",
        "experience:review": own_program,
        "faculty_assignment:manage": own_program or r == "EXPERIENTIAL_COORDINATOR",
        "faculty_assignment:read_history": student_owner or faculty_supervisor or own_program
                                             or r == "EXPERIENTIAL_COORDINATOR",
        # Contextual messaging separates joint practice communication from
        # academic-only discussion. Host-organization members never enter either.
        "message:joint:read": student_owner or current_workplace_supervisor or faculty_supervisor or own_program
                               or r == "EXPERIENTIAL_COORDINATOR",
        "message:academic:read": student_owner or faculty_supervisor or own_program
                                  or r == "EXPERIENTIAL_COORDINATOR",
    }[action]


def authorize(cur: psycopg.Cursor, subj: dict, action: str, pid: int) -> dict:
    """Raise NotFound/Forbidden unless the subject may perform ``action`` on ``pid``.

    Returns the placement context so callers can reuse it (avoid a second query).
    """
    c = _ctx(cur, subj, pid)
    if c is None or not any(_role_read(r, c, subj) for r in subj["roles"]):
        if subj["roles"] and all(r["role"] in EXTERNAL for r in subj["roles"]):
            raise NotFound()
        raise Forbidden("no relationship")
    if not any(_role_action(r, c, subj, action) for r in subj["roles"]):
        raise Forbidden(f"may not {action}")
    return c


def visible_placement_ids(cur: psycopg.Cursor, subj: dict) -> list[int]:
    """Scoped query (no fetch-then-filter)."""
    if any(r["role"] in GLOBAL_ROLES for r in subj["roles"]):
        return [x["id"] for x in cur.execute("SELECT id FROM placement ORDER BY id").fetchall()]

    base = """SELECT p.id FROM placement p JOIN application a ON a.id = p.application_id
              JOIN user_account s ON s.id = a.student_id JOIN opportunity o ON o.id = a.opportunity_id """
    clauses: list[str] = []
    params: list[Any] = []
    u = subj["id"]
    for r in subj["roles"]:
        role = r["role"]
        if role == "STUDENT":
            clauses.append("a.student_id = %s")
            params.append(u)
        elif role == "HOST_ORG_MEMBER":
            clauses.append(
                """o.host_org_id = %s OR EXISTS (SELECT 1 FROM placement_segment sg
                   WHERE sg.placement_id = p.id AND sg.host_org_id = %s AND sg.status <> 'CANCELLED')"""
            )
            params.extend([r["host_org_id"], r["host_org_id"]])
        elif role == "WORKPLACE_SUPERVISOR":
            clauses.append(
                """(NOT EXISTS (SELECT 1 FROM placement_segment sg WHERE sg.placement_id = p.id)
                    AND o.host_org_id = %s AND EXISTS (SELECT 1 FROM placement_version v
                   WHERE v.placement_id = p.id AND v.workplace_supervisor_id = %s))
                   OR EXISTS (SELECT 1 FROM placement_segment sg WHERE sg.placement_id = p.id
                   AND sg.workplace_supervisor_id = %s AND sg.host_org_id = %s
                   AND sg.status IN ('PLANNED','ACTIVE'))"""
            )
            params.extend([r["host_org_id"], u, u, r["host_org_id"]])
        elif role == "FACULTY_SUPERVISOR":
            clauses.append(
                """EXISTS (SELECT 1 FROM supervisor_assignment sa
                   WHERE sa.placement_id = p.id AND sa.user_id = %s AND sa.kind = 'FACULTY')"""
            )
            params.append(u)
        elif role == "PROGRAM_COORDINATOR":
            clauses.append(
                """EXISTS (SELECT 1 FROM role_assignment ra2
                   WHERE ra2.user_id = a.student_id AND ra2.role = 'STUDENT' AND ra2.program_id = %s)"""
            )
            params.append(r["program_id"])
    where = " OR ".join(f"({cl})" for cl in clauses) if clauses else "FALSE"
    rows = cur.execute(base + " WHERE " + where, params).fetchall()
    return sorted(x["id"] for x in rows)


def external_student_view(cur: psycopg.Cursor, student_id: int) -> dict | None:
    """Minimal projection for external roles (BR-13): only display_name and program_code."""
    return cur.execute(
        """SELECT u.display_name, p.code AS program_code
           FROM user_account u
           LEFT JOIN role_assignment ra ON ra.user_id = u.id AND ra.role = 'STUDENT'
           LEFT JOIN academic_program p ON p.id = ra.program_id
           WHERE u.id = %s LIMIT 1""",
        (student_id,),
    ).fetchone()
