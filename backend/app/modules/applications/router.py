"""HTTP endpoints for applications (C-04)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import db
from app.deps import requires
from app.modules import authz
from app.modules.applications import service as applications

router = APIRouter()


class SelectBody(BaseModel):
    workplace_supervisor_id: int | None = None
    start_date: date
    end_date: date
    location: str
    responsibilities: str


@router.get("/applications")
def list_my_applications(subject_id: int = Depends(requires("application:list"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return applications.list_my_applications(cur, subj)


@router.post("/opportunities/{oid}/apply", status_code=201)
def apply(oid: int, subject_id: int = Depends(requires("application:create"))) -> dict:
    with db.command(subject_id) as ctx:
        return applications.submit_application(ctx, oid)


@router.get("/opportunities/{oid}/applications")
def list_for_opportunity(oid: int, subject_id: int = Depends(requires("application:list"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return applications.list_for_opportunity(cur, subj, oid)


@router.post("/applications/{aid}/select", status_code=201)
def select(aid: int, body: SelectBody,
           subject_id: int = Depends(requires("application:select"))) -> dict:
    with db.command(subject_id) as ctx:
        pid = applications.select_application(ctx, aid, body.model_dump())
    return {"placement_id": pid}
