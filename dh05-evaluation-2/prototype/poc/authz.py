"""Relationship-based authorization (ADR-004): role AND relationship to the resource.
External roles get NotFound (no existence disclosure); internal roles get Forbidden."""

EXTERNAL = {"HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR"}


class Forbidden(Exception):
    pass


class NotFound(Exception):
    pass


def subject(cur, user_id):
    return cur.execute("SELECT * FROM user_account WHERE id=%s", (user_id,)).fetchone()


def _ctx(cur, subj, pid):
    return cur.execute(
        """SELECT p.id, p.state, a.student_id, s.program_id AS student_program, o.host_org_id,
                  EXISTS (SELECT 1 FROM placement_version v WHERE v.placement_id = p.id
                          AND v.workplace_supervisor_id = %(u)s) AS is_workplace_sup,
                  EXISTS (SELECT 1 FROM supervisor_assignment sa WHERE sa.placement_id = p.id
                          AND sa.user_id = %(u)s AND sa.kind = 'FACULTY') AS is_faculty_sup
           FROM placement p JOIN application a ON a.id = p.application_id
           JOIN user_account s ON s.id = a.student_id
           JOIN opportunity o ON o.id = a.opportunity_id
           WHERE p.id = %(p)s""", {"u": subj["id"], "p": pid}).fetchone()


def can_read(cur, subj, pid):
    c = _ctx(cur, subj, pid)
    if c is None:
        return False
    r = subj["role"]
    if r == "STUDENT":
        return c["student_id"] == subj["id"]
    if r == "HOST_ORG_MEMBER":
        return c["host_org_id"] == subj["host_org_id"]
    if r == "WORKPLACE_SUPERVISOR":
        return c["host_org_id"] == subj["host_org_id"] and c["is_workplace_sup"]
    if r == "FACULTY_SUPERVISOR":
        return c["is_faculty_sup"]
    if r == "PROGRAM_COORDINATOR":
        return c["student_program"] == subj["program_id"]
    return r in ("EXPERIENTIAL_COORDINATOR", "LEGAL_REVIEWER")  # scope of these roles: OPEN


def _action_allowed(subj, c, action):
    r = subj["role"]
    own_program = r == "PROGRAM_COORDINATOR" and c["student_program"] == subj["program_id"]
    return {
        "placement:read": True,
        "placement:approve_academic": own_program,
        "version:approve": own_program,
        "placement:confirm_completion": own_program,
        "placement:activate": r == "EXPERIENTIAL_COORDINATOR",
        "placement:close": r == "EXPERIENTIAL_COORDINATOR",
        "document:review": r == "LEGAL_REVIEWER",
        "placement:propose_change": r == "EXPERIENTIAL_COORDINATOR"
                                    or (r == "WORKPLACE_SUPERVISOR" and c["is_workplace_sup"]),
        "progress:create": r == "STUDENT" and c["student_id"] == subj["id"],
        "evidence:submit": r == "STUDENT" and c["student_id"] == subj["id"],
    }[action]


def authorize(cur, subj, action, pid):
    if not can_read(cur, subj, pid):
        raise NotFound() if subj["role"] in EXTERNAL else Forbidden("no relationship")
    c = _ctx(cur, subj, pid)
    if not _action_allowed(subj, c, action):
        raise Forbidden(f"{subj['role']} may not {action}")


def visible_placement_ids(cur, subj):
    """Scoped query (no fetch-then-filter)."""
    r, u = subj["role"], subj["id"]
    base = """SELECT p.id FROM placement p JOIN application a ON a.id = p.application_id
              JOIN user_account s ON s.id = a.student_id JOIN opportunity o ON o.id = a.opportunity_id """
    where, params = {
        "STUDENT": ("WHERE a.student_id = %s", (u,)),
        "HOST_ORG_MEMBER": ("WHERE o.host_org_id = %s", (subj["host_org_id"],)),
        "WORKPLACE_SUPERVISOR": ("""WHERE o.host_org_id = %s AND EXISTS (SELECT 1 FROM placement_version v
              WHERE v.placement_id = p.id AND v.workplace_supervisor_id = %s)""", (subj["host_org_id"], u)),
        "FACULTY_SUPERVISOR": ("""WHERE EXISTS (SELECT 1 FROM supervisor_assignment sa
              WHERE sa.placement_id = p.id AND sa.user_id = %s AND sa.kind = 'FACULTY')""", (u,)),
        "PROGRAM_COORDINATOR": ("WHERE s.program_id = %s", (subj["program_id"],)),
        "EXPERIENTIAL_COORDINATOR": ("", ()),
        "LEGAL_REVIEWER": ("", ()),
    }[r]
    return sorted(x["id"] for x in cur.execute(base + where, params).fetchall())


def external_student_view(cur, student_id):
    """Minimal projection for external roles (BR-14): no credits, level, courses, other applications."""
    return cur.execute(
        """SELECT u.display_name, p.code AS program_code FROM user_account u
           JOIN academic_program p ON p.id = u.program_id WHERE u.id = %s""", (student_id,)).fetchone()
