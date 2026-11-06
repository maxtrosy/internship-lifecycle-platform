"""Synthetic seed data (RNF-06). Run: python -m app.seed (after alembic upgrade head)."""
from __future__ import annotations

import os

from app import db
from app import security
from psycopg.types.json import Jsonb

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "Demo-Only-2026!")


def seed(cur) -> dict:
    cur.execute("INSERT INTO academic_program(code,name) VALUES "
                "('ING-SIS','Systems Engineering (synthetic)'),('ADM','Business Admin (synthetic)')")
    cur.execute("INSERT INTO host_org(name) VALUES ('Org Alfa (synthetic)'),('Org Beta (synthetic)')")
    programs = {r["code"]: r["id"] for r in cur.execute("SELECT * FROM academic_program").fetchall()}
    users: dict[str, int] = {}

    def add_user(key: str, name: str, roles: list[tuple[str, str | None, int | None]],
                 email: str | None = None, credits: int | None = None,
                 level: int | None = None, courses: tuple[str, ...] = ()) -> None:
        uid = cur.execute(
            """INSERT INTO user_account(username,email,password_hash,is_active,display_name,
                                         credits,academic_level,completed_courses)
               VALUES (%s,%s,%s,true,%s,%s,%s,%s) RETURNING id""",
            (key, email or f"{key}@demo.local", security.hash_password(DEMO_PASSWORD),
             name, credits, level, list(courses)),
        ).fetchone()["id"]
        for role, program_code, org_id in roles:
            cur.execute(
                "INSERT INTO role_assignment(user_id, role, program_id, host_org_id) VALUES (%s,%s,%s,%s)",
                (uid, role, programs[program_code] if program_code else None, org_id),
            )
        users[key] = uid

    add_user("s1", "Student One", [("STUDENT", "ING-SIS", None)], credits=105, level=7, courses=("MAT101",))
    add_user("s2", "Student Two", [("STUDENT", "ING-SIS", None)], credits=90, level=5)
    add_user("s3", "Student Three", [("STUDENT", "ADM", None)], credits=120, level=8)
    add_user("pc_sys", "Coord Sys", [("PROGRAM_COORDINATOR", "ING-SIS", None)])
    add_user("pc_adm", "Coord Adm", [("PROGRAM_COORDINATOR", "ADM", None)])
    add_user("ec1", "Experiential Coord 1", [("EXPERIENTIAL_COORDINATOR", None, None)])
    add_user("legal1", "Legal Reviewer", [("LEGAL_REVIEWER", None, None)])
    add_user("hm_alfa", "Host Member Alfa", [("HOST_ORG_MEMBER", None, 1)])
    add_user("hm_beta", "Host Member Beta", [("HOST_ORG_MEMBER", None, 2)])
    add_user("ws_alfa", "Workplace Sup Alfa", [("WORKPLACE_SUPERVISOR", None, 1)])
    add_user("ws_alfa2", "Workplace Sup Alfa 2", [("WORKPLACE_SUPERVISOR", None, 1)])
    add_user("ws_beta", "Workplace Sup Beta", [("WORKPLACE_SUPERVISOR", None, 2)])
    add_user("f1", "Faculty Sup 1", [("FACULTY_SUPERVISOR", None, None)])
    # At least one user with TWO roles (T-03/T-21 multi-role coverage).
    add_user("dual1", "Dual Coordinator/Faculty",
             [("PROGRAM_COORDINATOR", "ING-SIS", None), ("FACULTY_SUPERVISOR", None, None)])
    for code, coordinator in (("ING-SIS", "pc_sys"), ("ADM", "pc_adm")):
        cur.execute(
            "INSERT INTO policy_version(policy_key,version_no,conditions,created_by) VALUES (%s,1,%s,%s)",
            (f"ACTIVATION:{code}", Jsonb([
                {"type": "REQUIRE_DOCUMENTS", "value": ["DOC_INSURANCE"]},
                {"type": "SUPERVISORS_ASSIGNED", "value": True},
            ]), users[coordinator]),
        )
        cur.execute(
            "INSERT INTO policy_version(policy_key,version_no,conditions,created_by) VALUES (%s,1,%s,%s)",
            (f"COMPLETION:{code}", Jsonb([
                {"type": "FINAL_REPORT", "value": True},
                {"type": "FINAL_EVALUATION", "value": True},
                {"type": "MIN_HOURS", "value": 100},
            ]), users[coordinator]),
        )
    users["programs"] = programs
    return users


def main() -> None:
    if os.environ.get("APP_ENV", "development").strip().lower() != "development":
        raise RuntimeError("The synthetic seed is available only with APP_ENV=development")
    with db.admin() as cur:
        seed(cur)
    print("Synthetic development accounts and sample data created.")


if __name__ == "__main__":
    main()
