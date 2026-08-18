from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.contexts.agreements.application.use_cases import ReviewDocument, SubmitDocument
from src.contexts.agreements.domain.models import DocumentRequirementType
from src.db import get_session
from src.shared.auth import Action, Principal, ResourceRelation, get_current_principal, is_authorized

router = APIRouter()


class SubmitDocumentRequest(BaseModel):
    student_id: UUID | None = None
    host_org_rep_id: UUID | None = None
    requirement_type: DocumentRequirementType
    required: bool = True


@router.post("/placements/{placement_id}/documents")
def submit_document(
    placement_id: UUID,
    request: SubmitDocumentRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    relation = ResourceRelation(student_id=request.student_id, host_org_rep_id=request.host_org_rep_id)
    if not is_authorized(principal, Action.UPLOAD_OR_REVIEW_DOCUMENTS, relation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    document_status = SubmitDocument(session).execute(
        placement_id=placement_id,
        requirement_type=request.requirement_type,
        required=request.required,
    )
    session.commit()
    return {"id": str(document_status.id), "status": document_status.status.value}


class ApproveDocumentRequest(BaseModel):
    student_id: UUID | None = None
    host_org_rep_id: UUID | None = None


@router.post("/documents/{document_status_id}/approve")
def approve_document(
    document_status_id: UUID,
    request: ApproveDocumentRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    relation = ResourceRelation(student_id=request.student_id, host_org_rep_id=request.host_org_rep_id)
    if not is_authorized(principal, Action.UPLOAD_OR_REVIEW_DOCUMENTS, relation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        document_status = ReviewDocument(session).approve(document_status_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    session.commit()
    return {"status": document_status.status.value}
