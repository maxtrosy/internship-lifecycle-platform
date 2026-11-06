"""C-01 local account authentication, sessions, password recovery and invitations."""
from __future__ import annotations

import datetime as dt
import re

import psycopg

from app import security
from app.config import get_settings
from app.db import CommandContext
from app.errors import BusinessError, Forbidden, NotFound, Unauthorized
from app.modules.audit import service as audit_service
from app.modules.authz import service as authz

_USERNAME = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")


def normalize_identifier(identifier: str) -> str:
    return identifier.strip().casefold()


def validate_username(username: str) -> str:
    value = username.strip().casefold()
    if not _USERNAME.fullmatch(value):
        raise BusinessError("INVALID_USERNAME", "Use 3–64 letters, digits, dots, underscores or hyphens.")
    return value


def account_for_login(cur: psycopg.Cursor, identifier: str) -> dict | None:
    normalized = normalize_identifier(identifier)
    if not normalized:
        return None
    return cur.execute(
        """SELECT id, username, email, password_hash, is_active
           FROM user_account
           WHERE lower(username)=%s OR lower(email)=%s
           LIMIT 1""",
        (normalized, normalized),
    ).fetchone()


def verify_login(account: dict | None, password: str) -> int:
    stored_hash = account["password_hash"] if account else None
    valid = security.verify_password(password, stored_hash)
    if account is None or not account["is_active"] or not valid:
        raise Unauthorized()
    return account["id"]


def create_session(ctx: CommandContext, user_id: int,
                   action: str = "auth.login.succeeded") -> str:
    session_id = security.new_session_id()
    settings = get_settings()
    expires_at = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=settings.jwt_ttl_minutes)
    ctx.execute(
        """DELETE FROM auth_session
           WHERE expires_at < now() OR revoked_at < now() - interval '30 days'"""
    )
    ctx.execute(
        "INSERT INTO auth_session(jti,user_id,expires_at) VALUES (%s,%s,%s)",
        (session_id, user_id, expires_at),
    )
    audit_service.write(ctx.cur, action, "user_account", user_id,
                        None, {"session_expires_at": expires_at.isoformat()})
    return security.issue_token(user_id, session_id)


def revoke_session(ctx: CommandContext, user_id: int, session_id: str) -> None:
    cur = ctx.execute(
        """UPDATE auth_session SET revoked_at=now()
           WHERE jti=%s AND user_id=%s AND revoked_at IS NULL RETURNING jti""",
        (session_id, user_id),
    )
    if cur.fetchone() is not None:
        audit_service.write(ctx.cur, "auth.logout", "user_account", user_id,
                            None, {"session_revoked": True})


def me(cur: psycopg.Cursor, user_id: int) -> dict:
    subj = authz.subject(cur, user_id)
    if subj is None or not subj["is_active"]:
        raise Unauthorized()
    return {
        "id": subj["id"],
        "username": subj["username"],
        "display_name": subj["display_name"],
        "email": subj["email"],
        "roles": [
            {"role": r["role"], "program_id": r["program_id"], "host_org_id": r["host_org_id"]}
            for r in subj["roles"]
        ],
    }


def _is_experiential_coordinator(ctx: CommandContext) -> bool:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    return bool(subj and any(r["role"] == "EXPERIENTIAL_COORDINATOR" for r in subj["roles"]))


def create_invitation(ctx: CommandContext, email: str, host_org_id: int, role: str,
                      ttl_days: int = 7) -> str:
    if role not in ("HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR"):
        raise BusinessError("INVALID_ROLE", role)
    if not _is_experiential_coordinator(ctx):
        raise Forbidden("only EXPERIENTIAL_COORDINATOR may create invitations")
    normalized_email = email.strip().casefold()
    token = security.new_invitation_token()
    ctx.execute(
        """INSERT INTO invitation(email, host_org_id, role, token_hash, created_by, expires_at)
           VALUES (%s, %s, %s, %s, %s, now() + make_interval(days => %s))""",
        (normalized_email, host_org_id, role, security.hash_invitation_token(token), ctx.actor_id, ttl_days),
    )
    audit_service.write(ctx.cur, "invitation.created", "invitation",
                        _last_invitation_id(ctx), None, {"email": normalized_email, "role": role})
    return token


def _last_invitation_id(ctx: CommandContext) -> int:
    return ctx.execute("SELECT currval(pg_get_serial_sequence('invitation','id')) AS id").fetchone()["id"]


def accept_invitation(ctx: CommandContext, token: str, display_name: str,
                      username: str, password: str) -> tuple[int, str]:
    h = security.hash_invitation_token(token)
    row = ctx.execute("SELECT * FROM invitation WHERE token_hash=%s FOR UPDATE", (h,)).fetchone()
    if row is None:
        raise NotFound()
    if row["accepted_at"] is not None:
        raise BusinessError("INVITATION_USED")
    if row["expires_at"] < dt.datetime.now(dt.timezone.utc):
        raise BusinessError("INVITATION_EXPIRED")
    if ctx.execute("SELECT 1 FROM user_account WHERE lower(email)=%s", (row["email"].casefold(),)).fetchone():
        raise BusinessError("INVITATION_ACCOUNT_EXISTS")
    login_name = validate_username(username)
    if ctx.execute("SELECT 1 FROM user_account WHERE lower(username)=%s", (login_name,)).fetchone():
        raise BusinessError("USERNAME_UNAVAILABLE")
    password_hash = security.hash_password(password)
    user = ctx.execute(
        """INSERT INTO user_account(username,email,password_hash,is_active,display_name)
           VALUES (%s,%s,%s,true,%s) RETURNING id""",
        (login_name, row["email"], password_hash, display_name.strip()),
    ).fetchone()
    ctx.execute("INSERT INTO role_assignment(user_id, role, host_org_id) VALUES (%s, %s, %s)",
                (user["id"], row["role"], row["host_org_id"]))
    ctx.execute("UPDATE invitation SET accepted_at=now() WHERE id=%s", (row["id"],))
    audit_service.write(ctx.cur, "invitation.accepted", "invitation", row["id"],
                        None, {"user_id": user["id"]})
    return user["id"], create_session(ctx, user["id"], "auth.invitation.accepted")


def create_password_reset(ctx: CommandContext, email: str) -> str | None:
    normalized_email = email.strip().casefold()
    row = ctx.execute(
        "SELECT id FROM user_account WHERE lower(email)=%s AND is_active=true",
        (normalized_email,),
    ).fetchone()
    if row is None:
        return None
    token = security.new_password_reset_token()
    ctx.execute("UPDATE auth_password_reset SET used_at=now() WHERE user_id=%s AND used_at IS NULL",
                (row["id"],))
    ctx.execute(
        """INSERT INTO auth_password_reset(token_hash,user_id,expires_at)
           VALUES (%s,%s,now() + interval '30 minutes')""",
        (security.hash_password_reset_token(token), row["id"]),
    )
    audit_service.write(ctx.cur, "auth.password_reset.requested", "user_account", row["id"],
                        None, {"delivery_mode": "development_or_configured_adapter"})
    return token


def password_reset_owner(cur: psycopg.Cursor, token: str) -> int | None:
    row = cur.execute(
        """SELECT r.user_id FROM auth_password_reset r JOIN user_account u ON u.id=r.user_id
           WHERE r.token_hash=%s AND r.used_at IS NULL AND r.expires_at>now() AND u.is_active=true""",
        (security.hash_password_reset_token(token),),
    ).fetchone()
    return row["user_id"] if row else None


def reset_password(ctx: CommandContext, token: str, password: str, user_id: int) -> None:
    token_hash = security.hash_password_reset_token(token)
    row = ctx.execute(
        """SELECT user_id,expires_at,used_at FROM auth_password_reset
           WHERE token_hash=%s FOR UPDATE""",
        (token_hash,),
    ).fetchone()
    if (row is None or row["user_id"] != user_id or row["used_at"] is not None
            or row["expires_at"] <= dt.datetime.now(dt.timezone.utc)):
        raise BusinessError("PASSWORD_RESET_INVALID")
    password_hash = security.hash_password(password)
    ctx.execute("UPDATE user_account SET password_hash=%s WHERE id=%s AND is_active=true",
                (password_hash, user_id))
    ctx.execute("UPDATE auth_password_reset SET used_at=now() WHERE token_hash=%s", (token_hash,))
    ctx.execute("UPDATE auth_session SET revoked_at=now() WHERE user_id=%s AND revoked_at IS NULL",
                (user_id,))
    audit_service.write(ctx.cur, "auth.password_reset.completed", "user_account", user_id,
                        None, {"sessions_revoked": True})
