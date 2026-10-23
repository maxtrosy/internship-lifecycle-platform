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
    "ELIGIBILITY": {
        "PROGRAM_IN": list,
        "ACADEMIC_LEVEL_MIN": int,
        "CREDITS_MIN": int,
        "PREREQUISITE_COMPLETED": list,
    },
    "ACTIVATION": {
        "REQUIRE_DOCUMENTS": list,
        "SUPERVISORS_ASSIGNED": bool,
    },
    "COMPLETION": {
        "FINAL_REPORT": bool,
        "FINAL_EVALUATION": bool,
        "MIN_HOURS": int,
    },
}


class PolicyValidationError(BusinessError):
    def __init__(self, detail):
        super().__init__("POLICY_INVALID", detail)


def validate(conditions, kind: str = "ELIGIBILITY") -> None:
    if kind not in VOCABULARY:
        raise PolicyValidationError(f"unsupported policy kind: {kind}")
    if not isinstance(conditions, list) or not conditions:
        raise PolicyValidationError("conditions must be a non-empty list")
    vocabulary = VOCABULARY[kind]
    for c in conditions:
        if set(c) != {"type", "value"}:
            raise PolicyValidationError(f"bad condition shape: {c}")
        if c["type"] not in vocabulary:
            raise PolicyValidationError(f"unsupported condition type: {c['type']}")
        expected = vocabulary[c["type"]]
        value = c["value"]
        if not isinstance(value, expected) or (expected is int and isinstance(value, bool)):
            raise PolicyValidationError(f"bad value for {c['type']}")
        if expected is list and (not all(isinstance(v, str) and v.strip() for v in value)
                                 or len(value) != len(set(value))):
            raise PolicyValidationError(f"{c['type']} must contain unique, non-empty strings")
        if c["type"] == "REQUIRE_DOCUMENTS" and any(not kind.startswith("DOC_") for kind in value):
            raise PolicyValidationError("REQUIRE_DOCUMENTS entries must use the DOC_ prefix")
        if c["type"] in ("ACADEMIC_LEVEL_MIN", "CREDITS_MIN") and value < 0:
            raise PolicyValidationError(f"{c['type']} cannot be negative")
        if c["type"] == "MIN_HOURS" and value < 1:
            raise PolicyValidationError("MIN_HOURS must be at least 1")


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


def create_policy_version(ctx: CommandContext, program_code: str, conditions, kind: str = "ELIGIBILITY") -> int:
    validate(conditions, kind)
    subj = subject(ctx.cur, ctx.actor_id)
    prog = ctx.execute("SELECT * FROM academic_program WHERE code=%s", (program_code,)).fetchone()
    if prog is None:
        raise BusinessError("UNKNOWN_PROGRAM", program_code)
    if not any(r["role"] == "PROGRAM_COORDINATOR" and r["program_id"] == prog["id"] for r in subj["roles"]):
        raise Forbidden("only the program coordinator of this program may change its policy")
    key = f"{kind}:{program_code}"
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


def latest_policy(cur, program_code: str, kind: str = "ELIGIBILITY") -> dict | None:
    return cur.execute(
        """SELECT * FROM policy_version WHERE policy_key=%s AND effective_from <= now()
           ORDER BY effective_from DESC, version_no DESC LIMIT 1""",
        (f"{kind}:{program_code}",),
    ).fetchone()


def activation_requirements(cur, program_code: str) -> list[str] | None:
    """Return the activation policy's required document kinds, or None if not configured."""
    pv = latest_policy(cur, program_code, kind="ACTIVATION")
    if pv is None:
        return None
    kinds: list[str] = []
    for c in pv["conditions"]:
        if c["type"] == "REQUIRE_DOCUMENTS":
            kinds.extend(c["value"])
    return kinds


def supervisor_condition(cur, program_code: str) -> bool:
    pv = latest_policy(cur, program_code, kind="ACTIVATION")
    return bool(pv and any(c["type"] == "SUPERVISORS_ASSIGNED" and c["value"]
                           for c in pv["conditions"]))


def completion_requirements(cur, policy_version_id: int) -> list[dict]:
    pv = cur.execute("SELECT conditions FROM policy_version WHERE id=%s", (policy_version_id,)).fetchone()
    if pv is None:
        raise BusinessError("COMPLETION_POLICY_MISSING")
    requirements = []
    for condition in pv["conditions"]:
        kind, value = condition["type"], condition["value"]
        if kind in ("FINAL_REPORT", "FINAL_EVALUATION") and value:
            requirements.append({"kind": kind, "threshold": None})
        elif kind == "MIN_HOURS":
            requirements.append({"kind": kind, "threshold": value})
    return requirements


def policies_for_subject(cur, subj: dict) -> list[dict]:
    """Current versioned policies for the caller's own coordinator program scopes."""
    program_ids = sorted({r["program_id"] for r in subj["roles"]
                          if r["role"] == "PROGRAM_COORDINATOR" and r["program_id"] is not None})
    if not program_ids:
        raise Forbidden("only program coordinators may read policy versions")
    programs = cur.execute(
        "SELECT id, code, name FROM academic_program WHERE id = ANY(%s) ORDER BY code",
        (program_ids,),
    ).fetchall()
    versions = cur.execute(
        """SELECT DISTINCT ON (pv.policy_key) pv.id, pv.policy_key, pv.version_no,
                  pv.conditions, pv.effective_from
           FROM policy_version pv
           WHERE pv.effective_from <= now()
             AND pv.policy_key = ANY(%s)
           ORDER BY pv.policy_key, pv.effective_from DESC, pv.version_no DESC""",
        ([f"{kind}:{row['code']}" for row in programs for kind in VOCABULARY],),
    ).fetchall()
    by_program: dict[str, dict] = {p["code"]: {} for p in programs}
    for version in versions:
        kind, code = version["policy_key"].split(":", 1)
        if code in by_program:
            by_program[code][kind] = {
                "id": version["id"], "version_no": version["version_no"],
                "conditions": version["conditions"], "effective_from": version["effective_from"],
            }
    return [{**p, "policies": by_program[p["code"]]} for p in programs]
