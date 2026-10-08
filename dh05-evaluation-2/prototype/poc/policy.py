"""ADR-001: small, controlled condition vocabulary. No scripts, no expressions."""
import json
from psycopg.types.json import Jsonb
from . import authz

VOCABULARY = {
    "PROGRAM_IN": list,
    "ACADEMIC_LEVEL_MIN": int,
    "CREDITS_MIN": int,
    "PREREQUISITE_COMPLETED": list,
}


class PolicyValidationError(Exception):
    pass


def validate(conditions):
    if not isinstance(conditions, list) or not conditions:
        raise PolicyValidationError("conditions must be a non-empty list")
    for c in conditions:
        if set(c) != {"type", "value"}:
            raise PolicyValidationError(f"bad condition shape: {c}")
        if c["type"] not in VOCABULARY:
            raise PolicyValidationError(f"unsupported condition type: {c['type']}")
        if not isinstance(c["value"], VOCABULARY[c["type"]]) or isinstance(c["value"], bool):
            raise PolicyValidationError(f"bad value for {c['type']}")


def evaluate(profile, program_code, conditions):
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


def create_policy_version(conn, actor_id, program_code, conditions):
    validate(conditions)
    with conn.transaction():
        cur = conn.cursor()
        actor = authz.subject(cur, actor_id)
        prog = cur.execute("SELECT * FROM academic_program WHERE code=%s", (program_code,)).fetchone()
        if actor["role"] != "PROGRAM_COORDINATOR" or actor["program_id"] != prog["id"]:
            raise authz.Forbidden("only the program coordinator of this program may change its policy")
        key = f"ELIGIBILITY:{program_code}"
        n = cur.execute("SELECT coalesce(max(version_no),0)+1 AS n FROM policy_version WHERE policy_key=%s",
                        (key,)).fetchone()["n"]
        pv = cur.execute("""INSERT INTO policy_version(policy_key, version_no, conditions, created_by)
                            VALUES (%s,%s,%s,%s) RETURNING id""",
                         (key, n, Jsonb(conditions), actor_id)).fetchone()
        cur.execute("""INSERT INTO audit_event(actor_id,action,subject_type,subject_id,before_state,after_state,correlation_id)
                       VALUES (%s,'policy.version_created','policy_version',%s,NULL,%s,'policy')""",
                    (actor_id, pv["id"], Jsonb({"key": key, "version_no": n, "conditions": conditions})))
        return pv["id"]


def submit_application(conn, student_id, opportunity_id):
    with conn.transaction():
        cur = conn.cursor()
        stu = authz.subject(cur, student_id)
        opp = cur.execute("""SELECT o.*, p.code FROM opportunity o JOIN academic_program p ON p.id=o.program_id
                             WHERE o.id=%s""", (opportunity_id,)).fetchone()
        pv = cur.execute("""SELECT * FROM policy_version WHERE policy_key=%s AND effective_from <= now()
                            ORDER BY version_no DESC LIMIT 1""", (f"ELIGIBILITY:{opp['code']}",)).fetchone()
        if pv is None:
            raise RuntimeError("no policy version in effect (eligibility cannot be evaluated; never default to eligible)")
        res = evaluate(stu, opp["code"], pv["conditions"])
        res["inputs"] = {"credits": stu["credits"], "academic_level": stu["academic_level"]}
        state = "SUBMITTED" if res["result"] == "ELIGIBLE" else "INELIGIBLE"
        a = cur.execute("""INSERT INTO application(opportunity_id,student_id,state,policy_version_id,eligibility_result)
                           VALUES (%s,%s,%s,%s,%s) RETURNING id""",
                        (opportunity_id, student_id, state, pv["id"], Jsonb(res))).fetchone()
        return a["id"]
