from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.contexts.applications_eligibility.application.use_cases import (
    EmployerAcceptCandidate,
    SubmitApplication,
    ValidateEligibility,
)
from src.db import get_session
from src.shared.auth import Action, Principal, ResourceRelation, get_current_principal, is_authorized

router = APIRouter()


class SubmitApplicationRequest(BaseModel):
    student_id: UUID
    opportunity_id: UUID


@router.post("/")
def submit_application(
    request: SubmitApplicationRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not is_authorized(principal, Action.APPLY, ResourceRelation(student_id=request.student_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        application = SubmitApplication(session).execute(request.student_id, request.opportunity_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"id": str(application.id), "status": application.status.value}


class ValidateEligibilityRequest(BaseModel):
    program_coordinator_id: UUID
    evaluated_criteria: dict = Field(default_factory=dict)


@router.post("/{application_id}/eligibility/approve")
def approve_eligibility(
    application_id: UUID,
    request: ValidateEligibilityRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    relation = ResourceRelation(program_coordinator_id=request.program_coordinator_id)
    if not is_authorized(principal, Action.VALIDATE_ELIGIBILITY, relation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        application = ValidateEligibility(session).approve(
            application_id=application_id,
            evaluator_id=request.program_coordinator_id,
            evaluated_criteria=request.evaluated_criteria,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"status": application.status.value}


class EmployerAcceptRequest(BaseModel):
    host_org_rep_id: UUID
    host_org_id: UUID
    workplace_supervisor_id: UUID
    faculty_supervisor_id: UUID
    program_coordinator_id: UUID
    start_date: date
    end_date: date


@router.post("/{application_id}/employer/accept")
def employer_accept_candidate(
    application_id: UUID,
    request: EmployerAcceptRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    relation = ResourceRelation(host_org_rep_id=request.host_org_rep_id)
    if not is_authorized(principal, Action.SELECT_OR_REJECT_CANDIDATE, relation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        placement = EmployerAcceptCandidate(session).execute(
            application_id=application_id,
            host_org_id=request.host_org_id,
            workplace_supervisor_id=request.workplace_supervisor_id,
            faculty_supervisor_id=request.faculty_supervisor_id,
            program_coordinator_id=request.program_coordinator_id,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"id": str(placement.id), "status": placement.status.value}
