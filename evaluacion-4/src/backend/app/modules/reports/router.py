"""HTTP API for internal operational aggregates."""
from fastapi import APIRouter, Depends, Query

from app import db
from app.deps import requires
from app.modules import authz
from app.modules.reports import service

router = APIRouter()


@router.get("/reports/operations")
def operational_reports(
    program_id: int | None = Query(default=None, ge=1),
    organization_id: int | None = Query(default=None, ge=1),
    placement_state: str | None = Query(default=None, min_length=1, max_length=80),
    opportunity_state: str | None = Query(default=None, min_length=1, max_length=80),
    application_state: str | None = Query(default=None, min_length=1, max_length=80),
    subject_id: int = Depends(requires("reports:read")),
) -> dict:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return service.operations(cur, subj, program_id=program_id, organization_id=organization_id,
                                  placement_state=placement_state, opportunity_state=opportunity_state,
                                  application_state=application_state)
