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
        "SELECT a.id, a.opportunity_id, a.state, a.eligibility_result, o.title "
        "FROM application a JOIN opportunity o ON o.id=a.opportunity_id "
        "WHERE a.student_id=%s ORDER BY a.id DESC",
        (subj["id"],),
    ).fetchall()
