"""Synthetic seed data (RNF-06). Run: python -m app.seed (after alembic upgrade head)."""
from __future__ import annotations

from app import db


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
            "INSERT INTO user_account(email, display_name, credits, academic_level, completed_courses) "
            "VALUES (%s,%s,%s,%s,%s) RETURNING id",
            (email, name, credits, level, list(courses)),
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
    users["programs"] = programs
    return users


def main() -> None:
    with db.admin() as cur:
        seed(cur)
    print("seed complete")


if __name__ == "__main__":
    main()
