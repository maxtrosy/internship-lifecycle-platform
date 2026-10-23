"""Shared pytest fixtures: isolated PostgreSQL (pgserver or DATABASE_URL) + synthetic seed."""
from __future__ import annotations

import datetime as dt
import os
import pathlib
import sys
import tempfile
import threading
import time

import psycopg
import pytest
from psycopg.rows import dict_row

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from migrations.schema_sql import SCHEMA  # noqa: E402


class DbEnv:
    def __init__(self):
        url = os.environ.get("DATABASE_URL")
        if url:
            self.uri = url
            self.owned = False
        else:
            import pgserver

            self.srv = pgserver.get_server(tempfile.mkdtemp(prefix="dh05_backend_"))
            self.uri = self.srv.get_uri()
            self.owned = True
        with psycopg.connect(self.uri, autocommit=True) as c:
            c.execute(SCHEMA)
        self.admin = psycopg.connect(self.uri, autocommit=True, row_factory=dict_row)

    def conn(self, app_role: bool = True):
        c = psycopg.connect(self.uri, autocommit=True, row_factory=dict_row)
        if app_role:
            c.execute("SET ROLE app_user")
        return c

    def close(self):
        self.admin.close()
        if getattr(self, "owned", False):
            self.srv.cleanup()


@pytest.fixture(scope="session")
def env():
    e = DbEnv()
    os.environ["DATABASE_URL"] = e.uri
    os.environ.setdefault("JWT_SECRET", "test-secret")
    yield e
    e.close()


_TABLES = (
    "academic_program, host_org, user_account, role_assignment, invitation, policy_version, "
    "opportunity, application, placement, placement_version, supervisor_assignment, "
    "checklist_item, completion_requirement, progress_entry, audit_event"
)


@pytest.fixture(autouse=True)
def _clean_db(env):
    env.admin.execute(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE")
    yield


def seed_base(env: DbEnv) -> dict:
    c = env.admin
    c.execute("INSERT INTO academic_program(code,name) VALUES "
              "('ING-SIS','Systems Engineering (synthetic)'),('ADM','Business Admin (synthetic)')")
    c.execute("INSERT INTO host_org(name) VALUES ('Org Alfa (synthetic)'),('Org Beta (synthetic)')")
    P = {r["code"]: r["id"] for r in c.execute("SELECT * FROM academic_program").fetchall()}
    users: dict[str, int] = {}

    def u(key, name, roles, credits=None, level=None, courses=()):
        users[key] = c.execute(
            "INSERT INTO user_account(display_name, credits, academic_level, completed_courses) "
            "VALUES (%s,%s,%s,%s) RETURNING id",
            (name, credits, level, list(courses)),
        ).fetchone()["id"]
        for role, program, org in roles:
            c.execute(
                "INSERT INTO role_assignment(user_id, role, program_id, host_org_id) VALUES (%s,%s,%s,%s)",
                (users[key], role, P.get(program) if program else None, org),
            )

    u("s1", "Student One", [("STUDENT", "ING-SIS", None)], credits=105, level=7, courses=("MAT101",))
    u("s2", "Student Two", [("STUDENT", "ING-SIS", None)], credits=90, level=5)
    u("s3", "Student Three", [("STUDENT", "ADM", None)], credits=120, level=8)
    u("pc_sys", "Coord Sys", [("PROGRAM_COORDINATOR", "ING-SIS", None)])
    u("pc_adm", "Coord Adm", [("PROGRAM_COORDINATOR", "ADM", None)])
    u("ec1", "Experiential Coord 1", [("EXPERIENTIAL_COORDINATOR", None, None)])
    u("legal1", "Legal Reviewer", [("LEGAL_REVIEWER", None, None)])
    u("hm_alfa", "Host Member Alfa", [("HOST_ORG_MEMBER", None, 1)])
    u("hm_beta", "Host Member Beta", [("HOST_ORG_MEMBER", None, 2)])
    u("ws_alfa", "Workplace Sup Alfa", [("WORKPLACE_SUPERVISOR", None, 1)])
    u("ws_alfa2", "Workplace Sup Alfa 2", [("WORKPLACE_SUPERVISOR", None, 1)])
    u("ws_beta", "Workplace Sup Beta", [("WORKPLACE_SUPERVISOR", None, 2)])
    u("f1", "Faculty Sup 1", [("FACULTY_SUPERVISOR", None, None)])
    u("dual1", "Dual", [("PROGRAM_COORDINATOR", "ING-SIS", None), ("FACULTY_SUPERVISOR", None, None)])
    users["P"] = P
    return users


def make_opportunity(env, org, program_id, title="Synthetic opportunity"):
    return env.admin.execute(
        "INSERT INTO opportunity(host_org_id,program_id,title) VALUES (%s,%s,%s) RETURNING id",
        (org, program_id, title),
    ).fetchone()["id"]


def make_placement(env, student_id, opp_id, supervisor_id=None, faculty_id=None):
    c = env.admin
    a = c.execute("INSERT INTO application(opportunity_id,student_id,state) VALUES (%s,%s,'SELECTED') RETURNING id",
                  (opp_id, student_id)).fetchone()["id"]
    p = c.execute("INSERT INTO placement(application_id,state) VALUES (%s,'PENDING_ACADEMIC_APPROVAL') RETURNING id",
                  (a,)).fetchone()["id"]
    v = c.execute(
        """INSERT INTO placement_version(placement_id,version_no,workplace_supervisor_id,start_date,end_date,location,responsibilities)
           VALUES (%s,1,%s,%s,%s,'Site A','Synthetic responsibilities') RETURNING id""",
        (p, supervisor_id, dt.date(2026, 11, 2), dt.date(2027, 2, 26)),
    ).fetchone()["id"]
    c.execute("UPDATE placement SET current_version_id=%s WHERE id=%s", (v, p))
    if faculty_id:
        c.execute("INSERT INTO supervisor_assignment VALUES (%s,%s,'FACULTY')", (p, faculty_id))
    return p


def make_doc_pending(env, users, student, opp, docs_approved=True, supervisor="ws_alfa"):
    p = make_placement(env, users[student], opp, supervisor_id=users[supervisor] if supervisor else None)
    c = env.admin
    for k in ("DOC_INSTITUTIONAL_AGREEMENT", "DOC_INSURANCE", "DOC_CONFIDENTIALITY"):
        c.execute("INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,%s,%s)",
                  (p, k, "APPROVED" if docs_approved else "REQUIRED"))
    c.execute("INSERT INTO checklist_item(placement_id,kind,status) VALUES (%s,'COND_SUPERVISOR_ASSIGNED',%s)",
              (p, "APPROVED" if supervisor else "REQUIRED"))
    c.execute("UPDATE placement_version SET status='APPROVED' WHERE placement_id=%s", (p,))
    c.execute("UPDATE placement SET state='DOCUMENTATION_PENDING', activation_requirements_instantiated=true WHERE id=%s", (p,))
    return p


def make_active(env, users, student, opp):
    p = make_doc_pending(env, users, student, opp)
    env.admin.execute("UPDATE placement SET state='ACTIVE' WHERE id=%s", (p,))
    env.admin.execute(
        """INSERT INTO completion_requirement(placement_id,kind,threshold) VALUES
           (%s,'FINAL_REPORT',NULL),(%s,'FINAL_EVALUATION',NULL),(%s,'MIN_HOURS',100)""",
        (p, p, p),
    )
    env.admin.execute("UPDATE placement SET completion_requirements_instantiated=true WHERE id=%s", (p,))
    return p


def race(fn_a, fn_b, delay_a=0.0, delay_b=0.0):
    barrier, out = threading.Barrier(2), {}

    def wrap(name, fn, delay):
        barrier.wait()
        time.sleep(delay)
        try:
            out[name] = ("OK", fn())
        except Exception as exc:  # noqa: BLE001
            out[name] = (type(exc).__name__, getattr(exc, "code", str(exc)))

    ts = [
        threading.Thread(target=wrap, args=("a", fn_a, delay_a)),
        threading.Thread(target=wrap, args=("b", fn_b, delay_b)),
    ]
    [t.start() for t in ts]
    [t.join() for t in ts]
    return out
