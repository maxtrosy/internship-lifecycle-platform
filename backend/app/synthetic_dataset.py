"""Deterministic, relationship-connected data for disposable workflow validation.

Identity and catalog rows are bootstrap fixtures because the product has no account
or organization provisioning API. Every opportunity, application and placement
transition, document, report, hour, evaluation, message and audit event is created
through the same domain services used by the HTTP API.

This module deliberately does not pick institutional authorities or eligibility
rules. Callers must opt into clearly labeled demo eligibility and lifecycle records,
and provide temporary authority configuration for executable synthetic flows.
"""
from __future__ import annotations

import datetime as dt
from typing import Callable

from app import db, security
from app.config import get_settings
from app.errors import BusinessError
from app.modules.applications import service as applications
from app.modules.lifecycle import service as lifecycle
from app.modules.notifications import service as messaging
from app.modules.opportunities import service as opportunities
from app.modules.policies import service as policies
from app.seed import DEMO_PASSWORD


PROGRAMS = {
    "ING-SIS": "Systems Engineering (synthetic)",
    "ADM": "Business Admin (synthetic)",
}
BASE_ORGANIZATIONS = (
    "Org Alfa (synthetic)",
    "Org Beta (synthetic)",
)
ORGANIZATIONS = (
    "Cooperativa Río Claro (synthetic)",
    "Centro Horizonte de Investigación (synthetic)",
    "Agencia Distrital de Servicios (synthetic)",
    "Fundación Puente Abierto (synthetic)",
    "Laboratorio Verde Norte (synthetic)",
    "Biblioteca Comunitaria del Prado (synthetic)",
    "Taller Urbano de Innovación (synthetic)",
    "Unidad Universitaria de Extensión (synthetic)",
)
ALL_SYNTHETIC_ORGANIZATIONS = BASE_ORGANIZATIONS + ORGANIZATIONS

# Scenario labels correspond only to persisted states and record types in this schema.
PLACEMENT_SCENARIOS = (
    ("cierre-completo", "CLOSED"),
    ("finalizada-pendiente-de-cierre", "COMPLETED"),
    ("activa-con-avance", "ACTIVE"),
    ("activa-con-incidente-y-cambio", "ACTIVE"),
    ("activa-con-evaluacion-parcial", "ACTIVE"),
    ("activa-sin-informe", "ACTIVE"),
    ("documentacion-pendiente", "DOCUMENTATION_PENDING"),
    ("documento-en-revision", "DOCUMENTATION_PENDING"),
    ("documento-devuelto", "DOCUMENTATION_PENDING"),
    ("aprobacion-academica-pendiente-1", "PENDING_ACADEMIC_APPROVAL"),
    ("aprobacion-academica-pendiente-2", "PENDING_ACADEMIC_APPROVAL"),
    ("seleccion-rechazada-academicamente", "REJECTED"),
)

def _synthetic_demo_pdf() -> bytes:
    content = (
        b"BT /F1 18 Tf 72 760 Td (SYNTHETIC DEMONSTRATION ONLY) Tj ET\n"
        b"BT /F1 11 Tf 72 736 Td (Not an institutional or real internship record.) Tj ET\n"
    )
    objects = (
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"endstream",
    )
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii"))
        pdf.extend(body)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    trailer = (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    )
    pdf.extend(trailer.encode("ascii"))
    return bytes(pdf)


_PDF = _synthetic_demo_pdf()
_DEMO_ELIGIBILITY_POLICY = [
    {"type": "PROGRAM_IN", "value": ["__PROGRAM__"]},
    {"type": "CREDITS_MIN", "value": 100},
    {"type": "ACADEMIC_LEVEL_MIN", "value": 6},
]


def _one(cur, sql: str, params: tuple = ()):
    rows = cur.execute(sql, params).fetchall()
    if len(rows) > 1:
        raise RuntimeError("Synthetic fixture natural key is not unique; no rows were changed.")
    return rows[0] if rows else None


def _ensure_program(cur, code: str) -> int:
    row = _one(cur, "SELECT id,name FROM academic_program WHERE code=%s", (code,))
    if row:
        if row["name"] != PROGRAMS[code]:
            raise RuntimeError(f"Synthetic program {code} exists with an unexpected name.")
        return row["id"]
    return cur.execute(
        "INSERT INTO academic_program(code,name) VALUES (%s,%s) RETURNING id",
        (code, PROGRAMS[code]),
    ).fetchone()["id"]


def _require_program(cur, code: str) -> int:
    row = _one(cur, "SELECT id,name FROM academic_program WHERE code=%s", (code,))
    if row is None or row["name"] != PROGRAMS[code]:
        raise RuntimeError(f"Required synthetic program {code} is absent or differs; no rows were changed.")
    return row["id"]


def _ensure_organization(cur, name: str) -> int:
    row = _one(cur, "SELECT id FROM host_org WHERE name=%s ORDER BY id", (name,))
    if row:
        return row["id"]
    return cur.execute("INSERT INTO host_org(name) VALUES (%s) RETURNING id", (name,)).fetchone()["id"]


def _ensure_account(cur, *, username: str, display_name: str, role: str,
                    program_id: int | None = None, host_org_id: int | None = None,
                    credits: int | None = None, level: int | None = None,
                    courses: tuple[str, ...] = (),
                    password_hash_for: Callable[[str], str]) -> int:
    row = _one(
        cur,
        """SELECT id,email,display_name,credits,academic_level,completed_courses,is_active
           FROM user_account WHERE username=%s""",
        (username,),
    )
    email = f"{username}@horizon.example.test"
    if row is None:
        password_hash = password_hash_for(username)
        if not isinstance(password_hash, str) or not password_hash:
            raise RuntimeError("Synthetic account password provider returned an invalid hash.")
        user_id = cur.execute(
            """INSERT INTO user_account(username,email,password_hash,is_active,display_name,
                       credits,academic_level,completed_courses)
               VALUES (%s,%s,%s,true,%s,%s,%s,%s) RETURNING id""",
            (username, email, password_hash, display_name, credits, level, list(courses)),
        ).fetchone()["id"]
        cur.execute(
            """INSERT INTO role_assignment(user_id,role,program_id,host_org_id)
               VALUES (%s,%s,%s,%s)""",
            (user_id, role, program_id, host_org_id),
        )
        return user_id

    expected_courses = list(courses)
    if (row["email"], row["display_name"], row["credits"], row["academic_level"],
            row["completed_courses"], row["is_active"]) != (
            email, display_name, credits, level, expected_courses, True):
        raise RuntimeError(f"Synthetic account {username} exists with different profile data; preserved.")
    assignment = _one(
        cur,
        """SELECT id FROM role_assignment WHERE user_id=%s AND role=%s
           AND program_id IS NOT DISTINCT FROM %s AND host_org_id IS NOT DISTINCT FROM %s""",
        (row["id"], role, program_id, host_org_id),
    )
    if assignment is None:
        raise RuntimeError(f"Synthetic account {username} has a different role relationship; preserved.")
    return row["id"]


def _profile(cur, username: str) -> dict:
    row = _one(
        cur,
        """SELECT u.id,u.credits,u.academic_level,ra.program_id,p.code AS program_code
           FROM user_account u JOIN role_assignment ra ON ra.user_id=u.id AND ra.role='STUDENT'
           JOIN academic_program p ON p.id=ra.program_id WHERE u.username=%s""",
        (username,),
    )
    if row is None:
        raise RuntimeError(f"Required synthetic student {username} is not enrolled in one program.")
    return row


def _command(actor_id: int, fn: Callable, *args, **kwargs):
    with db.command(actor_id) as ctx:
        return fn(ctx, *args, **kwargs)


def _ensure_demo_eligibility_policy(
    cur,
    code: str,
    coordinator_id: int,
    *,
    enabled: bool,
    reason: str,
) -> None:
    if policies.latest_policy(cur, code, "ELIGIBILITY") is not None or not enabled:
        return
    # The values are an explicitly opted-in synthetic demonstration assumption,
    # not an institutional rule. Creation still goes through the policy service
    # as the coordinator scoped to this program and is audit-traced.
    conditions = [dict(condition, value=[code] if condition["type"] == "PROGRAM_IN" else condition["value"])
                  for condition in _DEMO_ELIGIBILITY_POLICY]
    _command(
        coordinator_id, policies.create_policy_version, code, conditions, "ELIGIBILITY",
        reason,
    )


def _ensure_opportunity(cur, *, title: str, host_org_id: int, program_id: int,
                        creator_id: int, target_state: str, reviewer_id: int) -> int:
    row = _one(
        cur,
        "SELECT id,host_org_id,program_id,state FROM opportunity WHERE title=%s ORDER BY id",
        (title,),
    )
    if row is None:
        opportunity_id = _command(
            creator_id, opportunities.create_opportunity, host_org_id, program_id, title,
        )
        state = "DRAFT"
    else:
        if row["host_org_id"] != host_org_id or row["program_id"] != program_id:
            raise RuntimeError(f"Synthetic opportunity {title!r} has different relationships; preserved.")
        opportunity_id, state = row["id"], row["state"]

    if target_state == "CLOSED":
        if state != "CLOSED":
            _command(creator_id, opportunities.close_opportunity, opportunity_id)
        return opportunity_id
    if target_state == "DRAFT" or state == "CLOSED":
        return opportunity_id
    if state == "DRAFT":
        _command(creator_id, opportunities.submit_for_review, opportunity_id)
        state = "IN_REVIEW"
    if target_state == "IN_REVIEW" or state not in {"IN_REVIEW", "APPROVED", "PUBLISHED"}:
        return opportunity_id
    settings = get_settings()
    if state == "IN_REVIEW" and settings.opportunity_reviewer_roles:
        _command(reviewer_id, opportunities.approve_for_publication, opportunity_id)
        state = "APPROVED"
    if target_state == "APPROVED" or state != "APPROVED":
        return opportunity_id
    if settings.opportunity_publisher_roles:
        _command(reviewer_id, opportunities.publish_opportunity, opportunity_id)
        return opportunity_id
    return opportunity_id


def _ensure_application(cur, student_id: int, opportunity_id: int) -> dict:
    row = _one(
        cur,
        "SELECT id,state,eligibility_result FROM application WHERE student_id=%s AND opportunity_id=%s ORDER BY id",
        (student_id, opportunity_id),
    )
    if row:
        return row
    with db.command(student_id) as ctx:
        result = applications.submit_application(ctx, opportunity_id)
    return {"id": result["application_id"], "state": result["state"],
            "eligibility_result": result["eligibility"]}


def _ensure_selection(cur, app_id: int, *, creator_id: int, supervisor_id: int,
                      opportunity_index: int, scenario_index: int) -> int:
    row = _one(cur, "SELECT id,state FROM placement WHERE application_id=%s", (app_id,))
    if row:
        return row["id"]
    app = _one(cur, "SELECT state FROM application WHERE id=%s", (app_id,))
    if app is None or app["state"] != "SUBMITTED":
        raise RuntimeError("A selected synthetic placement must originate from an eligible submitted application.")
    if scenario_index < 2:
        start, end = dt.date(2026, 1, 12), dt.date(2026, 5, 29)
    elif scenario_index >= 9:
        start, end = dt.date(2027, 2, 1), dt.date(2027, 6, 25)
    else:
        start, end = dt.date(2026, 9, 1), dt.date(2027, 1, 15)
    details = {
        "workplace_supervisor_id": supervisor_id,
        "start_date": start,
        "end_date": end,
        "location": f"Sede sintética {opportunity_index + 1:02d}",
        "responsibilities": "Actividades formativas ficticias para validar el ciclo de prácticas.",
    }
    return _command(creator_id, applications.select_application, app_id, details)


def _checklist_item(cur, placement_id: int):
    return _one(
        cur,
        "SELECT id,status,current_submission_id FROM checklist_item WHERE placement_id=%s AND kind='DOC_INSURANCE'",
        (placement_id,),
    )


def _submit_insurance(student_id: int, placement_id: int, item_id: int) -> None:
    _command(student_id, lifecycle.submit_document, placement_id, item_id,
             "synthetic-insurance.pdf", "application/pdf", _PDF)


def _ensure_document_state(cur, *, student_id: int, placement_id: int,
                           desired: str, legal_id: int) -> None:
    item = _checklist_item(cur, placement_id)
    if item is None:
        raise RuntimeError("The persisted activation policy did not materialize DOC_INSURANCE.")
    if desired == "MISSING":
        return
    if item["status"] == "REQUIRED":
        _submit_insurance(student_id, placement_id, item["id"])
        item = _checklist_item(cur, placement_id)
    if desired == "PENDING_REVIEW" and item["status"] == "SUBMITTED":
        return
    if desired == "CORRECTION_PENDING" and item["status"] == "SUBMITTED":
        versions = cur.execute(
            "SELECT count(*) AS n FROM document_submission WHERE checklist_item_id=%s", (item["id"],),
        ).fetchone()["n"]
        if versions >= 2:
            return
    if item["status"] == "SUBMITTED":
        decision = "REJECTED" if desired in {"REJECTED", "CORRECTION_PENDING"} else "APPROVED"
        _command(legal_id, lifecycle.review_document, placement_id, item["id"], decision,
                 "Revisión sintética de documento para validar historial de versiones.")
        item = _checklist_item(cur, placement_id)
    if desired == "CORRECTION_PENDING" and item["status"] == "REJECTED":
        _submit_insurance(student_id, placement_id, item["id"])
        return
    if desired == "APPROVED" and item["status"] == "REJECTED":
        _submit_insurance(student_id, placement_id, item["id"])
        item = _checklist_item(cur, placement_id)
        _command(legal_id, lifecycle.review_document, placement_id, item["id"], "APPROVED",
                 "Segunda versión sintética aprobada para completar el escenario.")


def _ensure_academic_decision(cur, placement_id: int, actor_id: int, target: str) -> None:
    placement = _one(cur, "SELECT state FROM placement WHERE id=%s", (placement_id,))
    if placement["state"] != "PENDING_ACADEMIC_APPROVAL":
        return
    if target == "REJECTED":
        _command(actor_id, lifecycle.academic_reject, placement_id,
                 "Selección sintética rechazada en el escenario de demostración.")
    elif target != "PENDING_ACADEMIC_APPROVAL":
        _command(actor_id, lifecycle.academic_approve, placement_id)


def _ensure_hours(cur, placement_id: int, student_id: int, amount: float) -> None:
    total = float(cur.execute(
        "SELECT coalesce(sum(hours),0) AS n FROM progress_entry WHERE placement_id=%s",
        (placement_id,),
    ).fetchone()["n"])
    if total < amount:
        _command(student_id, lifecycle.record_hours, placement_id, amount - total,
                 synthetic_demo=True)


def _ensure_work_plan(cur, placement_id: int, supervisor_id: int) -> None:
    plan = cur.execute(
        "SELECT 1 FROM placement_work_plan_item WHERE placement_id=%s LIMIT 1", (placement_id,),
    ).fetchone()
    if not plan:
        _command(supervisor_id, lifecycle.assign_work_plan_item, placement_id,
                 "Documentar un proceso de trabajo",
                 "Registrar observaciones y entregar una síntesis narrativa del proceso asignado.")


def _ensure_completion(cur, *, placement_id: int, student_id: int, supervisor_id: int,
                       coordinator_id: int, ec_id: int,
                       allow_demo_lifecycle_records: bool = False, close: bool) -> None:
    if not allow_demo_lifecycle_records:
        # Persistent loads default to no invented hours, evaluations, evidence, or
        # completion. The explicit demo opt-in writes labeled synthetic records
        # through the same domain services and checks persisted requirements.
        return
    placement = _one(cur, "SELECT state FROM placement WHERE id=%s", (placement_id,))
    if placement["state"] == "ACTIVE":
        _ensure_work_plan(cur, placement_id, supervisor_id)
        reports = cur.execute(
            "SELECT 1 FROM placement_progress_report WHERE placement_id=%s LIMIT 1", (placement_id,),
        ).fetchone()
        if not reports:
            _command(student_id, lifecycle.create_progress_report, placement_id,
                     "Avance sintético: se documentaron actividades realizadas y aprendizajes del periodo.")

    if allow_demo_lifecycle_records:
        final_evaluation = _one(
            cur,
            "SELECT id FROM placement_evaluation WHERE placement_id=%s AND kind='FINAL' ORDER BY id",
            (placement_id,),
        )
        if final_evaluation is None:
            _command(supervisor_id, lifecycle.create_evaluation, placement_id, "FINAL",
                     "Evaluación narrativa sintética del cierre de actividades y evidencias entregadas.")
        evidence = _one(
            cur,
            "SELECT id FROM completion_evidence WHERE placement_id=%s AND kind='FINAL_REPORT' ORDER BY id",
            (placement_id,),
        )
        requirement = cur.execute(
            "SELECT 1 FROM completion_requirement WHERE placement_id=%s AND kind='FINAL_REPORT'",
            (placement_id,),
        ).fetchone()
        if evidence is None and requirement is not None:
            _command(student_id, lifecycle.submit_completion_evidence, placement_id, "FINAL_REPORT",
                     "informe-final-sintetico.pdf", "application/pdf", _PDF,
                     synthetic_demo=True)
    threshold = cur.execute(
        "SELECT threshold FROM completion_requirement WHERE placement_id=%s AND kind='MIN_HOURS'",
        (placement_id,),
    ).fetchone()
    # Never synthesize an hour requirement. A demo may only record hours against
    # the persisted threshold already instantiated for this placement.
    if threshold and threshold["threshold"] is not None and allow_demo_lifecycle_records:
        _ensure_hours(cur, placement_id, student_id, float(threshold["threshold"]))
    placement = _one(cur, "SELECT state FROM placement WHERE id=%s", (placement_id,))
    if placement["state"] == "ACTIVE" and allow_demo_lifecycle_records:
        _command(coordinator_id, lifecycle.confirm_completion, placement_id)
        placement = {"state": "COMPLETED"}
    if close and placement["state"] == "COMPLETED":
        _command(ec_id, lifecycle.close_placement, placement_id)


def _ensure_message(cur, placement_id: int, actor_id: int, audience: str, text: str) -> None:
    existing = cur.execute(
        """SELECT 1 FROM placement_conversation pc JOIN placement_message pm
           ON pm.conversation_id=pc.id WHERE pc.placement_id=%s AND pc.audience=%s LIMIT 1""",
        (placement_id, audience),
    ).fetchone()
    if not existing:
        _command(actor_id, messaging.create_message, placement_id, audience, text)


def populate_synthetic_dataset(cur, *, include_demo_eligibility_policy: bool = False,
                               demo_eligibility_policy_reason: str | None = None,
                               password_hash_for: Callable[[str], str] | None = None,
                               allow_test_password: bool = False,
                               allow_demo_lifecycle_records: bool = False) -> dict:
    """Add/reuse 30 students, 10 organizations, 16 opportunities, 24 applications and 12 placements.

    Eligibility conditions are only added when callers explicitly opt into the
    synthetic demo policy. Persistent loaders must provide a unique credential
    hash for each newly created account; existing users are never re-hashed.
    """
    if password_hash_for is None:
        if not allow_test_password:
            raise RuntimeError("A per-account password provider is required outside isolated tests.")
        test_password_hash = security.hash_password(DEMO_PASSWORD)
        password_hash_for = lambda _username: test_password_hash

    programs = {code: _ensure_program(cur, code) for code in PROGRAMS}
    organizations = {name: _ensure_organization(cur, name) for name in ORGANIZATIONS}
    organization_ids = {
        "Org Alfa (synthetic)": _ensure_organization(cur, "Org Alfa (synthetic)"),
        "Org Beta (synthetic)": _ensure_organization(cur, "Org Beta (synthetic)"),
        **organizations,
    }

    students: dict[str, int] = {}
    for username, code, name, credits, level, courses in (
        ("s1", "ING-SIS", "Student One", 105, 7, ("MAT101",)),
        ("s2", "ING-SIS", "Student Two", 90, 5, ()),
        ("s3", "ADM", "Student Three", 120, 8, ()),
    ):
        row = _one(cur, "SELECT id FROM user_account WHERE username=%s", (username,))
        if row is None:
            raise RuntimeError(f"Base synthetic account {username} is missing; bootstrap it before this dataset.")
        students[username] = row["id"]

    for n in range(4, 31):
        index = n - 4
        code = "ING-SIS" if index < 14 else "ADM"
        credit_values = (78, 92, 100, 108, 118, 132)
        level_values = (4, 5, 6, 7, 8)
        credits = credit_values[index % len(credit_values)]
        level = level_values[(index * 2 + 1) % len(level_values)]
        username = f"demo_student_{n:02d}"
        students[username] = _ensure_account(
            cur, username=username, display_name=f"Estudiante Demo {n:02d}",
            role="STUDENT", program_id=programs[code], credits=credits, level=level,
            courses=("SYS-101",) if code == "ING-SIS" and index % 2 == 0
                    else (("ADM-101",) if code == "ADM" and index % 2 == 0 else ()),
            password_hash_for=password_hash_for,
        )

    host_members: dict[int, int] = {}
    workplace_supervisors: dict[int, int] = {}
    all_orgs = list(organization_ids.items())
    for org_index, (org_name, org_id) in enumerate(all_orgs):
        if org_name == "Org Alfa (synthetic)":
            host_members[org_id] = _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='HOST_ORG_MEMBER' AND host_org_id=%s", (org_id,))["id"]
            workplace_supervisors[org_id] = cur.execute(
                """SELECT ra.user_id AS id FROM role_assignment ra JOIN user_account u ON u.id=ra.user_id
                   WHERE ra.role='WORKPLACE_SUPERVISOR' AND ra.host_org_id=%s
                   ORDER BY (u.username='ws_alfa') DESC,u.username LIMIT 1""",
                (org_id,),
            ).fetchone()["id"]
            continue
        if org_name == "Org Beta (synthetic)":
            host_members[org_id] = _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='HOST_ORG_MEMBER' AND host_org_id=%s", (org_id,))["id"]
            workplace_supervisors[org_id] = _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='WORKPLACE_SUPERVISOR' AND host_org_id=%s ORDER BY user_id", (org_id,))["id"]
            continue
        suffix = org_index - 1
        host_members[org_id] = _ensure_account(
            cur, username=f"demo_host_{suffix:02d}", display_name=f"Representante Demo {suffix:02d}",
            role="HOST_ORG_MEMBER", host_org_id=org_id, password_hash_for=password_hash_for,
        )
        workplace_supervisors[org_id] = _ensure_account(
            cur, username=f"demo_supervisor_{suffix:02d}", display_name=f"Supervisor Laboral Demo {suffix:02d}",
            role="WORKPLACE_SUPERVISOR", host_org_id=org_id, password_hash_for=password_hash_for,
        )

    coordinators = {
        "ING-SIS": _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='PROGRAM_COORDINATOR' AND program_id=%s ORDER BY user_id LIMIT 1", (programs["ING-SIS"],))["id"],
        "ADM": _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='PROGRAM_COORDINATOR' AND program_id=%s ORDER BY user_id LIMIT 1", (programs["ADM"],))["id"],
    }
    ec_row = _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='EXPERIENTIAL_COORDINATOR' ORDER BY user_id LIMIT 1")
    legal_row = _one(cur, "SELECT user_id AS id FROM role_assignment WHERE role='LEGAL_REVIEWER' ORDER BY user_id LIMIT 1")
    if ec_row is None or legal_row is None:
        raise RuntimeError("Base synthetic EC and Legal accounts are required for the supported demo workflows.")
    ec_id, legal_id = ec_row["id"], legal_row["id"]

    faculty: list[int] = []
    existing_faculty = cur.execute(
        "SELECT user_id FROM role_assignment WHERE role='FACULTY_SUPERVISOR' ORDER BY user_id",
    ).fetchall()
    faculty.extend(row["user_id"] for row in existing_faculty)
    for n in range(2, 6):
        user_id = _ensure_account(
            cur, username=f"demo_faculty_{n:02d}", display_name=f"Supervisor Académico Demo {n:02d}",
            role="FACULTY_SUPERVISOR", password_hash_for=password_hash_for,
        )
        if user_id not in faculty:
            faculty.append(user_id)

    policy_reason = (demo_eligibility_policy_reason or
                     "Temporary synthetic eligibility policy for an isolated validation database.")
    for code, coordinator_id in coordinators.items():
        _ensure_demo_eligibility_policy(
            cur, code, coordinator_id,
            enabled=include_demo_eligibility_policy,
            reason=policy_reason,
        )

    opportunity_ids: list[int] = []
    main_opportunities: list[dict] = []
    all_opportunity_orgs = list(organization_ids.values())
    for index in range(16):
        code = "ING-SIS" if index % 2 == 0 else "ADM"
        org_id = all_opportunity_orgs[index % len(all_opportunity_orgs)]
        target = "PUBLISHED" if index < 12 else ("DRAFT", "IN_REVIEW", "APPROVED", "CLOSED")[index - 12]
        if index < len(PLACEMENT_SCENARIOS):
            scenario = PLACEMENT_SCENARIOS[index][0]
            title = f"Práctica sintética {index + 1:02d} · {scenario}"
        else:
            title = f"Oportunidad sintética {index + 1:02d} · {code}"
        opportunity_id = _ensure_opportunity(
            cur, title=title, host_org_id=org_id, program_id=programs[code],
            creator_id=host_members[org_id], target_state=target, reviewer_id=ec_id,
        )
        opportunity_ids.append(opportunity_id)
        if index < 12:
            main_opportunities.append({"id": opportunity_id, "title": title, "program_code": code,
                                      "host_org_id": org_id, "index": index})

    profiles = {name: _profile(cur, name) for name in students}
    eligible: dict[str, list[str]] = {code: [] for code in PROGRAMS}
    ineligible: dict[str, list[str]] = {code: [] for code in PROGRAMS}
    for username, profile in profiles.items():
        policy = policies.latest_policy(cur, profile["program_code"], "ELIGIBILITY")
        if policy is None:
            continue
        evaluated = policies.evaluate(profile, profile["program_code"], policy["conditions"])
        target = eligible if evaluated["result"] == "ELIGIBLE" else ineligible
        target[profile["program_code"]].append(username)
    for code in PROGRAMS:
        eligible[code].sort()
        ineligible[code].sort()
    if include_demo_eligibility_policy and sum(map(len, eligible.values())) < 12:
        raise RuntimeError("The disposable eligibility fixture must yield 12 selected students.")

    placement_ids: dict[str, int] = {}
    scenario_students: dict[str, str] = {}
    selected_pairs: set[tuple[str, int]] = set()
    used_students: set[str] = set()
    for index, scenario in enumerate(PLACEMENT_SCENARIOS):
        opportunity = main_opportunities[index]
        candidates = [name for name in eligible[opportunity["program_code"]] if name not in used_students]
        if not candidates:
            raise RuntimeError(f"Insufficient eligible fixture students for {opportunity['program_code']}.")
        student_username = candidates[0]
        used_students.add(student_username)
        student_id = students[student_username]
        app = _ensure_application(cur, student_id, opportunity["id"])
        if app["state"] == "INELIGIBLE":
            raise RuntimeError("Synthetic selected student was rejected by persisted eligibility conditions.")
        placement_id = _ensure_selection(
            cur, app["id"], creator_id=host_members[opportunity["host_org_id"]],
            supervisor_id=workplace_supervisors[opportunity["host_org_id"]],
            opportunity_index=index, scenario_index=index,
        )
        placement_ids[scenario[0]] = placement_id
        scenario_students[scenario[0]] = student_username
        selected_pairs.add((student_username, opportunity["id"]))

        target = scenario[1]
        _ensure_academic_decision(cur, placement_id, coordinators[opportunity["program_code"]], target)
        current = _one(cur, "SELECT state FROM placement WHERE id=%s", (placement_id,))["state"]
        if current in {"PENDING_ACADEMIC_APPROVAL", "REJECTED"}:
            continue

        document_target = {
            6: "MISSING", 7: "PENDING_REVIEW", 8: "CORRECTION_PENDING",
        }.get(index, "APPROVED")
        _ensure_document_state(cur, student_id=student_id, placement_id=placement_id,
                               desired=document_target, legal_id=legal_id)
        current = _one(cur, "SELECT state FROM placement WHERE id=%s", (placement_id,))["state"]
        if current == "DOCUMENTATION_PENDING" and document_target == "APPROVED":
            _command(ec_id, lifecycle.activate, placement_id)
            current = "ACTIVE"
        if current != "ACTIVE":
            continue

        _ensure_work_plan(cur, placement_id, workplace_supervisors[opportunity["host_org_id"]])
        if get_settings().faculty_assigner_roles and index % 2 == 0:
            assigned = cur.execute(
                "SELECT 1 FROM supervisor_assignment WHERE placement_id=%s AND kind='FACULTY' AND user_id=%s",
                (placement_id, faculty[index % len(faculty)]),
            ).fetchone()
            if not assigned:
                _command(coordinators[opportunity["program_code"]], lifecycle.assign_faculty_supervisor,
                         placement_id, faculty[index % len(faculty)])

        if index in {0, 1}:
            _ensure_completion(
                cur, placement_id=placement_id, student_id=student_id,
                supervisor_id=workplace_supervisors[opportunity["host_org_id"]],
                coordinator_id=coordinators[opportunity["program_code"]], ec_id=ec_id,
                allow_demo_lifecycle_records=allow_demo_lifecycle_records,
                close=index == 0,
            )
            # Scenario 1 stops after completion; scenario 0 is closed.
            if index in {0, 1}:
                continue
        elif index in {2, 3, 4} and allow_demo_lifecycle_records:
            _ensure_hours(cur, placement_id, student_id, 12.0 + index)
        elif index == 5 and allow_demo_lifecycle_records:
            _ensure_hours(cur, placement_id, student_id, 8.0)
            _ensure_message(cur, placement_id, student_id, "JOINT",
                            "Seguimiento sintético compartido sobre las actividades realizadas.")
        if index == 2 and not cur.execute(
                "SELECT 1 FROM placement_progress_report WHERE placement_id=%s LIMIT 1", (placement_id,)
        ).fetchone():
            _command(student_id, lifecycle.create_progress_report, placement_id,
                     "Avance sintético: se registran actividades realizadas y resultados observados.")
        if index == 3:
            for kind, summary in (("INCIDENT", "Consulta sobre acceso al espacio de trabajo"),
                                  ("CHANGE", "Ajuste de responsabilidades solicitado")):
                exists = cur.execute(
                    "SELECT 1 FROM placement_incident WHERE placement_id=%s AND kind=%s LIMIT 1",
                    (placement_id, kind),
                ).fetchone()
                if not exists:
                    _command(student_id, lifecycle.create_incident, placement_id, kind, summary,
                             "Registro factual sintético; requiere seguimiento entre las personas autorizadas.")
            if not cur.execute(
                    "SELECT 1 FROM placement_progress_report WHERE placement_id=%s LIMIT 1", (placement_id,)
            ).fetchone():
                _command(student_id, lifecycle.create_progress_report, placement_id,
                         "Avance sintético registrado junto con una consulta y un cambio reportados.")
        if index == 4:
            exists = cur.execute(
                "SELECT 1 FROM placement_evaluation WHERE placement_id=%s AND kind='MIDTERM' LIMIT 1",
                (placement_id,),
            ).fetchone()
            if not exists:
                _command(workplace_supervisors[opportunity["host_org_id"]], lifecycle.create_evaluation,
                         placement_id, "MIDTERM", "Comentario narrativo sintético de seguimiento intermedio.")
        if index == 5:
            exists = cur.execute(
                "SELECT 1 FROM placement_progress_report WHERE placement_id=%s LIMIT 1", (placement_id,),
            ).fetchone()
            if not exists:
                _command(student_id, lifecycle.create_progress_report, placement_id,
                         "Avance sintético pendiente de revisión; no se asocia a un vencimiento.")

    # Add twelve more applications, with persisted eligibility deciding their state.
    extra_pairs = 0
    for opportunity in main_opportunities:
        code = opportunity["program_code"]
        candidates = ineligible[code] + eligible[code]
        for username in candidates:
            pair = (username, opportunity["id"])
            if pair in selected_pairs:
                continue
            _ensure_application(cur, students[username], opportunity["id"])
            selected_pairs.add(pair)
            extra_pairs += 1
            if extra_pairs == 12:
                break
        if extra_pairs == 12:
            break
    if include_demo_eligibility_policy and extra_pairs != 12:
        raise RuntimeError("The disposable fixture could not create 24 unique synthetic applications.")

    counts = {}
    for table in ("user_account", "host_org", "opportunity", "application", "placement",
                  "document_submission", "placement_progress_report", "progress_entry",
                  "placement_work_plan_item", "placement_evaluation", "placement_incident",
                  "completion_evidence", "user_notification", "placement_message", "audit_event"):
        counts[table] = cur.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
    counts["placement_scenarios"] = placement_ids
    counts["scenario_students"] = scenario_students
    counts["organizations_created_or_reused"] = len(organization_ids)
    counts["opportunities_created_or_reused"] = len(opportunity_ids)
    return counts


def _partial_opportunity_title(index: int) -> str:
    code = "ING-SIS" if index % 2 == 0 else "ADM"
    if index < len(PLACEMENT_SCENARIOS):
        return f"Práctica sintética {index + 1:02d} · {PLACEMENT_SCENARIOS[index][0]}"
    return f"Oportunidad sintética {index + 1:02d} · {code}"


def _partial_account_specs(program_ids: dict[str, int], organization_ids: dict[str, int]):
    for n in range(4, 31):
        index = n - 4
        code = "ING-SIS" if index < 14 else "ADM"
        credit_values = (78, 92, 100, 108, 118, 132)
        level_values = (4, 5, 6, 7, 8)
        yield {
            "username": f"demo_student_{n:02d}",
            "display_name": f"Estudiante Demo {n:02d}",
            "role": "STUDENT", "program_id": program_ids[code], "host_org_id": None,
            "credits": credit_values[index % len(credit_values)],
            "level": level_values[(index * 2 + 1) % len(level_values)],
            "courses": ("SYS-101",) if code == "ING-SIS" and index % 2 == 0
                       else (("ADM-101",) if code == "ADM" and index % 2 == 0 else ()),
        }
    for org_index, org_name in enumerate(ORGANIZATIONS, start=1):
        org_id = organization_ids[org_name]
        yield {
            "username": f"demo_host_{org_index:02d}",
            "display_name": f"Representante Demo {org_index:02d}",
            "role": "HOST_ORG_MEMBER", "program_id": None, "host_org_id": org_id,
            "credits": None, "level": None, "courses": (),
        }
        yield {
            "username": f"demo_supervisor_{org_index:02d}",
            "display_name": f"Supervisor Laboral Demo {org_index:02d}",
            "role": "WORKPLACE_SUPERVISOR", "program_id": None, "host_org_id": org_id,
            "credits": None, "level": None, "courses": (),
        }
    for n in range(2, 6):
        yield {
            "username": f"demo_faculty_{n:02d}",
            "display_name": f"Supervisor Académico Demo {n:02d}",
            "role": "FACULTY_SUPERVISOR", "program_id": None, "host_org_id": None,
            "credits": None, "level": None, "courses": (),
        }


def populate_synthetic_partial(cur, *, password_hash_for: Callable[[str], str]) -> dict:
    """Create only synthetic organizations, accounts, relationships, and pending opportunities.

    This bootstrap path intentionally has no access to application, placement, or
    policy creation. Opportunity state changes still go through domain services.
    """
    if password_hash_for is None:
        raise RuntimeError("A unique per-account password provider is required for the partial dataset.")

    if cur.connection.info.transaction_status.name == "IDLE":
        raise RuntimeError("The partial dataset must run inside one caller-owned transaction.")
    tracked = ("host_org", "user_account", "role_assignment", "opportunity", "audit_event")
    inserted = {table: 0 for table in tracked}
    # Programs are existing institutional catalogs. The partial loader never creates or updates them.
    program_ids = {code: _require_program(cur, code) for code in PROGRAMS}
    organization_ids = {}
    for name in ALL_SYNTHETIC_ORGANIZATIONS:
        existing_orgs = cur.execute(
            "SELECT id FROM host_org WHERE name=%s ORDER BY id", (name,),
        ).fetchall()
        if len(existing_orgs) > 1:
            raise RuntimeError(f"Synthetic organization {name!r} is duplicated; preserved.")
        if existing_orgs:
            organization_ids[name] = existing_orgs[0]["id"]
        else:
            organization_ids[name] = _ensure_organization(cur, name)
            inserted["host_org"] += 1

    accounts: dict[str, int] = {}
    specs = list(_partial_account_specs(program_ids, organization_ids))
    for spec in specs:
        existing_account = _one(
            cur, "SELECT id FROM user_account WHERE username=%s", (spec["username"],),
        )
        user_id = _ensure_account(cur, password_hash_for=password_hash_for, **spec)
        if existing_account is None:
            inserted["user_account"] += 1
            inserted["role_assignment"] += 1
        assigned = cur.execute(
            "SELECT role,program_id,host_org_id FROM role_assignment WHERE user_id=%s ORDER BY role,program_id,host_org_id",
            (user_id,),
        ).fetchall()
        expected_assignment = {
            "role": spec["role"], "program_id": spec["program_id"], "host_org_id": spec["host_org_id"],
        }
        if assigned != [expected_assignment]:
            raise RuntimeError(f"Synthetic account {spec['username']} has unexpected role relations; preserved.")
        accounts[spec["username"]] = user_id

    # The two base host accounts belong to the pre-existing synthetic seed.
    base_hosts = {}
    for username, org_name in (("hm_alfa", BASE_ORGANIZATIONS[0]), ("hm_beta", BASE_ORGANIZATIONS[1])):
        row = _one(
            cur,
            """SELECT u.id FROM user_account u JOIN role_assignment r ON r.user_id=u.id
               WHERE u.username=%s AND r.role='HOST_ORG_MEMBER' AND r.host_org_id=%s""",
            (username, organization_ids[org_name]),
        )
        if row is None:
            raise RuntimeError(f"Required base organization relationship for {username} is missing; preserved.")
        base_hosts[organization_ids[org_name]] = row["id"]

    orgs_ordered = list(ALL_SYNTHETIC_ORGANIZATIONS)
    creators = {
        organization_ids[BASE_ORGANIZATIONS[0]]: base_hosts[organization_ids[BASE_ORGANIZATIONS[0]]],
        organization_ids[BASE_ORGANIZATIONS[1]]: base_hosts[organization_ids[BASE_ORGANIZATIONS[1]]],
    }
    for org_index, org_name in enumerate(ORGANIZATIONS, start=1):
        creators[organization_ids[org_name]] = accounts[f"demo_host_{org_index:02d}"]

    opportunity_ids: list[int] = []
    for index in range(16):
        code = "ING-SIS" if index % 2 == 0 else "ADM"
        org_id = organization_ids[orgs_ordered[index % len(orgs_ordered)]]
        creator_id = creators[org_id]
        title = _partial_opportunity_title(index)
        target = "IN_REVIEW" if index % 2 else "DRAFT"
        existing_rows = cur.execute(
            "SELECT id,host_org_id,program_id,state FROM opportunity WHERE title=%s ORDER BY id",
            (title,),
        ).fetchall()
        if len(existing_rows) > 1:
            raise RuntimeError(f"Synthetic opportunity {title!r} is duplicated; preserved.")
        existing = existing_rows[0] if existing_rows else None
        if existing:
            if (existing["host_org_id"], existing["program_id"]) != (org_id, program_ids[code]):
                raise RuntimeError(f"Synthetic opportunity {title!r} has different relations; preserved.")
            if existing["state"] not in {"DRAFT", "IN_REVIEW"}:
                raise RuntimeError(f"Synthetic opportunity {title!r} is outside pending states; preserved.")
            opportunity_id = existing["id"]
        else:
            opportunity_id = _command(
                creator_id, opportunities.create_opportunity, org_id, program_ids[code], title,
            )
            inserted["opportunity"] += 1
            inserted["audit_event"] += 1
        state = cur.execute("SELECT state FROM opportunity WHERE id=%s", (opportunity_id,)).fetchone()["state"]
        if target == "IN_REVIEW" and state == "DRAFT":
            _command(creator_id, opportunities.submit_for_review, opportunity_id)
            inserted["audit_event"] += 1
        opportunity_ids.append(opportunity_id)

    # This function has no application, placement, or policy write path. The
    # isolated database tests and read-only production preflight verify those
    # tables independently; the bootstrap role receives no access to them.
    final_states = cur.execute(
        "SELECT state,count(*) AS n FROM opportunity WHERE id=ANY(%s) GROUP BY state ORDER BY state",
        (opportunity_ids,),
    ).fetchall()
    if any(row["state"] not in {"DRAFT", "IN_REVIEW"} for row in final_states):
        raise RuntimeError("Partial opportunities must remain in DRAFT or IN_REVIEW.")

    totals = {table: cur.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
              for table in tracked}
    omitted = {
        "organizations_reused": len(ALL_SYNTHETIC_ORGANIZATIONS) - inserted["host_org"],
        "accounts_reused": len(specs) - inserted["user_account"],
        "role_relations_reused": len(specs) - inserted["role_assignment"],
        "opportunities_reused": len(opportunity_ids) - inserted["opportunity"],
        "applications_by_partial_scope": 24,
        "placements_by_partial_scope": 12,
        "published_opportunities_by_partial_scope": 12,
        "policy_writes": 0,
    }
    return {
        "mode": "partial", "totals": totals, "inserted": inserted, "omitted": omitted,
        "opportunity_states": {row["state"]: row["n"] for row in final_states},
        "synthetic_accounts_expected": len(specs), "synthetic_organizations_expected": 10,
        "synthetic_opportunities_expected": 16, "applications_created": 0,
        "placements_created": 0, "policies_created": 0,
        "notifications": "generated transactionally by domain audit rules; total is reported by read-only postflight",
    }
