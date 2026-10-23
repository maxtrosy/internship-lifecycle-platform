"""DH-05 backend entry point (Phase 1)."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import BusinessError, DomainError, Forbidden, NotFound
from app.modules.identity import router as identity_router
from app.modules.lifecycle import router as lifecycle_router

app = FastAPI(title="DH-05 Placement API", version="0.1.0")

app.include_router(identity_router)
app.include_router(lifecycle_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    if isinstance(exc, NotFound):
        body = {"error": "not_found"}
    elif isinstance(exc, Forbidden):
        body = {"error": "forbidden"}
    elif isinstance(exc, BusinessError):
        body = {"error": exc.code, "detail": exc.detail}
    else:
        body = {"error": str(exc)}
    return JSONResponse(status_code=exc.status, content=body)
