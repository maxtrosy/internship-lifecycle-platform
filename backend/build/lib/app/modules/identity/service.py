"""C-01 identity use cases: login, me, invitations (OPEN-21 proposal)."""
from __future__ import annotations

import datetime as dt

from app import security
from app.adapters.simulated_identity import identity_adapter
from app.db import CommandContext
from app.errors import BusinessError, Forbidden, NotFound
from app.modules.audit import service as audit_service
from app.modules.authz import service as authz


def login(cur, user_id: int) -> str:
    if not identity_adapter.authenticate(cur, user_id):
        raise Forbidden("unknown subject")
    return security.issue_token(user_id)


def me(cur, user_id: int) -> dict:
    subj = authz.subject(cur, user_id)
    if subj is None:
        raise NotFound()
    return {
        "id": subj["id"],
        "display_name": subj["display_name"],
        "email": subj["email"],
        "roles": [
            {"role": r["role"], "program_id": r["program_id"], "host_org_id": r["host_org_id"]}
            for r in subj["roles"]
        ],
    }


def _is_experiential_coordinator(ctx: CommandContext) -> bool:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    return any(r["role"] == "EXPERIENTIAL_COORDINATOR" for r in subj["roles"])


def create_invitation(ctx: CommandContext, email: str, host_org_id: int, role: str,
                      ttl_days: int = 7) -> str:
    if role not in ("HOST_ORG_MEMBER", "WORKPLACE_SUPERVISOR"):
        raise BusinessError("INVALID_ROLE", role)
    if not _is_experiential_coordinator(ctx):
        raise Forbidden("only EXPERIENTIAL_COORDINATOR may create invitations")
    token = security.new_invitation_token()
    ctx.execute(
        """INSERT INTO invitation(email, host_org_id, role, token_hash, created_by, expires_at)
           VALUES (%s, %s, %s, %s, %s, now() + make_interval(days => %s))""",
        (email, host_org_id, role, security.hash_invitation_token(token), ctx.actor_id, ttl_days),
    )
    audit_service.write(ctx.cur, "invitation.created", "invitation",
                        _last_invitation_id(ctx), None, {"email": email, "role": role})
    return token


def _last_invitation_id(ctx: CommandContext) -> int:
    return ctx.execute("SELECT currval(pg_get_serial_sequence('invitation','id')) AS id").fetchone()["id"]


def accept_invitation(ctx: CommandContext, token: str, display_name: str) -> int:
    h = security.hash_invitation_token(token)
    row = ctx.execute("SELECT * FROM invitation WHERE token_hash=%s FOR UPDATE", (h,)).fetchone()
    if row is None:
        raise NotFound()
    if row["accepted_at"] is not None:
        raise BusinessError("INVITATION_USED")
    if row["expires_at"] < dt.datetime.now(dt.timezone.utc):
        raise BusinessError("INVITATION_EXPIRED")
    user = ctx.execute(
        "INSERT INTO user_account(email, display_name) VALUES (%s, %s) RETURNING id",
        (row["email"], display_name),
    ).fetchone()
    ctx.execute("INSERT INTO role_assignment(user_id, role, host_org_id) VALUES (%s, %s, %s)",
                (user["id"], row["role"], row["host_org_id"]))
    ctx.execute("UPDATE invitation SET accepted_at=now() WHERE id=%s", (row["id"],))
    audit_service.write(ctx.cur, "invitation.accepted", "invitation", row["id"],
                        None, {"user_id": user["id"]})
    return user["id"]
