"""Safely inspect or persist the connected synthetic workflow fixture in Neon.

The default is a read-only preflight. The apply path has separate gates for the
Neon target, a recent Neon branch snapshot, institutional policies/authorities,
and a one-time writer credential. It never reads ``DATABASE_URL`` or ``.env``.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import json
import os
import secrets
import shutil
import subprocess
import sys
import traceback
from ctypes import wintypes
from pathlib import Path
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app import db, security  # noqa: E402
from app.synthetic_dataset import ORGANIZATIONS, PLACEMENT_SCENARIOS, PROGRAMS, populate_synthetic_dataset  # noqa: E402

PROJECT_ID = "long-truth-39527618"
BRANCH_ID = "br-green-wind-bc6cvzzc"
BRANCH_NAME = "main"
DATABASE_NAME = "neondb"
DIRECT_HOST = "ep-wispy-base-bc3ecq8o.c-16.us-east-1.aws.neon.tech"
RUNTIME_CREDENTIAL = "InternshipLifecyclePlatform/Neon/main/app_runtime/DATABASE_URL"
WRITER_CREDENTIAL = "InternshipLifecyclePlatform/Neon/main/synthetic_loader/DATABASE_URL"
PASSWORD_TARGET_PREFIX = "InternshipLifecyclePlatform/SyntheticDataset/long-truth-39527618/main"
EXPECTED_USERS = {
    *(f"demo_student_{n:02d}" for n in range(4, 31)),
    *(f"demo_host_{n:02d}" for n in range(1, 9)),
    *(f"demo_supervisor_{n:02d}" for n in range(1, 9)),
    *(f"demo_faculty_{n:02d}" for n in range(2, 6)),
}
APPLICATION_TABLES = (
    "academic_program", "host_org", "user_account", "role_assignment", "policy_version",
    "opportunity", "application", "placement", "placement_version", "checklist_item",
    "document_submission", "document_review", "progress_entry", "placement_work_plan_item",
    "placement_progress_report", "placement_evaluation", "placement_incident", "completion_evidence",
    "user_notification", "placement_conversation", "placement_message", "audit_event",
)


class _FileTime(ctypes.Structure):
    _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]


class _CredentialAttributeW(ctypes.Structure):
    _fields_ = [
        ("Keyword", wintypes.LPWSTR), ("Flags", wintypes.DWORD),
        ("ValueSize", wintypes.DWORD), ("Value", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class _CredentialW(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD), ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
        ("LastWritten", _FileTime), ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
        ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.POINTER(_CredentialAttributeW)),
        ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR),
    ]


class WindowsCredentialStore:
    """Small generic-credential adapter; values never enter stdout or files."""

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2
    ERROR_NOT_FOUND = 1168

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Windows Credential Manager is required for this loader.")
        self._api = ctypes.WinDLL("Advapi32.dll", use_last_error=True)
        self._api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                        ctypes.POINTER(ctypes.POINTER(_CredentialW))]
        self._api.CredReadW.restype = wintypes.BOOL
        self._api.CredWriteW.argtypes = [ctypes.POINTER(_CredentialW), wintypes.DWORD]
        self._api.CredWriteW.restype = wintypes.BOOL
        self._api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        self._api.CredDeleteW.restype = wintypes.BOOL
        self._api.CredFree.argtypes = [ctypes.c_void_p]
        self._api.CredFree.restype = None

    def read(self, target: str) -> str | None:
        credential = ctypes.POINTER(_CredentialW)()
        if not self._api.CredReadW(target, self.CRED_TYPE_GENERIC, 0, ctypes.byref(credential)):
            if ctypes.get_last_error() == self.ERROR_NOT_FOUND:
                return None
            raise RuntimeError("Windows Credential Manager could not read a required credential.")
        try:
            blob = ctypes.string_at(credential.contents.CredentialBlob,
                                    credential.contents.CredentialBlobSize)
            value = blob.decode("utf-8")
            return value or None
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeError("A stored credential has an unsupported encoding.") from exc
        finally:
            self._api.CredFree(credential)

    def write(self, target: str, value: str, *, username: str, comment: str) -> None:
        blob = value.encode("utf-8")
        blob_buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        credential = _CredentialW(
            Flags=0, Type=self.CRED_TYPE_GENERIC, TargetName=target, Comment=comment,
            LastWritten=_FileTime(), CredentialBlobSize=len(blob),
            CredentialBlob=ctypes.cast(blob_buffer, ctypes.POINTER(ctypes.c_ubyte)),
            Persist=self.CRED_PERSIST_LOCAL_MACHINE, AttributeCount=0, Attributes=None,
            TargetAlias=None, UserName=username,
        )
        if not self._api.CredWriteW(ctypes.byref(credential), 0):
            raise RuntimeError("Windows Credential Manager could not store a generated credential.")

    def delete(self, target: str) -> None:
        if not self._api.CredDeleteW(target, self.CRED_TYPE_GENERIC, 0):
            if ctypes.get_last_error() != self.ERROR_NOT_FOUND:
                raise RuntimeError("Windows Credential Manager could not clean up a generated credential.")


class UniquePasswordHashes:
    def __init__(self, store: WindowsCredentialStore) -> None:
        self.store = store
        self.created_targets: list[str] = []

    def __call__(self, username: str) -> str:
        target = f"{PASSWORD_TARGET_PREFIX}/{username}/PASSWORD"
        password = self.store.read(target)
        if password is None:
            password = secrets.token_urlsafe(32)
            self.store.write(
                target, password, username=username,
                comment="Unique synthetic account credential; dataset loader.",
            )
            self.created_targets.append(target)
        return security.hash_password(password)

    def cleanup_new_credentials(self) -> None:
        for target in reversed(self.created_targets):
            self.store.delete(target)
        self.created_targets.clear()


def _credential_url(store: WindowsCredentialStore, target: str) -> str:
    value = store.read(target)
    if value is None:
        raise RuntimeError(f"Required Windows Credential Manager item is missing: {target}")
    return value


def _connection_details(url: str, *, require_direct: bool = False,
                        expected_user: str | None = None) -> dict[str, str]:
    try:
        details = conninfo_to_dict(url)
    except Exception as exc:
        raise RuntimeError("The stored database connection could not be parsed.") from exc
    host = (details.get("host") or "").lower().rstrip(".")
    host_unpooled = host.replace("-pooler.c-", ".c-")
    if host_unpooled != DIRECT_HOST or (require_direct and host != DIRECT_HOST):
        raise RuntimeError("The database endpoint is not the verified Neon main endpoint.")
    if details.get("dbname") != DATABASE_NAME:
        raise RuntimeError("The database name does not match the verified Neon database.")
    if details.get("sslmode", "").lower() not in {"require", "verify-ca", "verify-full"}:
        raise RuntimeError("The Neon connection must require TLS.")
    if expected_user and details.get("user") != expected_user:
        raise RuntimeError("The stored database credential has an unexpected database role.")
    return details


def _neon_branches() -> list[dict[str, Any]]:
    try:
        neon_cli = shutil.which("neon.cmd") or shutil.which("neon")
        if not neon_cli:
            raise RuntimeError("Neon CLI is not installed in this process environment.")
        command = [neon_cli, "branches", "list", "--project-id", PROJECT_ID, "--output", "json"]
        if neon_cli.lower().endswith((".cmd", ".bat")):
            command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", *command]
        result = subprocess.run(
            command,
            check=True, capture_output=True, text=True, timeout=30,
        )
        branches = json.loads(result.stdout)
    except Exception as exc:
        raise RuntimeError("Neon CLI could not verify project branches; no database write was attempted.") from exc
    if not isinstance(branches, list):
        raise RuntimeError("Neon CLI returned an unexpected branch inventory.")
    return branches


def _verify_target_branch(branches: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [branch for branch in branches
               if branch.get("project_id") == PROJECT_ID and branch.get("id") == BRANCH_ID
               and branch.get("name") == BRANCH_NAME]
    if len(matches) != 1 or matches[0].get("current_state") != "ready":
        raise RuntimeError("Neon project/branch identity did not match the authorized target.")
    return matches[0]


def _verify_recent_backup(branches: list[dict[str, Any]], backup_branch_id: str) -> dict[str, Any]:
    matches = [branch for branch in branches
               if branch.get("project_id") == PROJECT_ID and branch.get("id") == backup_branch_id]
    if len(matches) != 1:
        raise RuntimeError("The supplied backup branch is not present in the authorized Neon project.")
    backup = matches[0]
    if backup.get("id") == BRANCH_ID or backup.get("parent_id") != BRANCH_ID:
        raise RuntimeError("The backup branch must be a separate child of authorized Neon main.")
    created = backup.get("created_at")
    try:
        created_at = dt.datetime.fromisoformat(str(created).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Neon did not report a verifiable backup timestamp.") from exc
    age = dt.datetime.now(dt.timezone.utc) - created_at if created_at.tzinfo else dt.timedelta.max
    if created_at.tzinfo is None or age < dt.timedelta(0) or age > dt.timedelta(hours=24):
        raise RuntimeError("A Neon snapshot branch created within the last 24 hours is required.")
    return backup


def _expected_titles() -> set[str]:
    titles: set[str] = set()
    for index in range(16):
        code = "ING-SIS" if index % 2 == 0 else "ADM"
        if index < len(PLACEMENT_SCENARIOS):
            scenario = PLACEMENT_SCENARIOS[index][0]
            titles.add(f"Práctica sintética {index + 1:02d} · {scenario}")
        else:
            titles.add(f"Oportunidad sintética {index + 1:02d} · {code}")
    return titles


def _counts(cur) -> dict[str, int]:
    return {table: cur.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
            for table in APPLICATION_TABLES}


def _inspect_database(url: str, *, set_application_role: bool) -> dict[str, Any]:
    details = _connection_details(
        url, require_direct=not set_application_role,
        expected_user="app_runtime" if set_application_role else "neondb_owner",
    )
    report: dict[str, Any] = {
        "target": {"project": PROJECT_ID, "branch": BRANCH_NAME, "branch_id": BRANCH_ID,
                   "database": DATABASE_NAME},
        "fixture_target": {"new_accounts_max": len(EXPECTED_USERS), "organizations": len(ORGANIZATIONS),
                           "opportunities": 16, "applications": 24, "placements": 12,
                           "reuse_policy": "natural keys; existing unrelated rows preserved"},
        "connection_role": details.get("user"),
        "tls": False,
        "migration": None,
        "counts": {},
        "collisions": {},
        "eligibility_policies": [],
        "authority_variables_configured": {},
        "writer_capabilities": {},
        "blockers": [],
    }
    try:
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10,
                             application_name="synthetic_dataset_preflight") as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                if set_application_role:
                    conn.execute("SET ROLE app_user")
                identity = conn.execute(
                    "SELECT session_user AS login_role, current_user AS active_role, current_database() AS database"
                ).fetchone()
                if identity["database"] != DATABASE_NAME:
                    raise RuntimeError("Connected database does not match the authorized target.")
                if set_application_role and (identity["login_role"] != "app_runtime"
                                             or identity["active_role"] != "app_user"):
                    raise RuntimeError("Runtime login did not assume app_user as expected.")
                report["tls"] = bool(conn.pgconn.ssl_in_use)
                if not report["tls"]:
                    raise RuntimeError("Neon connection did not negotiate TLS.")
                if set_application_role:
                    report["migration"] = "not-readable-by-runtime"
                else:
                    version = conn.execute("SELECT version_num FROM alembic_version").fetchone()["version_num"]
                    report["migration"] = version
                    if version != "0013":
                        report["blockers"].append("The target schema must already be at migration 0013.")
                report["counts"] = _counts(conn.cursor())
                demo_users = conn.execute(
                    "SELECT username FROM user_account WHERE username LIKE %s ESCAPE '!' ORDER BY username",
                    ("demo!_%",),
                ).fetchall()
                demo_names = {row["username"] for row in demo_users}
                report["collisions"]["unexpected_demo_accounts"] = len(demo_names - EXPECTED_USERS)
                report["collisions"]["expected_accounts_already_present"] = len(demo_names & EXPECTED_USERS)
                if demo_names - EXPECTED_USERS:
                    report["blockers"].append("Unexpected demo_ usernames already exist; they will be preserved.")
                expected_orgs = list(ORGANIZATIONS)
                org_names = conn.execute(
                    "SELECT name,count(*) AS n FROM host_org WHERE name=ANY(%s) GROUP BY name",
                    (expected_orgs,),
                ).fetchall()
                if any(row["n"] != 1 for row in org_names):
                    report["blockers"].append("Expected synthetic organization names are duplicated.")
                report["collisions"]["expected_organizations_already_present"] = sum(
                    row["n"] for row in org_names
                )
                expected_titles = _expected_titles()
                opportunities = conn.execute(
                    "SELECT title,count(*) AS n FROM opportunity WHERE title LIKE 'Práctica sintética %' "
                    "OR title LIKE 'Oportunidad sintética %' GROUP BY title"
                ).fetchall()
                title_names = {row["title"] for row in opportunities}
                report["collisions"]["unexpected_synthetic_opportunities"] = len(title_names - expected_titles)
                report["collisions"]["expected_opportunities_already_present"] = sum(
                    row["n"] for row in opportunities if row["title"] in expected_titles
                )
                if title_names - expected_titles or any(row["n"] > 1 for row in opportunities):
                    report["blockers"].append("Synthetic opportunity names collide or are duplicated.")
                policies = conn.execute(
                    "SELECT policy_key FROM policy_version WHERE policy_key IN "
                    "('ELIGIBILITY:ING-SIS','ELIGIBILITY:ADM') GROUP BY policy_key ORDER BY policy_key"
                ).fetchall()
                report["eligibility_policies"] = [row["policy_key"] for row in policies]
                if len(report["eligibility_policies"]) != len(PROGRAMS):
                    report["blockers"].append(
                        "A persisted eligibility policy is missing for at least one program; test policies are forbidden."
                    )
                for key in ("OPPORTUNITY_REVIEWER_ROLES", "OPPORTUNITY_PUBLISHER_ROLES",
                            "PLACEMENT_FACULTY_ASSIGNER_ROLES"):
                    report["authority_variables_configured"][key] = bool(os.environ.get(key, "").strip())
                    if not report["authority_variables_configured"][key]:
                        report["blockers"].append(f"Institutional authority {key} is not configured for this loader.")
                report["writer_capabilities"] = {
                    "host_org_insert_as_active_role": bool(conn.execute(
                        "SELECT has_table_privilege(current_user,'public.host_org','INSERT') AS allowed"
                    ).fetchone()["allowed"]),
                }
                # The T-49 role deliberately cannot read the migration ledger.
                # The app_user grant path checks a schema marker instead.
                if set_application_role:
                    marker = conn.execute(
                        "SELECT to_regclass('public.placement_faculty_assignment_history') IS NOT NULL AS present"
                    ).fetchone()["present"]
                    report["schema_marker_present"] = bool(marker)
                    if not marker:
                        report["blockers"].append("The required application schema marker is missing.")
                else:
                    privileges = conn.execute(
                        "SELECT has_table_privilege(session_user,'public.host_org','INSERT') AS host_insert, "
                        "has_table_privilege(session_user,'public.user_account','INSERT') AS user_insert, "
                        "has_sequence_privilege(session_user,'public.host_org_id_seq','USAGE') AS org_sequence"
                    ).fetchone()
                    report["writer_capabilities"] = {
                        "host_org_insert": bool(privileges["host_insert"]),
                        "user_account_insert": bool(privileges["user_insert"]),
                        "host_org_sequence_usage": bool(privileges["org_sequence"]),
                    }
                    if not all(report["writer_capabilities"].values()):
                        report["blockers"].append("The one-time writer login lacks required bootstrap privileges.")
                    report["integrity"] = _table_integrity(conn.cursor())
    except Exception as exc:
        # Driver exception strings can include connection metadata; withhold them.
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        location = f"{Path(frame.filename).name}:{frame.lineno} ({frame.name})"
        raise RuntimeError(
            f"Read-only Neon preflight failed ({type(exc).__name__} at {location}); details withheld."
        ) from exc
    return report


def _snapshot_summary(branches: list[dict[str, Any]]) -> dict[str, Any]:
    return {"branch_count": len(branches),
            "recent_snapshot_available": any(
                branch.get("project_id") == PROJECT_ID and branch.get("id") != BRANCH_ID
                and branch.get("parent_id") == BRANCH_ID for branch in branches
            )}


def _print_report(report: dict[str, Any]) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def _assert_no_blockers(report: dict[str, Any]) -> None:
    blockers = report.get("blockers", [])
    if blockers:
        raise RuntimeError("Preflight blocked the write: " + " | ".join(blockers))


def _table_integrity(cur) -> dict[str, int]:
    checks = {
        "applications_without_program_student": """SELECT count(*) AS n FROM application a
            LEFT JOIN opportunity o ON o.id=a.opportunity_id
            LEFT JOIN role_assignment r ON r.user_id=a.student_id AND r.role='STUDENT' AND r.program_id=o.program_id
            WHERE o.id IS NULL OR r.user_id IS NULL""",
        "placements_without_application": """SELECT count(*) AS n FROM placement p
            LEFT JOIN application a ON a.id=p.application_id WHERE a.id IS NULL""",
        "documents_without_checklist": """SELECT count(*) AS n FROM document_submission d
            LEFT JOIN checklist_item c ON c.id=d.checklist_item_id WHERE c.id IS NULL""",
        "unvalidated_constraints": "SELECT count(*) AS n FROM pg_constraint WHERE connamespace='public'::regnamespace AND NOT convalidated",
    }
    return {name: cur.execute(sql).fetchone()["n"] for name, sql in checks.items()}


def _active_transaction_load(url: str, store: WindowsCredentialStore,
                            commit_state: dict[str, bool]) -> dict[str, Any]:
    _connection_details(url, require_direct=True, expected_user="neondb_owner")
    password_hash_for = UniquePasswordHashes(store)
    try:
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10,
                             application_name="synthetic_dataset_loader", autocommit=True) as conn:
            commit_state["transaction_started"] = True
            with conn.transaction():
                state = conn.execute(
                    "SELECT session_user AS login_role,current_database() AS database "
                    "FROM pg_catalog.pg_roles WHERE rolname=session_user"
                ).fetchone()
                if state["login_role"] != "neondb_owner" or state["database"] != DATABASE_NAME:
                    raise RuntimeError("The one-time writer identity does not match the approved target.")
                version = conn.execute("SELECT version_num FROM alembic_version").fetchone()["version_num"]
                if version != "0013":
                    raise RuntimeError("Migration head is not 0013; no data was changed.")
                before_counts = _counts(conn.cursor())
                original_acl = conn.execute(
                    "SELECT has_table_privilege('app_user','public.host_org','INSERT') AS table_insert, "
                    "has_sequence_privilege('app_user','public.host_org_id_seq','USAGE') AS sequence_usage, "
                    "(SELECT set_option FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid "
                    "JOIN pg_roles u ON u.oid=m.member WHERE g.rolname='app_user' AND u.rolname='neondb_owner') AS set_option, "
                    "(SELECT inherit_option FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid "
                    "JOIN pg_roles u ON u.oid=m.member WHERE g.rolname='app_user' AND u.rolname='neondb_owner') AS inherit_option, "
                    "(SELECT admin_option FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid "
                    "JOIN pg_roles u ON u.oid=m.member WHERE g.rolname='app_user' AND u.rolname='neondb_owner') AS admin_option"
                ).fetchone()
                if (original_acl["table_insert"] or original_acl["sequence_usage"]
                        or original_acl["set_option"] is not False
                        or original_acl["inherit_option"] is not False
                        or original_acl["admin_option"] is not True):
                    raise RuntimeError("The verified pre-load ACL baseline changed; no data was written.")

                # The owner can temporarily grant only the catalog insert path to
                # app_user inside this transaction. The original ACL/membership
                # is restored before commit; rollback restores it automatically.
                conn.execute("GRANT INSERT ON host_org TO app_user")
                conn.execute("GRANT USAGE ON SEQUENCE host_org_id_seq TO app_user")
                conn.execute(
                    "GRANT app_user TO neondb_owner WITH ADMIN TRUE, INHERIT FALSE, SET TRUE"
                )
                conn.execute("SET LOCAL ROLE app_user")

                existing_orgs = conn.execute(
                    "SELECT name FROM host_org WHERE name=ANY(%s)", (list(ORGANIZATIONS),)
                ).fetchall()
                existing_names = {row["name"] for row in existing_orgs}
                for name in ORGANIZATIONS:
                    if name not in existing_names:
                        conn.execute("INSERT INTO host_org(name) VALUES (%s)", (name,))

                with db.shared_command_connection(conn, required_role="app_user"):
                    first = populate_synthetic_dataset(
                        conn.cursor(), include_test_policy=False,
                        password_hash_for=password_hash_for,
                    )
                    second = populate_synthetic_dataset(
                        conn.cursor(), include_test_policy=False,
                        password_hash_for=password_hash_for,
                    )
                    if first != second:
                        raise RuntimeError("The second in-transaction load was not idempotent.")
                    integrity = _table_integrity(conn.cursor())
                    if any(integrity.values()):
                        raise RuntimeError("Relationship or constraint verification failed; transaction rolled back.")
                    final_counts = _counts(conn.cursor())
                    inserted_counts = {
                        table: final_counts[table] - before_counts[table]
                        for table in APPLICATION_TABLES
                    }

                conn.execute("RESET ROLE")
                conn.execute("REVOKE INSERT ON host_org FROM app_user")
                conn.execute("REVOKE USAGE ON SEQUENCE host_org_id_seq FROM app_user")
                conn.execute(
                    "GRANT app_user TO neondb_owner WITH ADMIN TRUE, INHERIT FALSE, SET FALSE"
                )
                acl_restored = conn.execute(
                    "SELECT NOT has_table_privilege('app_user','public.host_org','INSERT') AS table_ok, "
                    "NOT has_sequence_privilege('app_user','public.host_org_id_seq','USAGE') AS sequence_ok, "
                    "(SELECT set_option FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid "
                    "JOIN pg_roles u ON u.oid=m.member WHERE g.rolname='app_user' AND u.rolname='neondb_owner') AS set_option, "
                    "(SELECT inherit_option FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid "
                    "JOIN pg_roles u ON u.oid=m.member WHERE g.rolname='app_user' AND u.rolname='neondb_owner') AS inherit_option, "
                    "(SELECT admin_option FROM pg_auth_members m JOIN pg_roles g ON g.oid=m.roleid "
                    "JOIN pg_roles u ON u.oid=m.member WHERE g.rolname='app_user' AND u.rolname='neondb_owner') AS admin_option"
                ).fetchone()
                if (not acl_restored["table_ok"] or not acl_restored["sequence_ok"]
                        or acl_restored["set_option"] is not False
                        or acl_restored["inherit_option"] is not False
                        or acl_restored["admin_option"] is not True):
                    raise RuntimeError("Temporary writer permissions were not restored; transaction rolled back.")
            commit_state["committed"] = True
        password_hash_for.created_targets.clear()
    except Exception:
        if not commit_state["committed"]:
            password_hash_for.cleanup_new_credentials()
        raise

    # Verify the committed rows independently using a fresh TLS connection.
    verification = _inspect_database(url, set_application_role=False)
    verification["post_commit_integrity"] = verification.pop("integrity")
    verification["idempotent_in_same_transaction"] = first == second
    verification["loaded_totals"] = final_counts
    verification["inserted_counts"] = inserted_counts
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only preflight or guarded Neon synthetic dataset load.")
    parser.add_argument("--apply", action="store_true", help="Apply only after every preflight gate passes.")
    parser.add_argument("--confirm-target", help="Must equal long-truth-39527618/main for --apply.")
    parser.add_argument("--backup-branch-id", help="Recent Neon child snapshot branch id for --apply.")
    args = parser.parse_args()

    write_attempted = False
    commit_state = {"transaction_started": False, "committed": False}
    try:
        store = WindowsCredentialStore()
        branches = _neon_branches()
        _verify_target_branch(branches)
        if not args.apply:
            runtime_url = _credential_url(store, RUNTIME_CREDENTIAL)
            report = _inspect_database(runtime_url, set_application_role=True)
            report["backup"] = _snapshot_summary(branches)
            report["write_performed"] = False
            writer_url = store.read(WRITER_CREDENTIAL)
            report["one_time_writer_credential_available"] = writer_url is not None
            if writer_url:
                writer_report = _inspect_database(writer_url, set_application_role=False)
                report["writer_capabilities"] = writer_report["writer_capabilities"]
                report["blockers"].extend(writer_report["blockers"])
            elif "A one-time writer credential is absent; app_runtime is intentionally not elevated." \
                    not in report["blockers"]:
                report["blockers"].append(
                    "A one-time writer credential is absent; app_runtime is intentionally not elevated."
                )
            _print_report(report)
            return 0 if not report["blockers"] else 2

        if args.confirm_target != f"{PROJECT_ID}/{BRANCH_NAME}":
            raise RuntimeError("Apply requires --confirm-target long-truth-39527618/main.")
        if not args.backup_branch_id:
            raise RuntimeError("Apply requires a Neon snapshot branch created within the last 24 hours.")
        backup = _verify_recent_backup(branches, args.backup_branch_id)
        writer_url = _credential_url(store, WRITER_CREDENTIAL)
        report = _inspect_database(writer_url, set_application_role=False)
        report["backup"] = {"verified": True, "branch_id": backup["id"],
                            "created_at": backup.get("created_at")}
        report["write_performed"] = False
        _print_report(report)
        _assert_no_blockers(report)
        expected_phrase = f"PERSIST SYN-01 TO {PROJECT_ID}/{BRANCH_NAME}"
        if input(f"Type {expected_phrase} to continue: ").strip() != expected_phrase:
            print("Cancelled; no database write was performed.")
            return 3
        write_attempted = True
        result = _active_transaction_load(writer_url, store, commit_state)
        result["backup"] = {"verified": True, "branch_id": backup["id"],
                            "created_at": backup.get("created_at")}
        result["write_performed"] = True
        _print_report(result)
        return 0
    except Exception as exc:
        error = str(exc) if type(exc) is RuntimeError else f"{type(exc).__name__}; details withheld."
        status = "committed_unverified" if commit_state["committed"] else (
            "rolled_back" if commit_state["transaction_started"] else "blocked"
        )
        print(json.dumps({
            "status": status, "error": error, "write_attempted": write_attempted,
            "database_transaction_started": commit_state["transaction_started"],
            "database_rows_committed": commit_state["committed"],
            "possible_sequence_gaps": commit_state["transaction_started"] and not commit_state["committed"],
        },
                         ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
