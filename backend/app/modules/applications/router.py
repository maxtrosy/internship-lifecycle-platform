"""HTTP endpoints for applications (C-04)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app import db
from app.deps import requires
from app.modules import authz
from app.modules.applications import service as applications

router = APIRouter()


@router.get("/applications")
def list_my_applications(subject_id: int = Depends(requires("application:list"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return applications.list_my_applications(cur, subj)


@router.post("/opportunities/{oid}/apply", status_code=201)
def apply(oid: int, subject_id: int = Depends(requires("application:create"))) -> dict:
    with db.command(subject_id) as ctx:
        return applications.submit_application(ctx, oid)
