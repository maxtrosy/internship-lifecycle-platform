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


@router.post("/opportunities", status_code=201)
def create_opportunity(body: OpportunityBody,
                       subject_id: int = Depends(requires("opportunity:create"))) -> dict:
    with db.command(subject_id) as ctx:
        oid = opportunities.create_opportunity(ctx, body.host_org_id, body.program_id, body.title)
    return {"id": oid}
