from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.contexts.opportunities.application.use_cases import PublishOpportunity
from src.db import get_session
from src.shared.auth import Action, Principal, ResourceRelation, get_current_principal, is_authorized

router = APIRouter()


class PublishOpportunityRequest(BaseModel):
    host_org_rep_id: UUID | None = None


@router.post("/{opportunity_id}/publish")
def publish_opportunity(
    opportunity_id: UUID,
    request: PublishOpportunityRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    relation = ResourceRelation(host_org_rep_id=request.host_org_rep_id)
    if not is_authorized(principal, Action.PUBLISH_OPPORTUNITY, relation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        opportunity = PublishOpportunity(session).execute(opportunity_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"status": opportunity.status.value}
