"""HTTP endpoints for identity (login, me, invitations)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import db, security
from app.deps import requires
from app.modules.identity import service as identity

router = APIRouter()


class LoginBody(BaseModel):
    user_id: int


class InvitationBody(BaseModel):
    email: str
    host_org_id: int
    role: str


class AcceptInvitationBody(BaseModel):
    token: str
    display_name: str


@router.post("/auth/login")
def login(body: LoginBody) -> dict:
    with db.read() as cur:
        token = identity.login(cur, body.user_id)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/auth/me")
def me(subject_id: int = Depends(requires("identity:read"))) -> dict:
    with db.read() as cur:
        return identity.me(cur, subject_id)


@router.post("/invitations")
def create_invitation(body: InvitationBody,
                      subject_id: int = Depends(requires("invitation:create"))) -> dict:
    with db.command(subject_id) as ctx:
        token = identity.create_invitation(ctx, body.email, body.host_org_id, body.role)
    return {"token": token}


@router.post("/auth/accept-invitation")
def accept_invitation(body: AcceptInvitationBody) -> dict:
    with db.command(None) as ctx:
        user_id = identity.accept_invitation(ctx, body.token, body.display_name)
    return {"user_id": user_id, "access_token": security.issue_token(user_id)}
