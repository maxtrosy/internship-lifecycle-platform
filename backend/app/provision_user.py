"""Operator-only provisioning; credentials are entered interactively, never as CLI args.

Examples are documented in README.md. This command requires database-operator access and does
not create an application administrator or permit public self-assignment of a role.
"""
from __future__ import annotations

import argparse
import getpass
import uuid

from psycopg.types.json import Jsonb

from app import db, security
from app.modules.identity.service import validate_username

ROLES = {
    "STUDENT", "HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR", "FACULTY_SUPERVISOR",
    "PROGRAM_COORDINATOR", "EXPERIENTIAL_COORDINATOR", "LEGAL_REVIEWER",
}
PROGRAM_ROLES = {"STUDENT", "PROGRAM_COORDINATOR"}
ORG_ROLES = {"HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR"}


def _email(value: str) -> str:
    normalized = value.strip().casefold()
    if len(normalized) > 254 or "@" not in normalized or any(ch.isspace() for ch in normalized):
        raise ValueError("Provide a valid email address")
    return normalized


def _password() -> str:
    first = getpass.getpass("Password (12+ characters): ")
    second = getpass.getpass("Repeat password: ")
    if first != second:
        raise ValueError("Passwords did not match")
    return first


def _write_audit(cur, action: str, user_id: int, after: dict) -> None:
    cur.execute(
        """INSERT INTO audit_event(actor_id,action,subject_type,subject_id,after_state,correlation_id)
           VALUES (NULL,%s,'user_account',%s,%s,%s)""",
        (action, user_id, Jsonb(after), str(uuid.uuid4())),
    )


def provision(args: argparse.Namespace, password: str) -> int:
    username = validate_username(args.username)
    email = _email(args.email)
    name = args.display_name.strip()
    if not name:
        raise ValueError("Display name is required")
    password_hash = security.hash_password(password)

    with db.admin() as cur:
        if args.existing_user_id is not None:
            user = cur.execute(
                "SELECT id,is_active FROM user_account WHERE id=%s FOR UPDATE",
                (args.existing_user_id,),
            ).fetchone()
            if user is None:
                raise ValueError("Existing account was not found")
            if user["is_active"]:
                raise ValueError("Existing account is already active; use password recovery instead")
            cur.execute(
                """UPDATE user_account SET username=%s,email=%s,password_hash=%s,is_active=true,
                     display_name=%s WHERE id=%s""",
                (username, email, password_hash, name, user["id"]),
            )
            _write_audit(cur, "auth.account.provisioned", user["id"],
                         {"username": username, "legacy_roles_preserved": True})
            return user["id"]

        if args.role not in ROLES:
            raise ValueError("Unknown role")
        if args.role in PROGRAM_ROLES:
            if not args.program_code or args.host_org_id is not None:
                raise ValueError("Student and program coordinator accounts require only --program-code")
            program = cur.execute("SELECT id FROM academic_program WHERE code=%s", (args.program_code,)).fetchone()
            if program is None:
                raise ValueError("Program code was not found")
            program_id, host_org_id = program["id"], None
        elif args.role in ORG_ROLES:
            if args.host_org_id is None or args.program_code:
                raise ValueError("Host roles require only --host-org-id")
            org = cur.execute("SELECT id FROM host_org WHERE id=%s", (args.host_org_id,)).fetchone()
            if org is None:
                raise ValueError("Host organization was not found")
            program_id, host_org_id = None, org["id"]
        else:
            if args.program_code or args.host_org_id is not None:
                raise ValueError("This role does not accept a program or host organization")
            program_id, host_org_id = None, None

        user_id = cur.execute(
            """INSERT INTO user_account(username,email,password_hash,is_active,display_name)
               VALUES (%s,%s,%s,true,%s) RETURNING id""",
            (username, email, password_hash, name),
        ).fetchone()["id"]
        cur.execute(
            "INSERT INTO role_assignment(user_id,role,program_id,host_org_id) VALUES (%s,%s,%s,%s)",
            (user_id, args.role, program_id, host_org_id),
        )
        _write_audit(cur, "auth.account.provisioned", user_id,
                     {"username": username, "role": args.role,
                      "program_id": program_id, "host_org_id": host_org_id})
        return user_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a local account using database operator access")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", choices=sorted(ROLES))
    parser.add_argument("--program-code")
    parser.add_argument("--host-org-id", type=int)
    parser.add_argument("--existing-user-id", type=int,
                        help="Assign credentials to a migrated legacy account without changing its roles")
    args = parser.parse_args()
    if args.existing_user_id is None and args.role is None:
        parser.error("--role is required when creating a new account")
    if args.existing_user_id is not None and any((args.role, args.program_code, args.host_org_id is not None)):
        parser.error("--existing-user-id preserves roles; do not pass a new role or relationship")
    user_id = provision(args, _password())
    print(f"Account provisioned: user_id={user_id}; existing role relationships preserved where applicable.")


if __name__ == "__main__":
    main()
