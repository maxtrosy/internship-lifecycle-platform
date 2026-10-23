"""HTTP endpoints for local account authentication and invitations."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app import db, security
from app.config import get_settings
from app.deps import requires
from app.errors import BusinessError, Unauthorized
from app.modules.identity import service as identity
from app.modules.identity.password_reset_delivery import get_password_reset_delivery
from app.modules.identity.rate_limit import login_rate_limiter, reset_rate_limiter

router = APIRouter()


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(StrictBody):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class InvitationBody(StrictBody):
    email: str = Field(min_length=3, max_length=254)
    host_org_id: int
    role: str


class AcceptInvitationBody(StrictBody):
    token: str = Field(min_length=20, max_length=256)
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=security.PASSWORD_MIN_LENGTH, max_length=1024)


class PasswordResetRequestBody(StrictBody):
    email: str = Field(min_length=3, max_length=254)


class PasswordResetBody(StrictBody):
    token: str = Field(min_length=20, max_length=256)
    password: str = Field(min_length=security.PASSWORD_MIN_LENGTH, max_length=1024)


def _check_origin(request: Request) -> None:
    origin = request.headers.get("origin", "").rstrip("/")
    if origin not in get_settings().allowed_origins:
        from app.errors import Forbidden

        raise Forbidden("untrusted origin")


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        security.SESSION_COOKIE,
        token,
        max_age=settings.jwt_ttl_minutes * 60,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="strict",
        path="/",
    )


def _delete_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        security.SESSION_COOKIE,
        path="/",
        secure=settings.app_env == "production",
        httponly=True,
        samesite="strict",
    )


def _remote_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/auth/login")
def login(body: LoginBody, request: Request, response: Response) -> dict:
    _check_origin(request)
    identifier = identity.normalize_identifier(body.identifier)
    ip_address = _remote_ip(request)
    login_rate_limiter.check("login", identifier, ip_address)
    with db.read() as cur:
        account = identity.account_for_login(cur, identifier)
    try:
        user_id = identity.verify_login(account, body.password)
    except Unauthorized:
        login_rate_limiter.failed("login", identifier, ip_address)
        raise
    login_rate_limiter.succeeded("login", identifier)
    with db.command(user_id) as ctx:
        token = identity.create_session(ctx, user_id)
    _set_session_cookie(response, token)
    return {"authenticated": True}


@router.get("/auth/me")
def me(subject_id: int = Depends(requires("identity:read"))) -> dict:
    with db.read() as cur:
        return identity.me(cur, subject_id)


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response,
           subject_id: int = Depends(requires("identity:logout"))) -> Response:
    with db.command(subject_id) as ctx:
        identity.revoke_session(ctx, subject_id, request.state.auth_session_id)
    _delete_session_cookie(response)
    response.status_code = 204
    return response


@router.post("/auth/password-reset/request")
def request_password_reset(body: PasswordResetRequestBody, request: Request) -> dict:
    _check_origin(request)
    email = body.email.strip().casefold()
    ip_address = _remote_ip(request)
    reset_rate_limiter.check("password-reset", email, ip_address)
    settings = get_settings()
    message = (
        "La solicitud fue recibida. Esta instalación solo puede entregar recuperación "
        "si tiene un canal de correo configurado."
    )
    if settings.password_reset_delivery == "disabled":
        reset_rate_limiter.record("password-reset", email, ip_address)
        return {"message": message}

    with db.read() as cur:
        account = cur.execute(
            "SELECT id FROM user_account WHERE lower(email)=%s AND is_active=true",
            (email,),
        ).fetchone()
    if not account:
        reset_rate_limiter.record("password-reset", email, ip_address)
        return {"message": message}
    with db.command(account["id"]) as ctx:
        token = identity.create_password_reset(ctx, email)
    reset_rate_limiter.record("password-reset", email, ip_address)
    if token is None:
        return {"message": message}
    delivery = get_password_reset_delivery(settings).deliver(email, token)
    return {"message": message, **(delivery or {})}


@router.post("/auth/password-reset/complete")
def complete_password_reset(body: PasswordResetBody, response: Response) -> dict:
    with db.read() as cur:
        user_id = identity.password_reset_owner(cur, body.token)
    if user_id is None:
        raise HTTPException(status_code=400, detail="El enlace es inválido o venció.")
    with db.command(user_id) as ctx:
        try:
            identity.reset_password(ctx, body.token, body.password, user_id)
        except BusinessError as exc:
            # Do not expose token state or account details if a concurrent request consumed it.
            raise HTTPException(status_code=400, detail="El enlace es inválido o venció.") from exc
    _delete_session_cookie(response)
    return {"password_updated": True}


@router.post("/invitations")
def create_invitation(body: InvitationBody,
                      subject_id: int = Depends(requires("invitation:create"))) -> dict:
    with db.command(subject_id) as ctx:
        token = identity.create_invitation(ctx, body.email, body.host_org_id, body.role)
    return {"token": token}


@router.post("/auth/accept-invitation")
def accept_invitation(body: AcceptInvitationBody, request: Request, response: Response) -> dict:
    _check_origin(request)
    with db.command(None) as ctx:
        _, token = identity.accept_invitation(
            ctx, body.token, body.display_name, body.username, body.password
        )
    _set_session_cookie(response, token)
    return {"authenticated": True}
