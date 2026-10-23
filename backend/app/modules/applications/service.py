"""C-04 applications: eligibility-evaluated submission (ADR-001), ported from the PoC."""
from __future__ import annotations

import psycopg
from psycopg.types.json import Jsonb

from app.db import CommandContext
from app.errors import BusinessError, Forbidden, NotFound
from app.modules.audit import service as audit
from app.modules.authz import subject
from app.modules.policies.service import evaluate, latest_policy


def submit_application(ctx: CommandContext, opportunity_id: int) -> dict:
    subj = subject(ctx.cur, ctx.actor_id)
    if not any(r["role"] == "STUDENT" for r in subj["roles"]):
        raise Forbidden("only students may apply")
    opp = ctx.execute(
        "SELECT o.*, p.code FROM opportunity o JOIN academic_program p ON p.id=o.program_id WHERE o.id=%s",
        (opportunity_id,),
    ).fetchone()
    if opp is None:
        raise NotFound()
    if opp["state"] != "PUBLISHED":
        raise BusinessError("OPPORTUNITY_NOT_PUBLISHED", opp["state"])
    pv = latest_policy(ctx.cur, opp["code"])
    if pv is None:
        raise BusinessError("NO_POLICY_IN_EFFECT", opp["code"])
    res = evaluate(subj, opp["code"], pv["conditions"])
    res["inputs"] = {"credits": subj["credits"], "academic_level": subj["academic_level"]}
    state = "SUBMITTED" if res["result"] == "ELIGIBLE" else "INELIGIBLE"
    aid = ctx.execute(
        """INSERT INTO application(opportunity_id, student_id, state, policy_version_id, eligibility_result)
           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
        (opportunity_id, subj["id"], state, pv["id"], Jsonb(res)),
    ).fetchone()["id"]
    audit.write(ctx.cur, "application.submitted", "application", aid,
                None, {"opportunity_id": opportunity_id, "state": state})
    return {"application_id": aid, "state": state, "eligibility": res}


def list_my_applications(cur: psycopg.Cursor, subj: dict) -> list[dict]:
    return cur.execute(
        "SELECT a.id, a.opportunity_id, a.state, a.eligibility_result, o.title, "
        "       pl.id AS placement_id, pl.state AS placement_state "
        "FROM application a JOIN opportunity o ON o.id=a.opportunity_id "
        "LEFT JOIN placement pl ON pl.application_id = a.id "
        "WHERE a.student_id=%s ORDER BY a.id DESC",
        (subj["id"],),
    ).fetchall()


def _require_employer(subj: dict, host_org_id: int) -> bool:
    return any(r["role"] == "HOST_ORG_MEMBER" and r["host_org_id"] == host_org_id for r in subj["roles"])


def list_for_opportunity(cur: psycopg.Cursor, subj: dict, opportunity_id: int) -> list[dict]:
    opp = cur.execute("SELECT * FROM opportunity WHERE id=%s", (opportunity_id,)).fetchone()
    if opp is None:
        raise NotFound()
    if not _require_employer(subj, opp["host_org_id"]):
        raise Forbidden("only the host org member of this opportunity may review its applications")
    rows = cur.execute(
        """SELECT a.id, a.opportunity_id, a.state, a.eligibility_result,
                  u.display_name, p.code AS program_code,
                  pl.id AS placement_id, pl.state AS placement_state
           FROM application a
           JOIN user_account u ON u.id = a.student_id
           LEFT JOIN role_assignment ra ON ra.user_id = a.student_id AND ra.role = 'STUDENT'
           LEFT JOIN academic_program p ON p.id = ra.program_id
           LEFT JOIN placement pl ON pl.application_id = a.id
           WHERE a.opportunity_id = %s ORDER BY a.id""",
        (opportunity_id,),
    ).fetchall()
    # BR-13: employers receive only the eligibility decision, not student inputs
    # or evaluator reasons that may reveal credits, level, or completed courses.
    for r in rows:
        eligibility = r["eligibility_result"]
        if isinstance(eligibility, dict):
            r["eligibility_result"] = (
                {"result": eligibility["result"]}
                if isinstance(eligibility.get("result"), str)
                else None
            )
        else:
            r["eligibility_result"] = None
    return rows


def select_application(ctx: CommandContext, application_id: int, details: dict) -> int:
    subj = subject(ctx.cur, ctx.actor_id)
    app = ctx.execute("SELECT * FROM application WHERE id=%s FOR UPDATE", (application_id,)).fetchone()
    if app is None:
        raise NotFound()
    opp = ctx.execute("SELECT * FROM opportunity WHERE id=%s", (app["opportunity_id"],)).fetchone()
    if not _require_employer(subj, opp["host_org_id"]):
        raise Forbidden("only the host org member may select")
    if opp["state"] != "PUBLISHED":
        raise BusinessError("OPPORTUNITY_NOT_PUBLISHED", opp["state"])
    if app["state"] != "SUBMITTED":
        raise BusinessError("INVALID_TRANSITION", app["state"])
    eligibility = app["eligibility_result"]
    if not isinstance(eligibility, dict) or eligibility.get("result") != "ELIGIBLE":
        raise BusinessError("APPLICATION_NOT_ELIGIBLE")

    pid = ctx.execute(
        "INSERT INTO placement(application_id, state) VALUES (%s, 'PENDING_ACADEMIC_APPROVAL') RETURNING id",
        (application_id,),
    ).fetchone()["id"]
    vid = ctx.execute(
        """INSERT INTO placement_version(placement_id, version_no, workplace_supervisor_id, start_date, end_date,
           location, responsibilities) VALUES (%s,1,%s,%s,%s,%s,%s) RETURNING id""",
        (pid, details.get("workplace_supervisor_id"), details["start_date"], details["end_date"],
         details["location"], details["responsibilities"]),
    ).fetchone()["id"]
    ctx.execute("UPDATE placement SET current_version_id=%s WHERE id=%s", (vid, pid))
    ctx.execute("UPDATE application SET state='SELECTED' WHERE id=%s", (application_id,))
    audit.write(ctx.cur, "application.selected", "application", application_id,
                {"state": "SUBMITTED"}, {"state": "SELECTED", "placement_id": pid})
    return pid
