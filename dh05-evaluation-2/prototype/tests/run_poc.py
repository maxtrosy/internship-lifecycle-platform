"""DH-05 Evaluation 2 PoC runner. Executes T-01..T-08 against a REAL PostgreSQL instance (pgserver).
Run:  python tests/run_poc.py        (from the prototype/ directory)
Writes raw outcomes to evidence/results.json. Nothing here is mocked at the database layer."""
import json, os, platform, random, sys, threading, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from poc.db import Env
from poc import seed, authz, lifecycle as lc, policy
from poc.lifecycle import BusinessError

RESULTS = []
TRIALS = int(os.environ.get("POC_TRIALS", "100"))


def record(test_id, title, status, **kw):
    RESULTS.append({"test_id": test_id, "title": title, "status": status, **kw})
    print(f"[{status}] {test_id} {title}")
    for k, v in kw.items():
        print(f"      {k}: {v}")


def race(fn_a, fn_b, delay_a=0.0, delay_b=0.0):
    """Run two callables concurrently on independent connections; return their outcomes."""
    barrier, out = threading.Barrier(2), {}

    def wrap(name, fn, delay):
        barrier.wait()
        time.sleep(delay)
        try:
            out[name] = ("OK", fn())
        except BusinessError as e:
            out[name] = (e.code, e.detail)
        except Exception as e:  # unexpected -> surfaced, never swallowed
            out[name] = ("EXC:" + type(e).__name__, str(e)[:120])
    ts = [threading.Thread(target=wrap, args=("a", fn_a, delay_a)), threading.Thread(target=wrap, args=("b", fn_b, delay_b))]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return out


def audit_actions(env, pid):
    return [r["action"] for r in env.admin.execute(
        "SELECT action FROM audit_event WHERE subject_type='placement' AND subject_id=%s ORDER BY id", (pid,)).fetchall()]


def invariant_active_with_unapproved(env):
    """Final-state invariant: ACTIVE placement with an unapproved mandatory item that was never approved-then-rejected-after.
    (Rejection AFTER activation is a legal, separately handled case - OPEN policy.)  Used only as a sanity query."""
    return env.admin.execute(
        """SELECT count(*) AS n FROM placement p WHERE p.state='ACTIVE' AND NOT p.activation_requirements_instantiated""").fetchone()["n"]


# ------------------------------------------------------------------ T-01
def t01(env, U, opp):
    def trial(naive):
        p = seed.make_doc_pending(env, U, "s1", opp)
        c1, c2 = env.conn(), env.conn()
        out = race(lambda: lc.activate(c1, U["ec1"], p, naive=naive, pause=0.05 if naive else 0.0),
                   lambda: lc.activate(c2, U["ec1"], p, naive=naive, pause=0.05 if naive else 0.0))
        c1.close(); c2.close()
        n_ok = sum(1 for v in out.values() if v[0] == "OK")
        n_audit = audit_actions(env, p).count("placement.activated")
        state = env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"]
        return n_ok, n_audit, state, sorted(v[0] for v in out.values())
    good = [trial(False) for _ in range(TRIALS)]
    ok = all(g[0] == 1 and g[1] == 1 and g[2] == "ACTIVE" and g[3] == ["INVALID_TRANSITION", "OK"] for g in good)
    ctrl = [trial(True) for _ in range(30)]
    double = sum(1 for g in ctrl if g[0] == 2 or g[1] == 2)
    record("T-01", "Two actors activate the same placement simultaneously", "PASS" if ok else "FAIL",
           trials=TRIALS, proper_exactly_one_success_and_one_audit=sum(1 for g in good if g[0] == 1 and g[1] == 1),
           control_naive_no_lock_trials=30, control_double_activation_detected=double,
           note="control proves the test can detect a violation; the DB gate alone does not prevent duplicate ACTIVE->ACTIVE")


# ------------------------------------------------------------------ T-02
def t02(env, U, opp):
    def trial(variant):
        naive = variant != "A"
        p = seed.make_doc_pending(env, U, "s1", opp)
        item = env.admin.execute("SELECT id FROM checklist_item WHERE placement_id=%s AND kind='DOC_INSURANCE'", (p,)).fetchone()["id"]
        c1, c2 = env.conn(), env.conn()
        act_first = random.random() < 0.5
        out = race(lambda: lc.activate(c1, U["ec1"], p, naive=naive, pause=0.05),
                   lambda: lc.review_document(c2, U["legal1"], item, "REJECTED", naive=naive),
                   delay_a=0.0 if act_first else 0.02, delay_b=0.02 if act_first else 0.0)
        c1.close(); c2.close()
        rows = env.admin.execute("SELECT id,action FROM audit_event WHERE correlation_id IS NOT NULL ORDER BY id").fetchall()
        act = [r["id"] for r in rows if r["action"] == "placement.activated" and r["id"] > 0]
        # restrict to this placement
        a_ids = [r["id"] for r in env.admin.execute(
            "SELECT id FROM audit_event WHERE action='placement.activated' AND subject_id=%s", (p,)).fetchall()]
        r_ids = [r["id"] for r in env.admin.execute(
            "SELECT id FROM audit_event WHERE action='checklist_item.rejected' AND subject_id=%s", (item,)).fetchall()]
        forbidden = bool(a_ids and r_ids and r_ids[0] < a_ids[0])
        order = ("activation_first" if a_ids and r_ids and a_ids[0] < r_ids[0]
                 else "rejection_first_activation_denied" if r_ids and not a_ids else "other")
        return forbidden, order, out["a"][0]
    summary = {}
    for variant, n in (("A", TRIALS), ("B", 40), ("C", 40)):
        if variant == "B":
            env.admin.execute("ALTER TABLE placement DISABLE TRIGGER trg_placement_gate")
        res = [trial(variant) for _ in range(n)]
        if variant == "B":
            env.admin.execute("ALTER TABLE placement ENABLE TRIGGER trg_placement_gate")
        summary[variant] = {"trials": n, "forbidden": sum(1 for r in res if r[0]),
                            "orders": {k: sum(1 for r in res if r[1] == k) for k in {r[1] for r in res}},
                            "activation_outcomes": {k: sum(1 for r in res if r[2] == k) for k in {r[2] for r in res}}}
    ok = summary["A"]["forbidden"] == 0 and summary["C"]["forbidden"] == 0 and summary["B"]["forbidden"] > 0
    record("T-02", "Document rejected while activation is being attempted", "PASS" if ok else "FAIL",
           A_proper_lock_and_trigger=summary["A"], B_control_naive_no_lock_no_trigger=summary["B"],
           C_naive_no_lock_with_db_trigger=summary["C"])


def t02b(env, U, opp):
    p = seed.make_doc_pending(env, U, "s1", opp, docs_approved=False)
    c = env.conn()
    msgs = []
    for sql in ("UPDATE placement SET state='ACTIVE' WHERE id=%s",):
        try:
            c.execute(sql, (p,)); msgs.append("NOT_BLOCKED")
        except psycopg.errors.RaiseException as e:
            msgs.append(str(e).split("\n")[0])
    p2 = seed.make_placement(env, U["s2"], opp)  # PENDING_ACADEMIC_APPROVAL -> ACTIVE skipping approval
    try:
        c.execute("UPDATE placement SET state='ACTIVE' WHERE id=%s", (p2,)); msgs.append("NOT_BLOCKED")
    except psycopg.errors.RaiseException as e:
        msgs.append(str(e).split("\n")[0])
    st = env.admin.execute("SELECT state FROM placement WHERE id IN (%s,%s) ORDER BY id", (p, p2)).fetchall()
    ok = all(m.startswith("GATE") for m in msgs) and [s["state"] for s in st] == ["DOCUMENTATION_PENDING", "PENDING_ACADEMIC_APPROVAL"]
    # business-level denial leaves no audit trail of activation and no state change
    before = len(env.admin.execute("SELECT 1 FROM audit_event").fetchall())
    c1 = env.conn()
    try:
        lc.activate(c1, U["ec1"], p); code = "NOT_BLOCKED"
    except BusinessError as e:
        code = e.code
    after = len(env.admin.execute("SELECT 1 FROM audit_event").fetchall())
    c.close(); c1.close()
    ok = ok and code == "ACTIVATION_CONDITIONS_UNMET" and before == after
    record("T-02b", "Bypassing the application guard (raw SQL) and denied-command atomicity", "PASS" if ok else "FAIL",
           db_gate_messages=msgs, app_error_code=code, audit_rows_added_by_denied_command=after - before)


# ------------------------------------------------------------------ T-03
def t03(env, U, opp_alfa, opp_beta):
    p1 = seed.make_placement(env, U["s1"], opp_alfa, supervisor_id=U["ws_alfa"], faculty_id=U["f1"])
    p2 = seed.make_placement(env, U["s3"], opp_beta, supervisor_id=U["ws_beta"])
    p3 = seed.make_placement(env, U["s2"], opp_alfa, supervisor_id=U["ws_alfa2"])
    expected = {"hm_alfa": {p1, p3}, "hm_beta": {p2}, "ws_alfa": {p1}, "ws_alfa2": {p3}, "ws_beta": {p2},
                "s1": {p1}, "s2": {p3}, "s3": {p2}, "f1": {p1}, "pc_sys": {p1, p3}, "pc_adm": {p2},
                "ec1": {p1, p2, p3}, "legal1": {p1, p2, p3}}
    cur = env.conn().cursor()
    checks, failures, ext_notfound, int_forbidden = 0, [], 0, 0
    for key, exp in expected.items():
        subj = authz.subject(cur, U[key])
        listed = set(authz.visible_placement_ids(cur, subj))
        checks += 1
        if listed != exp:
            failures.append(f"list {key}: {listed} != {exp}")
        for pid in (p1, p2, p3):
            checks += 1
            can = authz.can_read(cur, subj, pid)
            if can != (pid in exp):
                failures.append(f"can_read {key} {pid}")
            if not can:
                try:
                    authz.authorize(cur, subj, "placement:read", pid); failures.append(f"no denial {key} {pid}")
                except authz.NotFound:
                    ext_notfound += subj["role"] in authz.EXTERNAL
                    if subj["role"] not in authz.EXTERNAL:
                        failures.append(f"internal got NotFound {key}")
                except authz.Forbidden:
                    int_forbidden += subj["role"] not in authz.EXTERNAL
                    if subj["role"] in authz.EXTERNAL:
                        failures.append(f"external got Forbidden {key}")
    action_cases = [("hm_alfa", "placement:activate", p1), ("hm_alfa", "placement:approve_academic", p1),
                    ("s1", "placement:activate", p1), ("pc_adm", "placement:approve_academic", p1),
                    ("pc_sys", "placement:activate", p1), ("ws_alfa", "document:review", p1),
                    ("s2", "progress:create", p1), ("f1", "placement:close", p1)]
    denied = 0
    for key, action, pid in action_cases:
        checks += 1
        try:
            authz.authorize(cur, authz.subject(cur, U[key]), action, pid); failures.append(f"allowed {key} {action}")
        except (authz.Forbidden, authz.NotFound):
            denied += 1
    allowed = 0
    for key, action, pid in [("ec1", "placement:activate", p1), ("pc_sys", "placement:approve_academic", p1),
                             ("legal1", "document:review", p2), ("s1", "progress:create", p1),
                             ("ws_alfa", "placement:propose_change", p1)]:
        checks += 1
        try:
            authz.authorize(cur, authz.subject(cur, U[key]), action, pid); allowed += 1
        except Exception:
            failures.append(f"positive case denied {key} {action}")
    view = authz.external_student_view(cur, U["s1"])
    checks += 1
    if set(view) != {"display_name", "program_code"}:
        failures.append(f"projection leaks fields: {set(view)}")
    record("T-03", "Role AND relationship authorization; external isolation; minimal projection",
           "PASS" if not failures else "FAIL", assertions=checks, failures=failures,
           external_denials_as_not_found=ext_notfound, internal_denials_as_forbidden=int_forbidden,
           negative_action_cases_denied=f"{denied}/{len(action_cases)}", positive_action_cases_allowed=f"{allowed}/5",
           projection_fields=sorted(view))


# ------------------------------------------------------------------ T-04 / T-08
def t04(env, U, opp):
    p = seed.make_active(env, U, "s1", opp)
    cs, cp, cec = env.conn(), env.conn(), env.conn()
    log, fails = {}, []

    def expect(label, fn, code):
        try:
            fn(); got = "OK"
        except BusinessError as e:
            got = e.code
        log[label] = got
        if got != code:
            fails.append(f"{label}: expected {code} got {got}")
    st = lambda: env.admin.execute("SELECT state FROM placement WHERE id=%s", (p,)).fetchone()["state"]
    expect("complete_with_nothing", lambda: lc.confirm_completion(cp, U["pc_sys"], p), "COMPLETION_EVIDENCE_MISSING")
    lc.submit_evidence(cs, U["s1"], p, "FINAL_REPORT")
    expect("complete_with_report_only", lambda: lc.confirm_completion(cp, U["pc_sys"], p), "COMPLETION_EVIDENCE_MISSING")
    lc.record_hours(cs, U["s1"], p, 40)
    lc.submit_evidence(cs, U["s1"], p, "FINAL_EVALUATION")
    expect("complete_with_40_of_100_hours", lambda: lc.confirm_completion(cp, U["pc_sys"], p), "COMPLETION_EVIDENCE_MISSING")
    if st() != "ACTIVE":
        fails.append("state changed by denied completion")
    try:
        cp.execute("UPDATE placement SET state='COMPLETED' WHERE id=%s", (p,)); log["raw_sql_complete"] = "NOT_BLOCKED"; fails.append("raw bypass not blocked")
    except psycopg.errors.RaiseException as e:
        log["raw_sql_complete"] = str(e).split("\n")[0]
    expect("close_before_completed", lambda: lc.close_placement(cec, U["ec1"], p), "INVALID_TRANSITION")
    lc.record_hours(cs, U["s1"], p, 70)  # 110h total, recomputed from source rows
    expect("complete_with_all_evidence", lambda: lc.confirm_completion(cp, U["pc_sys"], p), "OK")
    expect("close_after_completed", lambda: lc.close_placement(cec, U["ec1"], p), "OK")
    if st() != "CLOSED":
        fails.append("final state not CLOSED")
    # Stale-flag defence: satisfied flag forced true manually, hours rows insufficient -> recompute must still deny
    q = seed.make_active(env, U, "s2", opp)
    env.admin.execute("UPDATE completion_requirement SET satisfied=true WHERE placement_id=%s AND kind IN ('FINAL_REPORT','FINAL_EVALUATION')", (q,))
    env.admin.execute("UPDATE completion_requirement SET satisfied=true WHERE placement_id=%s AND kind='MIN_HOURS'", (q,))
    cq = env.conn()
    expect("stale_hours_flag_recomputed_from_rows", lambda: lc.confirm_completion(cq, U["pc_sys"], q), "COMPLETION_EVIDENCE_MISSING")
    [c.close() for c in (cs, cp, cec, cq)]
    record("T-04", "Closure integrity: completion/closure with missing evidence", "PASS" if not fails else "FAIL",
           outcomes=log, failures=fails,
           variant_not_executed="concurrent evidence withdrawal during confirm_completion (same lock pattern as T-02) - NOT EXECUTED")


def t08(env, U, opp):
    p = seed.make_doc_pending(env, U, "s1", opp)
    c = env.conn()
    try:
        lc.record_hours(c, U["s1"], p, 5); got = "NOT_BLOCKED"
    except BusinessError as e:
        got = e.code
    n = env.admin.execute("SELECT count(*) AS n FROM progress_entry WHERE placement_id=%s", (p,)).fetchone()["n"]
    c.close()
    record("T-08", "No hours/progress before activation (BR-02)", "PASS" if got == "PLACEMENT_NOT_ACTIVE" and n == 0 else "FAIL",
           outcome=got, rows_inserted=n)


# ------------------------------------------------------------------ T-05
def t05(env, U, opp):
    p = seed.make_active(env, U, "s1", opp)
    env.admin.execute("INSERT INTO supervisor_assignment VALUES (%s,%s,'FACULTY')", (p, U["f1"]))
    cws, cpc, cbad, cx = env.conn(), env.conn(), env.conn(), env.conn()
    fails = []
    v2 = lc.propose_change(cws, U["ws_alfa"], p, location="Site B (remote hybrid)")
    cur_ver = env.admin.execute("SELECT current_version_id FROM placement WHERE id=%s", (p,)).fetchone()["current_version_id"]
    v1 = env.admin.execute("SELECT id FROM placement_version WHERE placement_id=%s AND version_no=1", (p,)).fetchone()["id"]
    if cur_ver != v1:
        fails.append("current version changed before approval")
    try:
        lc.approve_version(cbad, U["pc_adm"], v2); fails.append("wrong-program coordinator approved")
    except authz.Forbidden:
        pass
    try:
        lc.propose_change(cx, U["ws_beta"], p, location="evil"); fails.append("foreign supervisor proposed change")
    except authz.NotFound:
        pass
    lc.approve_version(cpc, U["pc_sys"], v2)
    cur_ver = env.admin.execute("SELECT current_version_id FROM placement WHERE id=%s", (p,)).fetchone()["current_version_id"]
    if cur_ver != v2:
        fails.append("current version not updated after approval")
    rows = env.admin.execute("SELECT version_no,location,status FROM placement_version WHERE placement_id=%s ORDER BY version_no", (p,)).fetchall()
    if [(r["version_no"], r["location"], r["status"]) for r in rows] != [(1, "Site A", "APPROVED"), (2, "Site B (remote hybrid)", "APPROVED")]:
        fails.append(f"versions wrong: {rows}")
    try:
        cws.execute("UPDATE placement_version SET location='tampered' WHERE id=%s", (v1,)); fails.append("version content mutable")
        immut = "NOT_BLOCKED"
    except psycopg.errors.RaiseException as e:
        immut = str(e).split("\n")[0]
    ev = env.admin.execute("""SELECT action,before_state,after_state FROM audit_event
                              WHERE (subject_type='placement_version' AND subject_id=%s) OR (subject_type='placement' AND subject_id=%s)
                              ORDER BY id""", (v2, p)).fetchall()
    actions = [e["action"] for e in ev]
    approved = [e for e in ev if e["action"] == "placement.version_approved"]
    ok_audit = (actions == ["placement.change_proposed", "placement.version_approved"] and
                approved[0]["before_state"]["location"] == "Site A" and approved[0]["after_state"]["location"] == "Site B (remote hybrid)")
    if not ok_audit:
        fails.append(f"audit incomplete: {actions}")
    [c.close() for c in (cws, cpc, cbad, cx)]
    record("T-05", "Relevant change after approval -> new version, reapproval, history preserved", "PASS" if not fails else "FAIL",
           failures=fails, versions=[(r["version_no"], r["location"], r["status"]) for r in rows], audit_actions=actions,
           db_immutability_message=immut,
           not_covered="state of the placement while a version is pending, and urgent-change override: OPEN / TO VALIDATE")


# ------------------------------------------------------------------ T-06
def t06(env, U, opp_sys):
    fails = []
    cpc, cs1, cadm = env.conn(), env.conn(), env.conn()
    v1 = policy.create_policy_version(cpc, U["pc_sys"], "ING-SIS",
                                      [{"type": "CREDITS_MIN", "value": 100}, {"type": "ACADEMIC_LEVEL_MIN", "value": 6}])
    a1 = policy.submit_application(cs1, U["s1"], opp_sys)
    time.sleep(0.05)
    v2 = policy.create_policy_version(cpc, U["pc_sys"], "ING-SIS",
                                      [{"type": "CREDITS_MIN", "value": 110}, {"type": "ACADEMIC_LEVEL_MIN", "value": 6}])
    a2 = policy.submit_application(cs1, U["s1"], opp_sys)
    r = {x["id"]: x for x in env.admin.execute("SELECT * FROM application WHERE id IN (%s,%s)", (a1, a2)).fetchall()}
    if not (r[a1]["state"] == "SUBMITTED" and r[a1]["policy_version_id"] == v1 and r[a1]["eligibility_result"]["result"] == "ELIGIBLE"):
        fails.append("first application should be ELIGIBLE under v1 and keep v1")
    if not (r[a2]["state"] == "INELIGIBLE" and r[a2]["policy_version_id"] == v2 and "credits 105 < 110" in r[a2]["eligibility_result"]["reasons"]):
        fails.append("second application should be NOT_ELIGIBLE under v2 with reason")
    bad = {}
    for label, cond in {"script": [{"type": "EVAL", "value": "credits > 3"}], "extra_key": [{"type": "CREDITS_MIN", "value": 1, "expr": "x"}],
                        "bad_value": [{"type": "CREDITS_MIN", "value": "many"}], "empty": []}.items():
        try:
            policy.create_policy_version(cpc, U["pc_sys"], "ING-SIS", cond); bad[label] = "ACCEPTED"; fails.append(f"accepted {label}")
        except policy.PolicyValidationError:
            bad[label] = "rejected"
    try:
        policy.create_policy_version(cadm, U["pc_adm"], "ING-SIS", [{"type": "CREDITS_MIN", "value": 1}]); fails.append("foreign coordinator changed policy")
        foreign = "ACCEPTED"
    except authz.Forbidden:
        foreign = "Forbidden"
    audit_n = env.admin.execute("SELECT count(*) AS n FROM audit_event WHERE action='policy.version_created'").fetchone()["n"]
    [c.close() for c in (cpc, cs1, cadm)]
    record("T-06", "Eligibility rule change applies to new evaluations without code change; vocabulary is closed",
           "PASS" if not fails else "FAIL", failures=fails, v1_application=r[a1]["eligibility_result"]["result"],
           v2_application=r[a2]["eligibility_result"]["result"], invalid_policies=bad, foreign_coordinator=foreign,
           policy_audit_events=audit_n,
           not_covered="re-evaluation of in-flight applications and policy effective dates in the future: OPEN / TO VALIDATE")


# ------------------------------------------------------------------ T-07
def t07(env, U, opp):
    p = seed.make_doc_pending(env, U, "s1", opp)
    c = env.conn()
    lc.activate(c, U["ec1"], p)
    msgs = {}
    for label, sql in (("app_update", "UPDATE audit_event SET action='x' WHERE subject_id=%s"),
                       ("app_delete", "DELETE FROM audit_event WHERE subject_id=%s")):
        try:
            c.execute(sql, (p,)); msgs[label] = "NOT_BLOCKED"
        except psycopg.errors.InsufficientPrivilege:
            msgs[label] = "permission denied"
        except psycopg.errors.RaiseException as e:
            msgs[label] = str(e).split("\n")[0]
    for label, sql in (("owner_update", "UPDATE audit_event SET action='x' WHERE subject_id=%s"),
                       ("owner_delete", "DELETE FROM audit_event WHERE subject_id=%s")):
        try:
            env.admin.execute(sql, (p,)); msgs[label] = "NOT_BLOCKED"
        except psycopg.errors.RaiseException as e:
            msgs[label] = str(e).split("\n")[0]
    intact = env.admin.execute("SELECT count(*) AS n FROM audit_event WHERE subject_id=%s AND action='placement.activated'", (p,)).fetchone()["n"]
    c.close()
    ok = (msgs["app_update"] == "permission denied" and msgs["app_delete"] == "permission denied"
          and msgs["owner_update"].startswith("IMMUTABLE") and msgs["owner_delete"].startswith("IMMUTABLE") and intact == 1)
    record("T-07", "Audit history is append-only for the application role and for the table owner", "PASS" if ok else "FAIL",
           outcomes=msgs, activation_event_intact=intact,
           limitation="a database superuser can DISABLE the trigger; not tested, documented as residual risk")


def main():
    env = Env()
    try:
        U = seed.seed_base(env)
        P = U["P"]
        opp_alfa = seed.make_opportunity(env, 1, P["ING-SIS"], "Alfa opportunity")
        opp_beta = seed.make_opportunity(env, 2, P["ADM"], "Beta opportunity")
        t01(env, U, opp_alfa)
        t02(env, U, opp_alfa)
        t02b(env, U, opp_alfa)
        # T-03 runs on an ISOLATED database: its expected visibility sets are exact, so other tests' placements must not exist.
        # (Run 1 failed because T-03 shared a database with other tests - a fixture-scope defect, see validation-results.md)
        env3 = Env()
        try:
            U3 = seed.seed_base(env3)
            t03(env3, U3, seed.make_opportunity(env3, 1, U3["P"]["ING-SIS"], "Alfa"), seed.make_opportunity(env3, 2, U3["P"]["ADM"], "Beta"))
        finally:
            env3.close()
        t04(env, U, opp_alfa)
        t05(env, U, opp_alfa)
        t06(env, U, opp_alfa)
        t07(env, U, opp_alfa)
        t08(env, U, opp_alfa)
        meta = {
            "executed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "executor": "assistant-run in an isolated sandbox on behalf of the team (NOT yet re-run by the team)",
            "source_commit": None,
            "environment": {"os": platform.platform(), "python": platform.python_version(),
                            "postgres": env.admin.execute("SHOW server_version").fetchone()["server_version"],
                            "psycopg": psycopg.__version__, "trials_per_race": TRIALS},
        }
        summary = {"PASS": sum(r["status"] == "PASS" for r in RESULTS), "FAIL": sum(r["status"] == "FAIL" for r in RESULTS)}
        out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence", "results.json")
        json.dump({"meta": meta, "summary": summary, "results": RESULTS}, open(out, "w"), indent=2, default=str)
        print("\nSUMMARY", summary, "->", out)
        return 0 if summary["FAIL"] == 0 else 1
    finally:
        env.close()


if __name__ == "__main__":
    sys.exit(main())
