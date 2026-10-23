"""HTTP endpoints for policy versions (C-05)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import db
from app.deps import requires
from app.modules.policies import service as policies

router = APIRouter()


class PolicyBody(BaseModel):
    program_code: str
    conditions: list[dict]
    kind: str = "ELIGIBILITY"


@router.get("/policies")
def list_policies(subject_id: int = Depends(requires("policy:list"))) -> list[dict]:
    from app.modules import authz

    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return policies.policies_for_subject(cur, subj)


@router.post("/policies", status_code=201)
def create_policy(body: PolicyBody,
                  subject_id: int = Depends(requires("policy:create"))) -> dict:
    with db.command(subject_id) as ctx:
        pv = policies.create_policy_version(ctx, body.program_code, body.conditions, body.kind)
    return {"id": pv}
