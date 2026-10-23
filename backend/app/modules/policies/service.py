"""C-05 policy vocabulary (ADR-001), ported from prototype/poc/policy.py.

Small, controlled condition vocabulary; no scripts, no expressions.
"""
from __future__ import annotations

from psycopg.types.json import Jsonb

from app.db import CommandContext
from app.errors import BusinessError, Forbidden
from app.modules.audit import service as audit
from app.modules.authz import subject

VOCABULARY = {
    "PROGRAM_IN": list,
    "ACADEMIC_LEVEL_MIN": int,
    "CREDITS_MIN": int,
    "PREREQUISITE_COMPLETED": list,
}


class PolicyValidationError(BusinessError):
    def __init__(self, detail):
        super().__init__("POLICY_INVALID", detail)


def validate(conditions) -> None:
    if not isinstance(conditions, list) or not conditions:
        raise PolicyValidationError("conditions must be a non-empty list")
    for c in conditions:
        if set(c) != {"type", "value"}:
            raise PolicyValidationError(f"bad condition shape: {c}")
        if c["type"] not in VOCABULARY:
            raise PolicyValidationError(f"unsupported condition type: {c['type']}")
        if not isinstance(c["value"], VOCABULARY[c["type"]]) or isinstance(c["value"], bool):
            raise PolicyValidationError(f"bad value for {c['type']}")


def evaluate(profile, program_code: str, conditions) -> dict:
    reasons = []
    for c in conditions:
        t, v = c["type"], c["value"]
        if t == "PROGRAM_IN" and program_code not in v:
            reasons.append(f"program {program_code} not in {v}")
        elif t == "ACADEMIC_LEVEL_MIN" and (profile["academic_level"] or 0) < v:
            reasons.append(f"academic_level {profile['academic_level']} < {v}")
        elif t == "CREDITS_MIN" and (profile["credits"] or 0) < v:
            reasons.append(f"credits {profile['credits']} < {v}")
        elif t == "PREREQUISITE_COMPLETED" and not set(v) <= set(profile["completed_courses"] or []):
            reasons.append(f"missing prerequisites {sorted(set(v) - set(profile['completed_courses'] or []))}")
    return {"result": "NOT_ELIGIBLE" if reasons else "ELIGIBLE", "reasons": reasons}


def create_policy_version(ctx: CommandContext, program_code: str, conditions) -> int:
    validate(conditions)
    subj = subject(ctx.cur, ctx.actor_id)
    prog = ctx.execute("SELECT * FROM academic_program WHERE code=%s", (program_code,)).fetchone()
    if prog is None:
        raise BusinessError("UNKNOWN_PROGRAM", program_code)
    if not any(r["role"] == "PROGRAM_COORDINATOR" and r["program_id"] == prog["id"] for r in subj["roles"]):
        raise Forbidden("only the program coordinator of this program may change its policy")
    key = f"ELIGIBILITY:{program_code}"
    n = ctx.execute("SELECT coalesce(max(version_no),0)+1 AS n FROM policy_version WHERE policy_key=%s",
                    (key,)).fetchone()["n"]
    pv = ctx.execute(
        """INSERT INTO policy_version(policy_key, version_no, conditions, created_by)
           VALUES (%s,%s,%s,%s) RETURNING id""",
        (key, n, Jsonb(conditions), ctx.actor_id),
    ).fetchone()
    audit.write(ctx.cur, "policy.version_created", "policy_version", pv["id"],
                None, {"key": key, "version_no": n, "conditions": conditions})
    return pv["id"]


def latest_policy(cur, program_code: str) -> dict | None:
    return cur.execute(
        """SELECT * FROM policy_version WHERE policy_key=%s AND effective_from <= now()
           ORDER BY version_no DESC LIMIT 1""",
        (f"ELIGIBILITY:{program_code}",),
    ).fetchone()
