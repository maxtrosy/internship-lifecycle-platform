"""Placement lifecycle commands (ADR-003/005). One command = one DB transaction that
(1) authorizes, (2) locks the placement aggregate, (3) evaluates guards from source rows,
(4) mutates state, (5) writes the audit event. `naive=True` exists ONLY as a negative control."""
import time, uuid
import psycopg
from psycopg.types.json import Jsonb
from . import authz


class BusinessError(Exception):
    def __init__(self, code, detail=None):
        super().__init__(code)
        self.code, self.detail = code, detail


def _audit(cur, actor, action, stype, sid, before, after, corr):
    cur.execute(
        """INSERT INTO audit_event(actor_id,action,subject_type,subject_id,before_state,after_state,correlation_id)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (actor, action, stype, sid,
         Jsonb(before) if before is not None else None, Jsonb(after) if after is not None else None, corr))


def _placement(cur, pid, lock=True):
    return cur.execute("SELECT * FROM placement WHERE id=%s" + (" FOR UPDATE" if lock else ""), (pid,)).fetchone()


def activation_unmet(cur, pid):
    rows = cur.execute("""SELECT kind,status FROM checklist_item
                          WHERE placement_id=%s AND mandatory AND status<>'APPROVED' ORDER BY id""", (pid,)).fetchall()
    return [f"{r['kind']}={r['status']}" for r in rows]


def completion_unmet(cur, pid):
    # Recompute hours requirement from SOURCE rows, never from a cached flag (T-04)
    for r in cur.execute("SELECT * FROM completion_requirement WHERE placement_id=%s AND kind='MIN_HOURS'", (pid,)).fetchall():
        total = cur.execute("SELECT coalesce(sum(hours),0) AS t FROM progress_entry WHERE placement_id=%s", (pid,)).fetchone()["t"]
        cur.execute("UPDATE completion_requirement SET satisfied=%s WHERE id=%s", (total >= r["threshold"], r["id"]))
    rows = cur.execute("""SELECT kind FROM completion_requirement
                          WHERE placement_id=%s AND mandatory AND NOT satisfied ORDER BY id""", (pid,)).fetchall()
    return [r["kind"] for r in rows]


def _gate(fn):
    try:
        return fn()
    except psycopg.errors.RaiseException as e:  # DB safety net fired
        raise BusinessError("GATE_VIOLATION", str(e).split("\n")[0])


def academic_approve(conn, actor_id, pid, required_kinds):
    corr = str(uuid.uuid4())
    with conn.transaction():
        cur = conn.cursor()
        authz.authorize(cur, authz.subject(cur, actor_id), "placement:approve_academic", pid)
        p = _placement(cur, pid)
        if p["state"] != "PENDING_ACADEMIC_APPROVAL":
            raise BusinessError("INVALID_TRANSITION", p["state"])
        for k in required_kinds:
            cur.execute("INSERT INTO checklist_item(placement_id,kind) VALUES (%s,%s) ON CONFLICT DO NOTHING", (pid, k))
        # Condition-type requirement: supervisor assigned (auto-approved when version has one)
        cur.execute("INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,'COND_SUPERVISOR_ASSIGNED',"
                    "CASE WHEN (SELECT workplace_supervisor_id FROM placement_version WHERE id=%s) IS NULL "
                    "THEN 'REQUIRED' ELSE 'APPROVED' END) ON CONFLICT DO NOTHING", (pid, p["current_version_id"]))
        cur.execute("UPDATE placement_version SET status='APPROVED', decided_by=%s WHERE id=%s", (actor_id, p["current_version_id"]))
        cur.execute("UPDATE placement SET state='DOCUMENTATION_PENDING', activation_requirements_instantiated=true WHERE id=%s", (pid,))
        _audit(cur, actor_id, "placement.academic_approved", "placement", pid,
               {"state": p["state"]}, {"state": "DOCUMENTATION_PENDING", "version_id": p["current_version_id"]}, corr)


def review_document(conn, actor_id, item_id, decision, naive=False, pause=0.0):
    assert decision in ("APPROVED", "REJECTED")
    corr = str(uuid.uuid4())
    with conn.transaction():
        cur = conn.cursor()
        it = cur.execute("SELECT * FROM checklist_item WHERE id=%s", (item_id,)).fetchone()
        pid = it["placement_id"]
        authz.authorize(cur, authz.subject(cur, actor_id), "document:review", pid)
        p = _placement(cur, pid, lock=not naive)   # lock order: placement first, then item
        if pause:
            time.sleep(pause)
        cur.execute("UPDATE checklist_item SET status=%s WHERE id=%s", (decision, item_id))
        _audit(cur, actor_id, f"checklist_item.{decision.lower()}", "checklist_item", item_id,
               {"status": it["status"]}, {"status": decision, "placement_state": p["state"]}, corr)


def activate(conn, actor_id, pid, naive=False, pause=0.0):
    corr = str(uuid.uuid4())

    def run():
        with conn.transaction():
            cur = conn.cursor()
            authz.authorize(cur, authz.subject(cur, actor_id), "placement:activate", pid)
            p = _placement(cur, pid, lock=not naive)
            if p["state"] != "DOCUMENTATION_PENDING":
                raise BusinessError("INVALID_TRANSITION", p["state"])
            unmet = activation_unmet(cur, pid)
            if unmet:
                raise BusinessError("ACTIVATION_CONDITIONS_UNMET", unmet)
            if pause:
                time.sleep(pause)
            cur.execute("""INSERT INTO completion_requirement(placement_id,kind,threshold) VALUES
                           (%s,'FINAL_REPORT',NULL),(%s,'FINAL_EVALUATION',NULL),(%s,'MIN_HOURS',100)
                           ON CONFLICT DO NOTHING""", (pid, pid, pid))
            cur.execute("UPDATE placement SET state='ACTIVE', completion_requirements_instantiated=true WHERE id=%s", (pid,))
            _audit(cur, actor_id, "placement.activated", "placement", pid,
                   {"state": p["state"]}, {"state": "ACTIVE"}, corr)
    return _gate(run)


def submit_evidence(conn, actor_id, pid, kind):
    corr = str(uuid.uuid4())
    with conn.transaction():
        cur = conn.cursor()
        authz.authorize(cur, authz.subject(cur, actor_id), "evidence:submit", pid)
        _placement(cur, pid)
        cur.execute("UPDATE completion_requirement SET satisfied=true WHERE placement_id=%s AND kind=%s", (pid, kind))
        _audit(cur, actor_id, "completion_requirement.satisfied", "placement", pid, None, {"kind": kind}, corr)


def record_hours(conn, actor_id, pid, hours):
    corr = str(uuid.uuid4())

    def run():
        with conn.transaction():
            cur = conn.cursor()
            authz.authorize(cur, authz.subject(cur, actor_id), "progress:create", pid)
            cur.execute("INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,%s)", (pid, actor_id, hours))
            _audit(cur, actor_id, "progress.hours_recorded", "placement", pid, None, {"hours": hours}, corr)
    try:
        return _gate(run)
    except BusinessError as e:
        raise BusinessError("PLACEMENT_NOT_ACTIVE", e.detail)


def confirm_completion(conn, actor_id, pid):
    corr = str(uuid.uuid4())

    def run():
        with conn.transaction():
            cur = conn.cursor()
            authz.authorize(cur, authz.subject(cur, actor_id), "placement:confirm_completion", pid)
            p = _placement(cur, pid)
            if p["state"] != "ACTIVE":
                raise BusinessError("INVALID_TRANSITION", p["state"])
            unmet = completion_unmet(cur, pid)
            if unmet:
                raise BusinessError("COMPLETION_EVIDENCE_MISSING", unmet)
            cur.execute("UPDATE placement SET state='COMPLETED' WHERE id=%s", (pid,))
            _audit(cur, actor_id, "placement.completed", "placement", pid, {"state": "ACTIVE"}, {"state": "COMPLETED"}, corr)
    return _gate(run)


def close_placement(conn, actor_id, pid):
    corr = str(uuid.uuid4())

    def run():
        with conn.transaction():
            cur = conn.cursor()
            authz.authorize(cur, authz.subject(cur, actor_id), "placement:close", pid)
            p = _placement(cur, pid)
            if p["state"] != "COMPLETED":
                raise BusinessError("INVALID_TRANSITION", p["state"])
            unmet = completion_unmet(cur, pid)
            if unmet:
                raise BusinessError("COMPLETION_EVIDENCE_MISSING", unmet)
            cur.execute("UPDATE placement SET state='CLOSED' WHERE id=%s", (pid,))
            _audit(cur, actor_id, "placement.closed", "placement", pid, {"state": "COMPLETED"}, {"state": "CLOSED"}, corr)
    return _gate(run)


def propose_change(conn, actor_id, pid, **changes):
    corr = str(uuid.uuid4())
    with conn.transaction():
        cur = conn.cursor()
        authz.authorize(cur, authz.subject(cur, actor_id), "placement:propose_change", pid)
        p = _placement(cur, pid)
        cur_v = cur.execute("SELECT * FROM placement_version WHERE id=%s", (p["current_version_id"],)).fetchone()
        n = cur.execute("SELECT max(version_no)+1 AS n FROM placement_version WHERE placement_id=%s", (pid,)).fetchone()["n"]
        new = {k: cur_v[k] for k in ("workplace_supervisor_id", "start_date", "end_date", "location", "responsibilities")}
        new.update(changes)
        v = cur.execute("""INSERT INTO placement_version(placement_id,version_no,workplace_supervisor_id,start_date,end_date,
                           location,responsibilities,status) VALUES (%s,%s,%s,%s,%s,%s,%s,'PROPOSED') RETURNING id""",
                        (pid, n, new["workplace_supervisor_id"], new["start_date"], new["end_date"],
                         new["location"], new["responsibilities"])).fetchone()
        _audit(cur, actor_id, "placement.change_proposed", "placement_version", v["id"],
               {"version_no": cur_v["version_no"], "location": cur_v["location"]},
               {"version_no": n, "location": new["location"], "changed": sorted(changes)}, corr)
        return v["id"]


def approve_version(conn, actor_id, vid):
    corr = str(uuid.uuid4())
    with conn.transaction():
        cur = conn.cursor()
        v = cur.execute("SELECT * FROM placement_version WHERE id=%s", (vid,)).fetchone()
        authz.authorize(cur, authz.subject(cur, actor_id), "version:approve", v["placement_id"])
        p = _placement(cur, v["placement_id"])
        if v["status"] != "PROPOSED":
            raise BusinessError("INVALID_TRANSITION", v["status"])
        old = cur.execute("SELECT * FROM placement_version WHERE id=%s", (p["current_version_id"],)).fetchone()
        cur.execute("UPDATE placement_version SET status='APPROVED', decided_by=%s WHERE id=%s", (actor_id, vid))
        cur.execute("UPDATE placement SET current_version_id=%s WHERE id=%s", (vid, p["id"]))
        _audit(cur, actor_id, "placement.version_approved", "placement", p["id"],
               {"version_no": old["version_no"], "location": old["location"]},
               {"version_no": v["version_no"], "location": v["location"]}, corr)
