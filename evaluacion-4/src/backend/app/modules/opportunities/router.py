"""HTTP endpoints for opportunities (C-03)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import db
from app.deps import requires
from app.modules import authz
from app.modules.opportunities import service as opportunities

router = APIRouter()


class OpportunityBody(BaseModel):
    host_org_id: int
    program_id: int
    title: str


@router.get("/opportunities")
def list_opportunities(subject_id: int = Depends(requires("opportunity:list"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return opportunities.list_opportunities(cur, subj)


@router.get("/opportunities/catalogs")
def list_creation_catalogs(subject_id: int = Depends(requires("opportunity:create"))) -> dict:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return opportunities.list_creation_catalogs(cur, subj)


@router.get("/opportunities/{oid}/workplace-supervisors")
def list_workplace_supervisors(oid: int,
                               subject_id: int = Depends(requires("application:select"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return opportunities.list_workplace_supervisors(cur, subj, oid)


@router.post("/opportunities", status_code=201)
def create_opportunity(body: OpportunityBody,
                       subject_id: int = Depends(requires("opportunity:create"))) -> dict:
    with db.command(subject_id) as ctx:
        oid = opportunities.create_opportunity(ctx, body.host_org_id, body.program_id, body.title)
    return {"id": oid, "state": "DRAFT"}


@router.post("/opportunities/{oid}/submit-review", status_code=204)
def submit_for_review(oid: int, subject_id: int = Depends(requires("opportunity:transition"))) -> None:
    with db.command(subject_id) as ctx:
        opportunities.submit_for_review(ctx, oid)


@router.post("/opportunities/{oid}/approve", status_code=204)
def approve_for_publication(oid: int, subject_id: int = Depends(requires("opportunity:transition"))) -> None:
    with db.command(subject_id) as ctx:
        opportunities.approve_for_publication(ctx, oid)


@router.post("/opportunities/{oid}/publish", status_code=204)
def publish_opportunity(oid: int, subject_id: int = Depends(requires("opportunity:transition"))) -> None:
    with db.command(subject_id) as ctx:
        opportunities.publish_opportunity(ctx, oid)


@router.post("/opportunities/{oid}/close", status_code=204)
def close_opportunity(oid: int, subject_id: int = Depends(requires("opportunity:transition"))) -> None:
    with db.command(subject_id) as ctx:
        opportunities.close_opportunity(ctx, oid)
