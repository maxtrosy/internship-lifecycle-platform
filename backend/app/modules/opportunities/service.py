"""C-03 opportunities with configurable review and scoped publication."""
from __future__ import annotations

import psycopg

from app.config import get_settings
from app.db import CommandContext
from app.errors import BusinessError, Forbidden, NotFound
from app.modules.audit import service as audit
from app.modules.authz import GLOBAL_ROLES, subject


def create_opportunity(ctx: CommandContext, host_org_id: int, program_id: int, title: str) -> int:
    subj = subject(ctx.cur, ctx.actor_id)
    allowed = any(
        (r["role"] == "HOST_ORG_MEMBER" and r["host_org_id"] == host_org_id)
        or (r["role"] == "PROGRAM_COORDINATOR" and r["program_id"] == program_id)
        for r in subj["roles"]
    )
    if not allowed:
        raise Forbidden("only the host org member or the program coordinator may create this opportunity")
    oid = ctx.execute(
        "INSERT INTO opportunity(host_org_id, program_id, title, state) VALUES (%s,%s,%s,'DRAFT') RETURNING id",
        (host_org_id, program_id, title),
    ).fetchone()["id"]
    audit.write(ctx.cur, "opportunity.created", "opportunity", oid,
                None, {"host_org_id": host_org_id, "program_id": program_id, "title": title})
    return oid


def _creator_related(subj: dict, opportunity: dict) -> bool:
    return any(
        (role["role"] == "HOST_ORG_MEMBER" and role["host_org_id"] == opportunity["host_org_id"])
        or (role["role"] == "PROGRAM_COORDINATOR" and role["program_id"] == opportunity["program_id"])
        for role in subj["roles"]
    )


def _configured_authority(subj: dict, opportunity: dict, configured_roles: tuple[str, ...]) -> bool:
    for role in subj["roles"]:
        if role["role"] not in configured_roles:
            continue
        if role["role"] == "EXPERIENTIAL_COORDINATOR":
            return True
        if role["role"] == "PROGRAM_COORDINATOR" and role["program_id"] == opportunity["program_id"]:
            return True
    return False


def _transition(ctx: CommandContext, opportunity_id: int, target: str, event: str,
                allowed_from: tuple[str, ...], authority: str) -> None:
    subj = subject(ctx.cur, ctx.actor_id)
    opportunity = ctx.execute(
        "SELECT id, state, host_org_id, program_id FROM opportunity WHERE id=%s FOR UPDATE",
        (opportunity_id,),
    ).fetchone()
    if opportunity is None:
        raise NotFound()
    if opportunity["state"] not in allowed_from:
        raise BusinessError("OPPORTUNITY_INVALID_TRANSITION", {
            "state": opportunity["state"], "target": target,
        })
    settings = get_settings()
    if authority == "creator":
        permitted = _creator_related(subj, opportunity)
    else:
        configured_roles = (settings.opportunity_reviewer_roles if authority == "reviewer"
                            else settings.opportunity_publisher_roles)
        if not configured_roles:
            code = ("OPPORTUNITY_REVIEW_AUTHORITY_UNCONFIGURED" if authority == "reviewer"
                    else "OPPORTUNITY_PUBLISH_AUTHORITY_UNCONFIGURED")
            raise BusinessError(code)
        permitted = _configured_authority(subj, opportunity, configured_roles)
    if not permitted:
        raise Forbidden("the caller is not authorized for this opportunity transition")
    ctx.execute("UPDATE opportunity SET state=%s WHERE id=%s", (target, opportunity_id))
    audit.write(ctx.cur, event, "opportunity", opportunity_id,
                {"state": opportunity["state"]}, {"state": target})


def submit_for_review(ctx: CommandContext, opportunity_id: int) -> None:
    _transition(ctx, opportunity_id, "IN_REVIEW", "opportunity.submitted_for_review", ("DRAFT",), "creator")


def approve_for_publication(ctx: CommandContext, opportunity_id: int) -> None:
    _transition(ctx, opportunity_id, "APPROVED", "opportunity.approved_for_publication", ("IN_REVIEW",), "reviewer")


def publish_opportunity(ctx: CommandContext, opportunity_id: int) -> None:
    _transition(ctx, opportunity_id, "PUBLISHED", "opportunity.published", ("APPROVED",), "publisher")


def close_opportunity(ctx: CommandContext, opportunity_id: int) -> None:
    _transition(ctx, opportunity_id, "CLOSED", "opportunity.closed", ("DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED"), "creator")


def _visibility_clauses(subj: dict):
    """Return (clauses, params) for the caller's roles; global roles see everything."""
    clauses: list[str] = []
    params: list[object] = []
    for r in subj["roles"]:
        role = r["role"]
        if role == "STUDENT":
            clauses.append("(o.state = 'PUBLISHED' OR EXISTS (SELECT 1 FROM application sa "
                            "WHERE sa.opportunity_id=o.id AND sa.student_id=%s))")
            params.append(subj["id"])
        elif role in ("HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR"):
            clauses.append("o.host_org_id = %s")
            params.append(r["host_org_id"])
        elif role == "PROGRAM_COORDINATOR":
            clauses.append("o.program_id = %s")
            params.append(r["program_id"])
        elif role in GLOBAL_ROLES:
            return None, None  # all opportunities
    return clauses, params


def list_opportunities(cur: psycopg.Cursor, subj: dict) -> list[dict]:
    clauses, params = _visibility_clauses(subj)
    base = ("SELECT o.*, p.code AS program_code, h.name AS host_name "
            "FROM opportunity o JOIN academic_program p ON p.id=o.program_id "
            "JOIN host_org h ON h.id=o.host_org_id")
    if clauses is None:
        rows = cur.execute(base + " ORDER BY o.id").fetchall()
    else:
        where = " OR ".join(f"({c})" for c in clauses) if clauses else "FALSE"
        rows = cur.execute(base + " WHERE " + where + " ORDER BY o.id", params).fetchall()
    settings = get_settings()
    for row in rows:
        is_creator = _creator_related(subj, row)
        row["can_submit_for_review"] = is_creator and row["state"] == "DRAFT"
        row["review_authority_configured"] = bool(settings.opportunity_reviewer_roles)
        row["publisher_authority_configured"] = bool(settings.opportunity_publisher_roles)
        row["can_approve_for_publication"] = (
            row["state"] == "IN_REVIEW"
            and _configured_authority(subj, row, settings.opportunity_reviewer_roles)
        )
        row["can_publish"] = (
            row["state"] == "APPROVED"
            and _configured_authority(subj, row, settings.opportunity_publisher_roles)
        )
        row["can_close"] = is_creator and row["state"] in ("DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED")
    return rows


def list_creation_catalogs(cur: psycopg.Cursor, subj: dict) -> dict:
    """Return only organization/program choices the caller can use to create an opportunity."""
    host_org_ids = {
        role["host_org_id"] for role in subj["roles"]
        if role["role"] == "HOST_ORG_MEMBER" and role["host_org_id"] is not None
    }
    program_ids = {
        role["program_id"] for role in subj["roles"]
        if role["role"] == "PROGRAM_COORDINATOR" and role["program_id"] is not None
    }
    if not host_org_ids and not program_ids:
        raise Forbidden("only opportunity creators may read creation catalogs")

    if host_org_ids:
        organizations = cur.execute(
            "SELECT id, name FROM host_org WHERE id = ANY(%s) ORDER BY name, id",
            (sorted(host_org_ids),),
        ).fetchall()
    else:
        organizations = cur.execute(
            "SELECT id, name FROM host_org ORDER BY name, id"
        ).fetchall()

    if program_ids:
        programs = cur.execute(
            "SELECT id, code, name FROM academic_program WHERE id = ANY(%s) ORDER BY code, id",
            (sorted(program_ids),),
        ).fetchall()
    else:
        programs = cur.execute(
            "SELECT id, code, name FROM academic_program ORDER BY code, id"
        ).fetchall()

    return {"organizations": organizations, "programs": programs}


def list_workplace_supervisors(cur: psycopg.Cursor, subj: dict, opportunity_id: int) -> list[dict]:
    """List active supervisors only for the opportunity's related host organization."""
    opportunity = cur.execute(
        "SELECT host_org_id FROM opportunity WHERE id=%s", (opportunity_id,)
    ).fetchone()
    if opportunity is None:
        raise NotFound()
    host_org_id = opportunity["host_org_id"]
    if not any(
        role["role"] == "HOST_ORG_MEMBER" and role["host_org_id"] == host_org_id
        for role in subj["roles"]
    ):
        raise Forbidden("only the related host organization may select its supervisors")
    return cur.execute(
        """SELECT u.id, u.display_name FROM role_assignment ra
           JOIN user_account u ON u.id=ra.user_id
           WHERE ra.role='WORKPLACE_SUPERVISOR' AND ra.host_org_id=%s AND u.is_active=true
           ORDER BY u.display_name, u.id""",
        (host_org_id,),
    ).fetchall()


def can_view(cur: psycopg.Cursor, subj: dict, oid: int) -> bool:
    clauses, params = _visibility_clauses(subj)
    if clauses is None:
        return True
    if not clauses:
        return False
    where = " OR ".join(f"({c})" for c in clauses)
    row = cur.execute(
        f"SELECT 1 FROM opportunity o WHERE o.id=%s AND ({where})",
        [oid, *params],
    ).fetchone()
    return row is not None


def get_opportunity(cur: psycopg.Cursor, subj: dict, oid: int) -> dict:
    row = cur.execute(
        "SELECT o.*, p.code AS program_code, h.name AS host_name FROM opportunity o "
        "JOIN academic_program p ON p.id=o.program_id JOIN host_org h ON h.id=o.host_org_id WHERE o.id=%s",
        (oid,),
    ).fetchone()
    if row is None:
        raise NotFound()
    if not can_view(cur, subj, oid):
        raise Forbidden("no relationship to this opportunity")
    return row
