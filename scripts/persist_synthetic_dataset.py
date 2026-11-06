"""Safely inspect or persist the connected synthetic workflow fixture in Neon.

The default is a read-only preflight. Apply uses a dedicated least-privilege
bootstrap login per mode, with separate gates for the Neon target, a recent
child-branch snapshot, persisted policies, and configured authorities. It never
reads ``DATABASE_URL`` or ``.env``.
"""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
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
from app.synthetic_dataset import (  # noqa: E402
    ALL_SYNTHETIC_ORGANIZATIONS, PROGRAMS,
    _partial_account_specs, _partial_opportunity_title,
    populate_synthetic_dataset, populate_synthetic_partial,
)

PROJECT_ID = "long-truth-39527618"
BRANCH_ID = "br-green-wind-bc6cvzzc"
BRANCH_NAME = "main"
DATABASE_NAME = "neondb"
DIRECT_HOST = "ep-wispy-base-bc3ecq8o.c-16.us-east-1.aws.neon.tech"
RUNTIME_CREDENTIAL = "InternshipLifecyclePlatform/Neon/main/app_runtime/DATABASE_URL"
BOOTSTRAP_CREDENTIAL = "InternshipLifecyclePlatform/Neon/main/synthetic_loader/app_bootstrap/DATABASE_URL"
FULL_BOOTSTRAP_CREDENTIAL = "InternshipLifecyclePlatform/Neon/main/synthetic_loader/app_dataset_full/DATABASE_URL"
BOOTSTRAP_ROLE = "app_bootstrap"
FULL_BOOTSTRAP_ROLE = "app_dataset_full"
PASSWORD_TARGET_PREFIX = "InternshipLifecyclePlatform/SyntheticDataset/long-truth-39527618/main"
DEMO_POLICY_REASON = (
    "DH-05 synthetic demonstration assumption only: uses the fixture thresholds of 100 credits and "
    "academic level 6 within the named program. Not institutionally approved; replace with validated "
    "institutional criteria before operational use."
)
EXPECTED_USERS = {
    *(f"demo_student_{n:02d}" for n in range(4, 31)),
    *(f"demo_host_{n:02d}" for n in range(1, 9)),
    *(f"demo_supervisor_{n:02d}" for n in range(1, 9)),
    *(f"demo_faculty_{n:02d}" for n in range(2, 6)),
}
PARTIAL_ACL = {
    "select": {
        "academic_program": {"id", "code", "name"},
        "host_org": {"id", "name"},
        "user_account": {"id", "username", "email", "display_name", "is_active", "credits",
                         "academic_level", "completed_courses"},
        "role_assignment": {"id", "user_id", "role", "program_id", "host_org_id"},
        "opportunity": {"id", "host_org_id", "program_id", "title", "state"},
        "audit_event": {"id", "occurred_at"},
        "user_notification": {"recipient_id", "source_event_id"},
    },
    "insert": {
        "host_org": {"name"},
        "user_account": {"username", "email", "password_hash", "is_active", "display_name", "credits",
                         "academic_level", "completed_courses"},
        "role_assignment": {"user_id", "role", "program_id", "host_org_id"},
        "opportunity": {"host_org_id", "program_id", "title", "state"},
        "audit_event": {"actor_id", "action", "subject_type", "subject_id", "before_state",
                        "after_state", "correlation_id"},
        "user_notification": {"recipient_id", "source_event_id", "category", "placement_id",
                              "opportunity_id", "created_at"},
    },
    "update": {"opportunity": {"state"}},
}
PARTIAL_SEQUENCES = {
    "host_org_id_seq", "user_account_id_seq", "role_assignment_id_seq",
    "opportunity_id_seq", "audit_event_id_seq", "user_notification_id_seq",
}
APPLICATION_TABLES = (
    "academic_program", "host_org", "user_account", "role_assignment", "policy_version",
    "opportunity", "application", "placement", "placement_version", "supervisor_assignment",
    "placement_faculty_assignment_history", "checklist_item", "completion_requirement",
    "document_submission", "document_review", "progress_entry", "placement_work_plan_item",
    "placement_progress_report", "placement_evaluation", "placement_incident", "completion_evidence",
    "user_notification", "placement_conversation", "placement_message", "audit_event",
)
DEMO_POLICY_INSERT_COLUMNS = ("policy_key", "version_no", "conditions", "created_by")


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
    def __init__(self, store: WindowsCredentialStore, *, allow_credential_store_write: bool = False,
                 known_fingerprints: dict[str, bytes] | None = None) -> None:
        self.store = store
        self.allow_credential_store_write = allow_credential_store_write
        self.created_targets: list[str] = []
        self.known_fingerprints = known_fingerprints or {}
        self.used_fingerprints = set(self.known_fingerprints.values())

    def __call__(self, username: str) -> str:
        target = f"{PASSWORD_TARGET_PREFIX}/{username}/PASSWORD"
        password = self.store.read(target)
        if password is None:
            if not self.allow_credential_store_write:
                raise RuntimeError(
                    "A unique account credential is missing; explicit permission to write Windows Credential Manager is required."
                )
            password = secrets.token_urlsafe(32)
            fingerprint = hashlib.sha256(password.encode("utf-8")).digest()
            while fingerprint in self.used_fingerprints:
                password = secrets.token_urlsafe(32)
                fingerprint = hashlib.sha256(password.encode("utf-8")).digest()
            self.store.write(
                target, password, username=username,
                comment="Unique synthetic account credential; dataset loader.",
            )
            self.created_targets.append(target)
            self.used_fingerprints.add(fingerprint)
        else:
            fingerprint = hashlib.sha256(password.encode("utf-8")).digest()
            known = self.known_fingerprints.get(target)
            if (known is not None and known != fingerprint) or (
                    known is None and fingerprint in self.used_fingerprints):
                raise RuntimeError("A synthetic account password is duplicated or changed since preflight.")
            self.used_fingerprints.add(fingerprint)
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
    return {_partial_opportunity_title(index) for index in range(16)}


def _counts(cur, tables: tuple[str, ...] = APPLICATION_TABLES) -> dict[str, int]:
    return {table: cur.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
            for table in tables}


def _demo_eligibility_policy_plan(persisted_keys: set[str], *, enabled: bool) -> dict[str, Any]:
    required = {f"ELIGIBILITY:{code}" for code in PROGRAMS}
    present = sorted(required & persisted_keys)
    missing = sorted(required - persisted_keys)
    return {
        "present": present,
        "missing": missing,
        "to_create": missing if enabled else [],
        "opt_in_required": bool(missing and not enabled),
        "assumption_reason": DEMO_POLICY_REASON if enabled and missing else None,
    }


def _inspect_database(url: str, *, set_application_role: bool, mode: str = "partial",
                      allow_demo_eligibility_policy: bool = False,
                      allow_demo_lifecycle_records: bool = False) -> dict[str, Any]:
    details = _connection_details(
        url, require_direct=not set_application_role,
        expected_user="app_runtime" if set_application_role else (
            BOOTSTRAP_ROLE if mode == "partial" else FULL_BOOTSTRAP_ROLE
        ),
    )
    expected_titles = _expected_titles()
    report: dict[str, Any] = {
        "target": {"project": PROJECT_ID, "branch": BRANCH_NAME, "branch_id": BRANCH_ID,
                   "database": DATABASE_NAME},
        "mode": mode,
        "fixture_target": {"new_accounts_max": len(EXPECTED_USERS),
                           "organizations": 10,
                           "opportunities": 16,
                           "applications": 0 if mode == "partial" else 24,
                           "placements": 0 if mode == "partial" else 12,
                           "reuse_policy": "natural keys; existing unrelated rows preserved"},
        "connection_role": details.get("user"),
        "tls": False,
        "migration": None,
        "counts": {},
        "collisions": {},
        "eligibility_policies": [],
        "demo_eligibility_policy": {"enabled": allow_demo_eligibility_policy, "planned_keys": []},
        "demo_lifecycle_records": {
            "enabled": allow_demo_lifecycle_records,
            "classification": "explicit DH-05 synthetic records; never institutional evidence",
            "hours_source": "persisted placement requirement; no threshold is invented",
            "evidence_filename": "informe-final-sintetico.pdf",
        },
        "authority_variables_configured": {},
        "planned_insertions": {},
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
                if not set_application_role and identity["login_role"] != identity["active_role"]:
                    raise RuntimeError("The bootstrap credential must connect directly as its restricted login role.")
                report["tls"] = bool(conn.pgconn.ssl_in_use)
                if not report["tls"]:
                    raise RuntimeError("Neon connection did not negotiate TLS.")
                # The migration ledger is intentionally inaccessible to runtime and
                # bootstrap roles; this table is introduced by 0012/0013.
                marker = conn.execute(
                    "SELECT to_regclass('public.placement_faculty_assignment_history') IS NOT NULL AS present"
                ).fetchone()["present"]
                report["schema_marker_present"] = bool(marker)
                report["migration"] = (
                    "Alembic ledger is not readable by runtime; schema marker introduced at 0012 is present"
                    if marker else "unverified"
                )
                if not marker:
                    report["blockers"].append("The required application schema marker is missing.")
                report["counts"] = _counts(conn.cursor())
                demo_users = conn.execute(
                    "SELECT username FROM user_account WHERE username=ANY(%s) ORDER BY username",
                    (list(EXPECTED_USERS),),
                ).fetchall()
                demo_names = {row["username"] for row in demo_users}
                report["collisions"]["expected_accounts_already_present"] = len(demo_names)
                report["collisions"]["expected_accounts_missing"] = len(EXPECTED_USERS - demo_names)
                report["_missing_account_usernames"] = sorted(EXPECTED_USERS - demo_names)
                expected_orgs = list(ALL_SYNTHETIC_ORGANIZATIONS)
                org_names = conn.execute(
                    "SELECT name,count(*) AS n FROM host_org WHERE name=ANY(%s) GROUP BY name",
                    (expected_orgs,),
                ).fetchall()
                if any(row["n"] != 1 for row in org_names):
                    report["blockers"].append("Expected synthetic organization names are duplicated.")
                report["collisions"]["expected_organizations_already_present"] = sum(
                    row["n"] for row in org_names
                )
                opportunities = conn.execute(
                    "SELECT title,state,host_org_id,program_id,count(*) AS n FROM opportunity "
                    "WHERE title=ANY(%s) GROUP BY title,state,host_org_id,program_id",
                    (list(expected_titles),),
                ).fetchall()
                title_names = {row["title"] for row in opportunities}
                report["collisions"]["expected_opportunities_already_present"] = sum(
                    row["n"] for row in opportunities
                )
                if any(row["n"] > 1 for row in opportunities):
                    report["blockers"].append("An expected synthetic opportunity title is duplicated.")
                if mode == "partial" and any(
                        row["state"] not in {"DRAFT", "IN_REVIEW"} for row in opportunities):
                    report["blockers"].append(
                        "An expected synthetic opportunity is beyond DRAFT/IN_REVIEW; it will be preserved."
                    )
                org_missing = len(set(expected_orgs) - {row["name"] for row in conn.execute(
                    "SELECT name FROM host_org WHERE name=ANY(%s)", (expected_orgs,)
                ).fetchall()})
                account_missing = len(EXPECTED_USERS - demo_names)
                opportunities_missing = len(expected_titles - title_names)
                applications_on_expected = conn.execute(
                    "SELECT count(*) AS n FROM application a JOIN opportunity o ON o.id=a.opportunity_id "
                    "WHERE o.title=ANY(%s)", (list(expected_titles),),
                ).fetchone()["n"]
                if mode == "partial" and applications_on_expected:
                    report["blockers"].append(
                        "Expected partial opportunities already have applications; no existing record will be changed."
                    )
                programs = conn.execute(
                    "SELECT id,code,name FROM academic_program WHERE code=ANY(%s)", (list(PROGRAMS),)
                ).fetchall()
                program_names = {row["code"]: row["name"] for row in programs}
                if any(program_names.get(code) != name for code, name in PROGRAMS.items()):
                    report["blockers"].append(
                        "Required synthetic program catalogs are absent or differ; partial mode will not create them."
                    )
                program_ids = {row["code"]: row["id"] for row in programs}
                pending_transitions = 0
                states_by_title = {row["title"]: row["state"] for row in opportunities}
                new_review_indexes = []
                for index in range(16):
                    title = _partial_opportunity_title(index)
                    if index % 2 and states_by_title.get(title) in {None, "DRAFT"}:
                        pending_transitions += 1
                        new_review_indexes.append(index)
                reviewer_roles = [role.strip() for role in
                                  os.environ.get("OPPORTUNITY_REVIEWER_ROLES", "").split(",") if role.strip()]
                planned_notifications = 0
                if reviewer_roles:
                    for index in new_review_indexes:
                        program_code = "ING-SIS" if index % 2 == 0 else "ADM"
                        planned_notifications += conn.execute(
                            """SELECT count(DISTINCT ra.user_id) AS n FROM role_assignment ra
                               WHERE ra.role=ANY(%s) AND (ra.role='EXPERIENTIAL_COORDINATOR' OR ra.program_id=%s)""",
                            (reviewer_roles, program_ids.get(program_code)),
                        ).fetchone()["n"]
                report["planned_insertions"] = {
                    "host_org": org_missing if mode == "partial" else max(0, 10 - len(org_names)),
                    "user_account": account_missing,
                    "role_assignment": account_missing,
                    "opportunity": opportunities_missing,
                    "audit_event": opportunities_missing + pending_transitions if mode == "partial" else None,
                    "opportunity_submit_for_review": pending_transitions if mode == "partial" else None,
                    "user_notification": planned_notifications if mode == "partial" else None,
                    "application": 0 if mode == "partial" else None,
                    "placement": 0 if mode == "partial" else None,
                    "policies": 0,
                    "existing_applications_on_expected_opportunities": applications_on_expected,
                }
                report["planned_omissions"] = {
                    "host_org_reused": len(expected_orgs) - report["planned_insertions"]["host_org"],
                    "user_account_reused": len(EXPECTED_USERS) - account_missing,
                    "role_assignment_reused": len(EXPECTED_USERS) - account_missing,
                    "opportunity_reused": len(expected_titles) - opportunities_missing,
                    "policy_writes": 0,
                }
                if mode == "partial":
                    report["planned_omissions"].update({
                        "applications_by_partial_scope": 24,
                        "placements_by_partial_scope": 12,
                        "published_opportunities_by_partial_scope": 12,
                    })
                org_rows = conn.execute(
                    "SELECT id,name FROM host_org WHERE name=ANY(%s)", (expected_orgs,)
                ).fetchall()
                org_ids = {row["name"]: row["id"] for row in org_rows}
                profile_conflicts = 0
                relationship_conflicts = 0
                if (len(program_ids) == len(PROGRAMS) and len(org_ids) == len(expected_orgs)
                        and not any(row["n"] != 1 for row in org_names)):
                    for spec in _partial_account_specs(program_ids, org_ids):
                        existing = conn.execute(
                            """SELECT id,email,display_name,credits,academic_level,completed_courses,is_active
                               FROM user_account WHERE username=%s""",
                            (spec["username"],),
                        ).fetchone()
                        if existing is None:
                            continue
                        if (existing["email"], existing["display_name"], existing["credits"],
                                existing["academic_level"], existing["completed_courses"],
                                existing["is_active"]) != (
                                f"{spec['username']}@horizon.example.test", spec["display_name"],
                                spec["credits"], spec["level"], list(spec["courses"]), True):
                            profile_conflicts += 1
                        assignments = conn.execute(
                            "SELECT role,program_id,host_org_id FROM role_assignment WHERE user_id=%s "
                            "ORDER BY role,program_id,host_org_id", (existing["id"],),
                        ).fetchall()
                        expected_assignment = {"role": spec["role"], "program_id": spec["program_id"],
                                               "host_org_id": spec["host_org_id"]}
                        if assignments != [expected_assignment]:
                            relationship_conflicts += 1
                report["collisions"]["account_profile_conflicts"] = profile_conflicts
                report["collisions"]["account_role_conflicts"] = relationship_conflicts
                if profile_conflicts or relationship_conflicts:
                    report["blockers"].append(
                        "An expected synthetic account differs from the fixture profile/relationship; it will be preserved."
                    )
                opportunity_relation_conflicts = 0
                for row in opportunities:
                    if row["n"] != 1:
                        continue
                    index = next(i for i in range(16) if _partial_opportunity_title(i) == row["title"])
                    org_id = org_ids.get(ALL_SYNTHETIC_ORGANIZATIONS[index % len(ALL_SYNTHETIC_ORGANIZATIONS)])
                    program_code = "ING-SIS" if index % 2 == 0 else "ADM"
                    if (row["host_org_id"], row["program_id"]) != (org_id, program_ids.get(program_code)):
                        opportunity_relation_conflicts += 1
                report["collisions"]["opportunity_relation_conflicts"] = opportunity_relation_conflicts
                if opportunity_relation_conflicts:
                    report["blockers"].append(
                        "An expected synthetic opportunity has different organization/program relations; it will be preserved."
                    )
                policies = conn.execute(
                    "SELECT policy_key FROM policy_version WHERE policy_key IN "
                    "('ELIGIBILITY:ING-SIS','ELIGIBILITY:ADM','ACTIVATION:ING-SIS','ACTIVATION:ADM',"
                    "'COMPLETION:ING-SIS','COMPLETION:ADM') AND effective_from <= now() "
                    "GROUP BY policy_key ORDER BY policy_key"
                ).fetchall()
                persisted = {row["policy_key"] for row in policies}
                report["persisted_policies"] = sorted(persisted)
                report["eligibility_policies"] = sorted(
                    key for key in persisted if key.startswith("ELIGIBILITY:")
                )
                required_lifecycle_policies = {
                    f"{kind}:{code}" for kind in ("ACTIVATION", "COMPLETION") for code in PROGRAMS
                }
                missing_lifecycle_policies = sorted(required_lifecycle_policies - persisted)
                if mode == "full" and missing_lifecycle_policies:
                    report["blockers"].append(
                        "Full mode requires existing activation and completion policies for each program."
                    )
                demo_policy_plan = _demo_eligibility_policy_plan(
                    persisted, enabled=allow_demo_eligibility_policy,
                )
                report["demo_eligibility_policy"] = {
                    "enabled": allow_demo_eligibility_policy,
                    "present_keys": demo_policy_plan["present"],
                    "planned_keys": demo_policy_plan["to_create"],
                    "conditions_per_key": [
                        {"type": "PROGRAM_IN", "value": "the corresponding program code"},
                        {"type": "CREDITS_MIN", "value": 100},
                        {"type": "ACADEMIC_LEVEL_MIN", "value": 6},
                    ] if demo_policy_plan["to_create"] else [],
                    "reason": demo_policy_plan["assumption_reason"],
                    "classification": "replaceable DH-05 synthetic demo assumption; not institutional policy",
                }
                if mode == "full" and demo_policy_plan["opt_in_required"]:
                    report["blockers"].append(
                        "Full mode is missing eligibility policies; pass --allow-demo-eligibility-policy "
                        "to append the explicitly labeled synthetic demo assumptions."
                    )
                report["planned_insertions"]["policy_version"] = (
                    len(demo_policy_plan["to_create"]) if mode == "full" else 0
                )
                report["planned_insertions"]["policies"] = (
                    len(demo_policy_plan["to_create"]) if mode == "full" else 0
                )
                report["planned_omissions"]["policy_writes"] = 0
                for key in ("OPPORTUNITY_REVIEWER_ROLES", "OPPORTUNITY_PUBLISHER_ROLES",
                            "PLACEMENT_FACULTY_ASSIGNER_ROLES"):
                    report["authority_variables_configured"][key] = bool(os.environ.get(key, "").strip())
                    if mode == "full" and not report["authority_variables_configured"][key]:
                        report["blockers"].append(f"Institutional authority {key} is not configured for this loader.")
                report["integrity"] = _table_integrity(conn.cursor())
    except Exception as exc:
        # Driver exception strings can include connection metadata; withhold them.
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        location = f"{Path(frame.filename).name}:{frame.lineno} ({frame.name})"
        raise RuntimeError(
            f"Read-only Neon preflight failed ({type(exc).__name__} at {location}); details withheld."
        ) from exc
    return report


def _demo_policy_insert_acl(conn, *, enabled: bool) -> dict[str, Any]:
    """Require exact column-level append-only policy rights for the full-loader login."""
    columns = [row["attname"] for row in conn.execute(
        """SELECT a.attname FROM pg_attribute a
           WHERE a.attrelid='public.policy_version'::regclass
             AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"""
    ).fetchall()]
    capabilities: dict[str, Any] = {}
    blockers: list[str] = []
    for column in columns:
        allowed = conn.execute(
            "SELECT has_column_privilege(current_user,'public.policy_version',%s,'INSERT') AS allowed",
            (column,),
        ).fetchone()["allowed"]
        expected = enabled and column in DEMO_POLICY_INSERT_COLUMNS
        capabilities[f"insert_column:{column}"] = bool(allowed)
        if bool(allowed) != expected:
            level = "Unexpected" if allowed else "Missing"
            blockers.append(f"{level} policy_version.{column} INSERT privilege for demo policy scope.")

    table_insert = conn.execute(
        "SELECT has_table_privilege(current_user,'public.policy_version','INSERT') AS allowed"
    ).fetchone()["allowed"]
    if table_insert:
        blockers.append("Full bootstrap must use exact column INSERT grants, not table-wide policy_version INSERT.")
    update_rights = conn.execute(
        """SELECT has_table_privilege(current_user,'public.policy_version','UPDATE') AS table_allowed,
                  bool_or(has_column_privilege(current_user,'public.policy_version',a.attname,'UPDATE')) AS column_allowed
           FROM pg_attribute a WHERE a.attrelid='public.policy_version'::regclass
             AND a.attnum > 0 AND NOT a.attisdropped"""
    ).fetchone()
    if update_rights["table_allowed"] or update_rights["column_allowed"]:
        blockers.append("Full bootstrap must never update policy versions; demo policies are append-only.")
    for action in ("DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
        allowed = conn.execute(
            "SELECT has_table_privilege(current_user,'public.policy_version',%s) AS allowed",
            (action,),
        ).fetchone()["allowed"]
        if allowed:
            blockers.append(f"Full bootstrap must not have {action} on policy_version.")
        if action == "REFERENCES":
            column_allowed = conn.execute(
                """SELECT bool_or(has_column_privilege(current_user,'public.policy_version',a.attname,'REFERENCES')) AS allowed
                   FROM pg_attribute a WHERE a.attrelid='public.policy_version'::regclass
                     AND a.attnum > 0 AND NOT a.attisdropped"""
            ).fetchone()["allowed"]
            if column_allowed:
                blockers.append("Full bootstrap must not have column-level REFERENCES on policy_version.")

    sequence = "public.policy_version_id_seq"
    for action in ("USAGE", "SELECT", "UPDATE"):
        allowed = conn.execute(
            "SELECT has_sequence_privilege(current_user,%s,%s) AS allowed",
            (sequence, action),
        ).fetchone()["allowed"]
        expected = enabled and action == "USAGE"
        capabilities[f"policy_sequence:{action.lower()}"] = bool(allowed)
        if bool(allowed) != expected:
            level = "Unexpected" if allowed else "Missing"
            blockers.append(f"{level} {action} on policy_version_id_seq for demo policy scope.")
    return {"capabilities": capabilities, "blockers": blockers}


def _inspect_bootstrap(url: str, *, mode: str,
                       allow_demo_eligibility_policy: bool = False) -> dict[str, Any]:
    role = BOOTSTRAP_ROLE if mode == "partial" else FULL_BOOTSTRAP_ROLE
    details = _connection_details(url, require_direct=True, expected_user=role)
    result: dict[str, Any] = {"role": role, "tls": False, "capabilities": {}, "blockers": []}
    try:
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10,
                             application_name="synthetic_dataset_bootstrap_check") as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                identity = conn.execute(
                    "SELECT session_user AS login_role,current_user AS active_role,current_database() AS database"
                ).fetchone()
                if (identity["database"] != DATABASE_NAME or identity["login_role"] != role
                        or identity["active_role"] != role):
                    raise RuntimeError("Bootstrap identity does not match the restricted role for this mode.")
                result["tls"] = bool(conn.pgconn.ssl_in_use)
                if not result["tls"]:
                    raise RuntimeError("Bootstrap connection did not negotiate TLS.")
                role_state = conn.execute(
                    """SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls,
                              rolinherit,rolreplication
                       FROM pg_roles WHERE rolname=current_user"""
                ).fetchone()
                membership_count = conn.execute(
                    "SELECT count(*) AS n FROM pg_auth_members WHERE member=current_user::regrole"
                ).fetchone()["n"]
                result["role_flags"] = role_state
                result["membership_count"] = membership_count
                if (not role_state["rolcanlogin"] or role_state["rolsuper"] or role_state["rolcreatedb"]
                        or role_state["rolcreaterole"] or role_state["rolbypassrls"]
                        or role_state["rolinherit"] or role_state["rolreplication"] or membership_count):
                    result["blockers"].append(
                        "Bootstrap must be LOGIN, NOINHERIT, non-admin, and have no role memberships."
                    )
                if conn.execute(
                    "SELECT has_schema_privilege(current_user,'public','CREATE') AS allowed"
                ).fetchone()["allowed"]:
                    result["blockers"].append("Bootstrap must not have CREATE on schema public.")
                marker = conn.execute(
                    "SELECT to_regclass('public.placement_faculty_assignment_history') IS NOT NULL AS present"
                ).fetchone()["present"]
                if not marker:
                    result["blockers"].append("The required application schema marker is missing.")

                if mode == "full":
                    full_read = (
                        "academic_program", "host_org", "role_assignment", "policy_version", "opportunity",
                        "application", "placement", "placement_version", "checklist_item",
                        "document_submission", "document_review", "progress_entry",
                        "placement_work_plan_item", "placement_progress_report", "placement_evaluation",
                        "placement_incident", "completion_evidence", "completion_requirement",
                        "user_notification", "placement_conversation", "placement_message", "audit_event",
                        "supervisor_assignment", "placement_faculty_assignment_history",
                    )
                    full_insert = (
                        "academic_program", "host_org", "user_account", "role_assignment", "opportunity", "application",
                        "placement", "placement_version", "checklist_item", "completion_requirement",
                        "document_submission", "document_review", "progress_entry",
                        "placement_work_plan_item", "placement_progress_report", "placement_evaluation",
                        "placement_incident", "completion_evidence", "user_notification",
                        "placement_conversation", "placement_message", "audit_event", "supervisor_assignment",
                        "placement_faculty_assignment_history",
                    )
                    full_update = (
                        "opportunity", "application", "placement", "placement_version", "checklist_item",
                        "completion_requirement",
                    )
                    full_sequences = tuple(f"{table}_id_seq" for table in full_insert
                                           if table not in {"supervisor_assignment"})
                    for table in full_read:
                        allowed = conn.execute(
                            "SELECT has_table_privilege(current_user,%s,'SELECT') AS allowed",
                            (f"public.{table}",),
                        ).fetchone()["allowed"]
                        result["capabilities"][f"select:{table}"] = bool(allowed)
                        if not allowed:
                            result["blockers"].append(f"Full bootstrap is missing SELECT on {table}.")
                    account_columns = ("id", "username", "email", "is_active", "display_name", "credits",
                                       "academic_level", "completed_courses")
                    for column in account_columns:
                        allowed = conn.execute(
                            "SELECT has_column_privilege(current_user,'public.user_account',%s,'SELECT') AS allowed",
                            (column,),
                        ).fetchone()["allowed"]
                        result["capabilities"][f"select:user_account.{column}"] = bool(allowed)
                        if not allowed:
                            result["blockers"].append(f"Full bootstrap is missing SELECT on user_account.{column}.")
                    if conn.execute(
                        "SELECT has_column_privilege(current_user,'public.user_account','password_hash','SELECT') AS allowed"
                    ).fetchone()["allowed"]:
                        result["blockers"].append("Full bootstrap must not read password hashes.")
                    for table in full_insert:
                        allowed = conn.execute(
                            "SELECT has_table_privilege(current_user,%s,'INSERT') AS allowed",
                            (f"public.{table}",),
                        ).fetchone()["allowed"]
                        result["capabilities"][f"insert:{table}"] = bool(allowed)
                        if not allowed:
                            result["blockers"].append(f"Full bootstrap is missing INSERT on {table}.")
                    for table in full_update:
                        allowed = conn.execute(
                            "SELECT has_table_privilege(current_user,%s,'UPDATE') AS allowed",
                            (f"public.{table}",),
                        ).fetchone()["allowed"]
                        result["capabilities"][f"update:{table}"] = bool(allowed)
                        if not allowed:
                            result["blockers"].append(f"Full bootstrap is missing UPDATE on {table}.")
                    policy_acl = _demo_policy_insert_acl(
                        conn, enabled=allow_demo_eligibility_policy,
                    )
                    result["capabilities"].update(policy_acl["capabilities"])
                    result["blockers"].extend(policy_acl["blockers"])
                    for table in set(full_read) | set(full_insert) | set(full_update):
                        allowed = conn.execute(
                            "SELECT has_table_privilege(current_user,%s,'DELETE') AS allowed",
                            (f"public.{table}",),
                        ).fetchone()["allowed"]
                        result["capabilities"][f"delete:{table}"] = not bool(allowed)
                        if allowed:
                            result["blockers"].append(f"Full bootstrap must not have DELETE on {table}.")
                    for sequence in full_sequences:
                        allowed = conn.execute(
                            "SELECT has_sequence_privilege(current_user,%s,'USAGE') AS allowed",
                            (f"public.{sequence}",),
                        ).fetchone()["allowed"]
                        result["capabilities"][f"sequence_usage:{sequence}"] = bool(allowed)
                        if not allowed:
                            result["blockers"].append(f"Full bootstrap is missing USAGE on {sequence}.")
                    return result

                required_select = {
                    "academic_program": ("id", "code", "name"),
                    "host_org": ("id", "name"),
                    "user_account": ("id", "username", "email", "display_name", "is_active", "credits",
                                     "academic_level", "completed_courses"),
                    "role_assignment": ("id", "user_id", "role", "program_id", "host_org_id"),
                    "opportunity": ("id", "host_org_id", "program_id", "title", "state"),
                    "audit_event": ("id", "occurred_at"),
                    # PostgreSQL requires SELECT on the ON CONFLICT arbiter columns.
                    "user_notification": ("recipient_id", "source_event_id"),
                }
                required_insert = {
                    "host_org": ("name",),
                    "user_account": ("username", "email", "password_hash", "is_active", "display_name",
                                     "credits", "academic_level", "completed_courses"),
                    "role_assignment": ("user_id", "role", "program_id", "host_org_id"),
                    "opportunity": ("host_org_id", "program_id", "title", "state"),
                    "audit_event": ("actor_id", "action", "subject_type", "subject_id", "before_state",
                                    "after_state", "correlation_id"),
                    "user_notification": ("recipient_id", "source_event_id", "category", "placement_id",
                                          "opportunity_id", "created_at"),
                }
                for action, requirements in (("SELECT", required_select), ("INSERT", required_insert)):
                    for table, columns in requirements.items():
                        for column in columns:
                            allowed = conn.execute(
                                "SELECT has_column_privilege(current_user,%s,%s,%s) AS allowed",
                                (f"public.{table}", column, action),
                            ).fetchone()["allowed"]
                            result["capabilities"][f"{action.lower()}:{table}.{column}"] = bool(allowed)
                            if not allowed:
                                result["blockers"].append(
                                    f"Bootstrap is missing required {action} on {table}.{column}."
                                )
                state_update = conn.execute(
                    "SELECT has_column_privilege(current_user,'public.opportunity','state','UPDATE') AS allowed"
                ).fetchone()["allowed"]
                result["capabilities"]["update:opportunity.state"] = bool(state_update)
                if not state_update:
                    result["blockers"].append("Bootstrap is missing UPDATE on opportunity.state.")

                prohibited = ("academic_program", "policy_version", "application", "placement")
                for table in prohibited:
                    dml = conn.execute(
                        "SELECT has_table_privilege(current_user,%s,'INSERT') AS ins, "
                        "has_table_privilege(current_user,%s,'UPDATE') AS upd, "
                        "has_table_privilege(current_user,%s,'DELETE') AS del",
                        (f"public.{table}",) * 3,
                    ).fetchone()
                    result["capabilities"][f"prohibited_dml:{table}"] = not any(dml.values())
                    if any(dml.values()):
                        result["blockers"].append(f"Bootstrap has prohibited write access to {table}.")
                if conn.execute(
                    "SELECT has_column_privilege(current_user,'public.user_account','password_hash','SELECT') AS allowed"
                ).fetchone()["allowed"]:
                    result["blockers"].append("Bootstrap must not read password hashes.")
                sequences = ("host_org_id_seq", "user_account_id_seq", "role_assignment_id_seq",
                             "opportunity_id_seq", "audit_event_id_seq", "user_notification_id_seq")
                for sequence in sequences:
                    allowed = conn.execute(
                        "SELECT has_sequence_privilege(current_user,%s,'USAGE') AS allowed",
                        (f"public.{sequence}",),
                    ).fetchone()["allowed"]
                    result["capabilities"][f"sequence_usage:{sequence}"] = bool(allowed)
                    if not allowed:
                        result["blockers"].append(f"Bootstrap is missing USAGE on sequence {sequence}.")
                result["blockers"].extend(_unexpected_partial_privileges(conn))
    except Exception as exc:
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        location = f"{Path(frame.filename).name}:{frame.lineno} ({frame.name})"
        raise RuntimeError(
            f"Read-only bootstrap check failed ({type(exc).__name__} at {location}); details withheld."
        ) from exc
    return result


def _unexpected_partial_privileges(conn) -> list[str]:
    """Require the partial login's effective public-schema ACL to match its allowlist."""
    blockers: list[str] = []
    relations = conn.execute(
        """SELECT c.oid,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f') ORDER BY c.relname"""
    ).fetchall()
    for relation in relations:
        columns = conn.execute(
            """SELECT a.attname FROM pg_attribute a
               WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped ORDER BY a.attnum""",
            (relation["oid"],),
        ).fetchall()
        for action, table_allowlist in PARTIAL_ACL.items():
            permitted = table_allowlist.get(relation["relname"], set())
            for column in columns:
                allowed = conn.execute(
                    "SELECT has_column_privilege(current_user,%s,%s,%s) AS allowed",
                    (relation["oid"], column["attname"], action.upper()),
                ).fetchone()["allowed"]
                if bool(allowed) != (column["attname"] in permitted):
                    direction = "Unexpected" if allowed else "Missing"
                    blockers.append(
                        f"{direction} effective {action.upper()} on public.{relation['relname']}.{column['attname']}."
                    )
        for action in ("DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            allowed = conn.execute(
                "SELECT has_table_privilege(current_user,%s,%s) AS allowed",
                (relation["oid"], action),
            ).fetchone()["allowed"]
            if allowed:
                blockers.append(f"Unexpected effective {action} on public.{relation['relname']}.")
        for column in columns:
            references = conn.execute(
                "SELECT has_column_privilege(current_user,%s,%s,'REFERENCES') AS allowed",
                (relation["oid"], column["attname"]),
            ).fetchone()["allowed"]
            if references:
                blockers.append(
                    f"Unexpected effective REFERENCES on public.{relation['relname']}.{column['attname']}."
                )

    sequences = conn.execute(
        """SELECT c.oid,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
           WHERE n.nspname='public' AND c.relkind='S' ORDER BY c.relname"""
    ).fetchall()
    for sequence in sequences:
        for action in ("USAGE", "SELECT", "UPDATE"):
            allowed = conn.execute(
                "SELECT has_sequence_privilege(current_user,%s,%s) AS allowed",
                (sequence["oid"], action),
            ).fetchone()["allowed"]
            expected = action == "USAGE" and sequence["relname"] in PARTIAL_SEQUENCES
            if bool(allowed) != expected:
                direction = "Unexpected" if allowed else "Missing"
                blockers.append(f"{direction} effective {action} on public.{sequence['relname']}.")

    schemas = conn.execute(
        """SELECT oid,nspname FROM pg_namespace
           WHERE nspname <> 'information_schema' AND nspname !~ '^pg_' ORDER BY nspname"""
    ).fetchall()
    for schema in schemas:
        usage = conn.execute(
            "SELECT has_schema_privilege(current_user,%s,'USAGE') AS allowed",
            (schema["oid"],),
        ).fetchone()["allowed"]
        create = conn.execute(
            "SELECT has_schema_privilege(current_user,%s,'CREATE') AS allowed",
            (schema["oid"],),
        ).fetchone()["allowed"]
        if bool(usage) != (schema["nspname"] == "public"):
            direction = "Unexpected" if usage else "Missing"
            blockers.append(f"{direction} effective USAGE on schema {schema['nspname']}.")
        if create:
            blockers.append(f"Unexpected effective CREATE on schema {schema['nspname']}.")

    database_privileges = conn.execute(
        """SELECT d.oid,
                  has_database_privilege(current_user,d.oid,'CREATE') AS create_allowed,
                  EXISTS (
                    SELECT 1 FROM aclexplode(coalesce(d.datacl,acldefault('d',d.datdba))) acl
                    WHERE acl.grantee=current_user::regrole AND acl.privilege_type='TEMPORARY'
                  ) AS direct_temp_grant
           FROM pg_database d WHERE d.datname=current_database()"""
    ).fetchone()
    if database_privileges["create_allowed"] or database_privileges["direct_temp_grant"]:
        blockers.append("Bootstrap must not have CREATE or a direct TEMP grant on the database.")
    return blockers


def _snapshot_summary(branches: list[dict[str, Any]]) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    recent = []
    for branch in branches:
        if (branch.get("project_id") != PROJECT_ID or branch.get("id") == BRANCH_ID
                or branch.get("parent_id") != BRANCH_ID):
            continue
        try:
            created = dt.datetime.fromisoformat(str(branch.get("created_at")).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            continue
        if created.tzinfo is not None and dt.timedelta(0) <= now - created <= dt.timedelta(hours=24):
            recent.append(branch)
    return {"branch_count": len(branches), "recent_snapshot_available": bool(recent),
            "recent_snapshot_count": len(recent)}


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


def _active_transaction_load(url: str, runtime_url: str, store: WindowsCredentialStore,
                            commit_state: dict[str, bool], *, mode: str,
                            allow_credential_store_write: bool,
                            allow_demo_eligibility_policy: bool,
                            allow_demo_lifecycle_records: bool,
                            known_password_fingerprints: dict[str, bytes]) -> dict[str, Any]:
    role = BOOTSTRAP_ROLE if mode == "partial" else FULL_BOOTSTRAP_ROLE
    _connection_details(url, require_direct=True, expected_user=role)
    password_hash_for = UniquePasswordHashes(
        store, allow_credential_store_write=allow_credential_store_write,
        known_fingerprints=known_password_fingerprints,
    )
    synthetic_placement_states: dict[str, int] = {}
    try:
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=10,
                             application_name="synthetic_dataset_loader", autocommit=True) as conn:
            commit_state["transaction_started"] = True
            with conn.transaction():
                state = conn.execute(
                    "SELECT session_user AS login_role,current_user AS active_role,current_database() AS database"
                ).fetchone()
                if (state["login_role"] != role or state["active_role"] != role
                        or state["database"] != DATABASE_NAME):
                    raise RuntimeError("Bootstrap identity does not match the approved target and mode.")
                marker = conn.execute(
                    "SELECT to_regclass('public.placement_faculty_assignment_history') IS NOT NULL AS present"
                ).fetchone()["present"]
                if not marker:
                    raise RuntimeError("The required schema marker is missing; no data was changed.")
                conn.execute(
                    "SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",
                    (f"synthetic-dataset:{mode}:{PROJECT_ID}:{BRANCH_ID}",),
                )
                with db.shared_command_connection(conn, required_role=role):
                    if mode == "partial":
                        first = populate_synthetic_partial(
                            conn.cursor(), password_hash_for=password_hash_for,
                        )
                        second = populate_synthetic_partial(
                            conn.cursor(), password_hash_for=password_hash_for,
                        )
                        if any(second["inserted"].values()):
                            raise RuntimeError("The partial second pass inserted duplicate records; transaction rolled back.")
                        inserted_counts = first["inserted"]
                        integrity = conn.execute(
                            """SELECT count(*) AS broken FROM opportunity o
                               LEFT JOIN host_org h ON h.id=o.host_org_id
                               LEFT JOIN academic_program p ON p.id=o.program_id
                               WHERE o.title=ANY(%s) AND (h.id IS NULL OR p.id IS NULL
                                 OR o.state NOT IN ('DRAFT','IN_REVIEW'))""",
                            (list(_expected_titles()),),
                        ).fetchone()["broken"]
                        if integrity:
                            raise RuntimeError("Partial relationship/state integrity failed; transaction rolled back.")
                    else:
                        before_counts = _counts(conn.cursor())
                        first = populate_synthetic_dataset(
                            conn.cursor(), include_demo_eligibility_policy=allow_demo_eligibility_policy,
                            demo_eligibility_policy_reason=DEMO_POLICY_REASON,
                            password_hash_for=password_hash_for,
                            allow_demo_lifecycle_records=allow_demo_lifecycle_records,
                        )
                        second = populate_synthetic_dataset(
                            conn.cursor(), include_demo_eligibility_policy=allow_demo_eligibility_policy,
                            demo_eligibility_policy_reason=DEMO_POLICY_REASON,
                            password_hash_for=password_hash_for,
                            allow_demo_lifecycle_records=allow_demo_lifecycle_records,
                        )
                        if first != second:
                            raise RuntimeError("The second full pass was not idempotent; transaction rolled back.")
                        integrity = _table_integrity(conn.cursor())
                        if any(integrity.values()):
                            raise RuntimeError("Relationship or constraint verification failed; transaction rolled back.")
                        final_counts = _counts(conn.cursor())
                        inserted_counts = {
                            table: final_counts[table] - before_counts[table]
                            for table in APPLICATION_TABLES
                        }
                        scenario_ids = list(first.get("placement_scenarios", {}).values())
                        if scenario_ids:
                            synthetic_placement_states = {
                                row["state"]: row["n"] for row in conn.execute(
                                    "SELECT state,count(*) AS n FROM placement WHERE id=ANY(%s) GROUP BY state",
                                    (scenario_ids,),
                                ).fetchall()
                            }
            commit_state["committed"] = True
        password_hash_for.created_targets.clear()
    except Exception:
        if not commit_state["committed"]:
            password_hash_for.cleanup_new_credentials()
        raise

    # Read-only runtime postflight verifies the committed projection and lifecycle tables.
    verification = _inspect_database(
        runtime_url, set_application_role=True, mode=mode,
        allow_demo_eligibility_policy=allow_demo_eligibility_policy,
        allow_demo_lifecycle_records=allow_demo_lifecycle_records,
    )
    verification["post_commit_integrity"] = verification.pop("integrity")
    verification["idempotent_in_same_transaction"] = (
        not any(second["inserted"].values()) if mode == "partial" else first == second
    )
    verification["loaded_totals"] = first.get("totals", first)
    verification["inserted_counts"] = inserted_counts
    verification["omitted_counts"] = first.get("omitted", {})
    if mode == "partial":
        verification["opportunity_states"] = first.get("opportunity_states", {})
        verification["mode_report"] = {
            "synthetic_accounts_expected": first.get("synthetic_accounts_expected"),
            "synthetic_organizations_expected": first.get("synthetic_organizations_expected"),
            "synthetic_opportunities_expected": first.get("synthetic_opportunities_expected"),
            "applications_created": 0,
            "placements_created": 0,
            "policies_created": 0,
        }
    else:
        verification["mode_report"] = {
            "demo_eligibility_policy_opt_in": allow_demo_eligibility_policy,
            "demo_eligibility_policies_created": inserted_counts.get("policy_version", 0),
            "demo_lifecycle_records_opt_in": allow_demo_lifecycle_records,
            "synthetic_hours_created": inserted_counts.get("progress_entry", 0),
            "synthetic_completion_evidence_created": inserted_counts.get("completion_evidence", 0),
            "synthetic_evaluations_created": inserted_counts.get("placement_evaluation", 0),
            "synthetic_placement_states": synthetic_placement_states,
        }
    verification["write_performed"] = True
    return verification


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only preflight or guarded Neon synthetic dataset load.")
    parser.add_argument("--mode", choices=("partial", "full"), default="partial",
                        help="Partial catalog-only fixture (default) or full workflow fixture.")
    parser.add_argument("--apply", action="store_true", help="Apply only after every preflight gate passes.")
    parser.add_argument("--confirm-target", help="Must equal long-truth-39527618/main for --apply.")
    parser.add_argument("--backup-branch-id", help="Recent Neon child snapshot branch id for --apply.")
    parser.add_argument("--allow-credential-store-write", action="store_true",
                        help="Allow unique generated account passwords to be stored in Windows Credential Manager.")
    parser.add_argument(
        "--allow-demo-eligibility-policy", action="store_true",
        help=("For full mode only: append missing versioned eligibility policies using explicit, "
              "replaceable DH-05 synthetic assumptions. Never changes existing policy versions."),
    )
    parser.add_argument(
        "--allow-demo-lifecycle-records", action="store_true",
        help=("For full mode only: submit clearly labeled synthetic hours/evidence/evaluations and "
              "attempt completion using only persisted requirements. No completion threshold is created."),
    )
    args = parser.parse_args()

    write_attempted = False
    commit_state = {"transaction_started": False, "committed": False}
    try:
        store = WindowsCredentialStore()
        branches = _neon_branches()
        _verify_target_branch(branches)
        runtime_url = _credential_url(store, RUNTIME_CREDENTIAL)
        if args.allow_demo_eligibility_policy and args.mode != "full":
            raise RuntimeError("--allow-demo-eligibility-policy is available only with --mode full.")
        if args.allow_demo_lifecycle_records and args.mode != "full":
            raise RuntimeError("--allow-demo-lifecycle-records is available only with --mode full.")
        report = _inspect_database(
            runtime_url, set_application_role=True, mode=args.mode,
            allow_demo_eligibility_policy=args.allow_demo_eligibility_policy,
            allow_demo_lifecycle_records=args.allow_demo_lifecycle_records,
        )
        snapshot = _snapshot_summary(branches)
        report["snapshot"] = snapshot
        if not snapshot["recent_snapshot_available"]:
            report["blockers"].append("A separate child snapshot created in the last 24 hours is required.")
        bootstrap_target = BOOTSTRAP_CREDENTIAL if args.mode == "partial" else FULL_BOOTSTRAP_CREDENTIAL
        expected_role = BOOTSTRAP_ROLE if args.mode == "partial" else FULL_BOOTSTRAP_ROLE
        bootstrap_url = store.read(bootstrap_target)
        report["bootstrap_credential_available"] = bootstrap_url is not None
        if bootstrap_url is None:
            report["blockers"].append(f"The dedicated {expected_role} credential is not present in Credential Manager.")
        else:
            bootstrap_report = _inspect_bootstrap(
                bootstrap_url, mode=args.mode,
                allow_demo_eligibility_policy=args.allow_demo_eligibility_policy,
            )
            report["bootstrap"] = bootstrap_report
            report["blockers"].extend(bootstrap_report["blockers"])
        missing_account_passwords = 0
        new_account_count = report["planned_insertions"].get("user_account", 0)
        # Use only usernames absent in the read-only database preflight. Values stay
        # in Windows Credential Manager and are never logged or included in the report.
        missing_users = report.pop("_missing_account_usernames", [])
        known_password_fingerprints: dict[str, bytes] = {}
        for username in missing_users:
            target = f"{PASSWORD_TARGET_PREFIX}/{username}/PASSWORD"
            value = store.read(target)
            if value is None:
                missing_account_passwords += 1
            else:
                known_password_fingerprints[target] = hashlib.sha256(value.encode("utf-8")).digest()
        # Also check already-stored fixture passwords for reuse without revealing
        # the values. The script rejects duplicates before creating any accounts.
        all_fingerprints = []
        for username in sorted(EXPECTED_USERS):
            target = f"{PASSWORD_TARGET_PREFIX}/{username}/PASSWORD"
            value = store.read(target)
            if value is not None:
                fingerprint = hashlib.sha256(value.encode("utf-8")).digest()
                all_fingerprints.append(fingerprint)
                known_password_fingerprints.setdefault(target, fingerprint)
        duplicate_password_items = len(all_fingerprints) - len(set(all_fingerprints))
        if duplicate_password_items:
            report["blockers"].append(
                "Stored synthetic account credentials contain duplicates; no database or credential changes were made."
            )
        report["account_credentials"] = {
            "new_account_count": new_account_count,
            "missing_unique_password_count": missing_account_passwords,
            "duplicate_password_items": duplicate_password_items,
            "credential_store_write_authorized": args.allow_credential_store_write,
        }
        report["write_performed"] = False
        if args.apply and missing_account_passwords and not args.allow_credential_store_write:
            report["blockers"].append(
                "Missing account passwords require explicit --allow-credential-store-write; no credential was changed."
            )
        report["write_performed"] = False
        _print_report(report)
        if not args.apply:
            return 0 if not report["blockers"] else 2
        if args.confirm_target != f"{PROJECT_ID}/{BRANCH_NAME}":
            raise RuntimeError("Apply requires --confirm-target long-truth-39527618/main.")
        if not args.backup_branch_id:
            raise RuntimeError("Apply requires a Neon snapshot branch created within the last 24 hours.")
        backup = _verify_recent_backup(branches, args.backup_branch_id)
        _assert_no_blockers(report)
        action_label = "FULL"
        if args.mode == "full" and args.allow_demo_eligibility_policy:
            action_label += " WITH LABELED DEMO ELIGIBILITY POLICIES"
        if args.mode == "full" and args.allow_demo_lifecycle_records:
            action_label += " AND LABELED DEMO LIFECYCLE RECORDS"
        expected_phrase = f"PERSIST SYN-01 {action_label} TO {PROJECT_ID}/{BRANCH_NAME}"
        if input(f"Type {expected_phrase} to continue: ").strip() != expected_phrase:
            print("Cancelled; no database write was performed.")
            return 3
        write_attempted = True
        result = _active_transaction_load(
            bootstrap_url, runtime_url, store, commit_state, mode=args.mode,
            allow_credential_store_write=args.allow_credential_store_write,
            allow_demo_eligibility_policy=args.allow_demo_eligibility_policy,
            allow_demo_lifecycle_records=args.allow_demo_lifecycle_records,
            known_password_fingerprints=known_password_fingerprints,
        )
        result["backup"] = {"verified": True, "branch_id": backup["id"],
                            "created_at": backup.get("created_at")}
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
