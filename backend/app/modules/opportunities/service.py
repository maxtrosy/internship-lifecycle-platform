"""C-03 opportunities: publication and scoped listing (Sprint 1 slice).

OPEN-05 (quién revisa/publica) remains open: the increment stores opportunities as
PUBLISHED directly and does not invent a review step.
"""
from __future__ import annotations

import psycopg

from app.db import CommandContext
from app.errors import Forbidden, NotFound
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
        "INSERT INTO opportunity(host_org_id, program_id, title, state) VALUES (%s,%s,%s,'PUBLISHED') RETURNING id",
        (host_org_id, program_id, title),
    ).fetchone()["id"]
    audit.write(ctx.cur, "opportunity.created", "opportunity", oid,
                None, {"host_org_id": host_org_id, "program_id": program_id, "title": title})
    return oid


def _visibility_clauses(subj: dict):
    """Return (clauses, params) for the caller's roles; global roles see everything."""
    clauses: list[str] = []
    params: list[object] = []
    for r in subj["roles"]:
        role = r["role"]
        if role == "STUDENT":
            clauses.append("o.state = 'PUBLISHED'")
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
    return rows


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
