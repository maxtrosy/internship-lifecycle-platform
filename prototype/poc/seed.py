"""Synthetic fixtures only (RNF-06)."""
import datetime as dt
from psycopg.types.json import Jsonb


def seed_base(env):
    c = env.admin
    c.execute("INSERT INTO academic_program(code,name) VALUES ('ING-SIS','Systems Engineering (synthetic)'),('ADM','Business Admin (synthetic)')")
    c.execute("INSERT INTO host_org(name) VALUES ('Org Alfa (synthetic)'),('Org Beta (synthetic)')")
    P = {r["code"]: r["id"] for r in c.execute("SELECT * FROM academic_program").fetchall()}
    users = {}

    def u(key, name, role, program=None, org=None, credits=None, level=None, courses=()):
        users[key] = c.execute(
            """INSERT INTO user_account(display_name,role,program_id,host_org_id,credits,academic_level,completed_courses)
               VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (name, role, P.get(program) if program else None, org, credits, level, list(courses))).fetchone()["id"]
    u("s1", "Student One", "STUDENT", "ING-SIS", credits=105, level=7, courses=["MAT101"])
    u("s2", "Student Two", "STUDENT", "ING-SIS", credits=90, level=5)
    u("s3", "Student Three", "STUDENT", "ADM", credits=120, level=8)
    u("pc_sys", "Coord Sys", "PROGRAM_COORDINATOR", "ING-SIS")
    u("pc_adm", "Coord Adm", "PROGRAM_COORDINATOR", "ADM")
    u("ec1", "Experiential Coord 1", "EXPERIENTIAL_COORDINATOR")
    u("legal1", "Legal Reviewer", "LEGAL_REVIEWER")
    u("hm_alfa", "Host Member Alfa", "HOST_ORG_MEMBER", org=1)
    u("hm_beta", "Host Member Beta", "HOST_ORG_MEMBER", org=2)
    u("ws_alfa", "Workplace Sup Alfa", "WORKPLACE_SUPERVISOR", org=1)
    u("ws_alfa2", "Workplace Sup Alfa 2", "WORKPLACE_SUPERVISOR", org=1)
    u("ws_beta", "Workplace Sup Beta", "WORKPLACE_SUPERVISOR", org=2)
    u("f1", "Faculty Sup 1", "FACULTY_SUPERVISOR")
    users["P"] = P
    return users


def make_opportunity(env, org, program_id, title="Synthetic opportunity"):
    return env.admin.execute("INSERT INTO opportunity(host_org_id,program_id,title) VALUES (%s,%s,%s) RETURNING id",
                             (org, program_id, title)).fetchone()["id"]


def make_placement(env, student_id, opp_id, state="PENDING_ACADEMIC_APPROVAL", supervisor_id=None, faculty_id=None):
    """Create application+placement+version 1 directly (synthetic fixture, bypassing commands)."""
    c = env.admin
    a = c.execute("INSERT INTO application(opportunity_id,student_id,state) VALUES (%s,%s,'SELECTED') RETURNING id",
                  (opp_id, student_id)).fetchone()["id"]
    p = c.execute("INSERT INTO placement(application_id,state) VALUES (%s,'PENDING_ACADEMIC_APPROVAL') RETURNING id", (a,)).fetchone()["id"]
    v = c.execute("""INSERT INTO placement_version(placement_id,version_no,workplace_supervisor_id,start_date,end_date,location,responsibilities)
                     VALUES (%s,1,%s,%s,%s,'Site A','Synthetic responsibilities') RETURNING id""",
                  (p, supervisor_id, dt.date(2026, 11, 2), dt.date(2027, 2, 26))).fetchone()["id"]
    c.execute("UPDATE placement SET current_version_id=%s WHERE id=%s", (v, p))
    if faculty_id:
        c.execute("INSERT INTO supervisor_assignment VALUES (%s,%s,'FACULTY')", (p, faculty_id))
    return p


def make_doc_pending(env, users, student, opp, docs_approved=True, supervisor="ws_alfa"):
    """Placement in DOCUMENTATION_PENDING with 3 documents + supervisor condition (fixture via admin)."""
    p = make_placement(env, users[student], opp, supervisor_id=users[supervisor] if supervisor else None)
    c = env.admin
    for k in ("DOC_INSTITUTIONAL_AGREEMENT", "DOC_INSURANCE", "DOC_CONFIDENTIALITY"):
        c.execute("INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,%s,%s)", (p, k, "APPROVED" if docs_approved else "REQUIRED"))
    c.execute("INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,'COND_SUPERVISOR_ASSIGNED',%s)",
              (p, "APPROVED" if supervisor else "REQUIRED"))
    c.execute("UPDATE placement_version SET status='APPROVED' WHERE placement_id=%s", (p,))
    c.execute("UPDATE placement SET state='DOCUMENTATION_PENDING', activation_requirements_instantiated=true WHERE id=%s", (p,))
    return p


def make_active(env, users, student, opp):
    p = make_doc_pending(env, users, student, opp)
    env.admin.execute("UPDATE placement SET state='ACTIVE' WHERE id=%s", (p,))
    env.admin.execute("""INSERT INTO completion_requirement(placement_id,kind,threshold) VALUES
                         (%s,'FINAL_REPORT',NULL),(%s,'FINAL_EVALUATION',NULL),(%s,'MIN_HOURS',100)""", (p, p, p))
    env.admin.execute("UPDATE placement SET completion_requirements_instantiated=true WHERE id=%s", (p,))
    return p
