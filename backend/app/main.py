"""DH-05 backend entry point (Phase 1)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.errors import BusinessError, DomainError, Forbidden, NotFound, TooManyRequests, Unauthorized
from app.modules.applications.router import router as applications_router
from app.modules.identity.router import router as identity_router
from app.modules.lifecycle.router import router as lifecycle_router
from app.modules.opportunities.router import router as opportunities_router
from app.modules.policies.router import router as policies_router

app = FastAPI(title="DH-05 Placement API", version="0.1.0")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(identity_router)
app.include_router(lifecycle_router)
app.include_router(opportunities_router)
app.include_router(applications_router)
app.include_router(policies_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    if isinstance(exc, Unauthorized):
        body = {"error": "unauthorized"}
    elif isinstance(exc, TooManyRequests):
        body = {"error": "too_many_requests"}
    elif isinstance(exc, NotFound):
        body = {"error": "not_found"}
    elif isinstance(exc, Forbidden):
        body = {"error": "forbidden"}
    elif isinstance(exc, BusinessError):
        body = {"error": exc.code, "detail": exc.detail}
    else:
        body = {"error": str(exc)}
    return JSONResponse(status_code=exc.status, content=body)
