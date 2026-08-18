from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.contexts.placements.application.use_cases import TransitionPlacement
from src.db import get_session
from src.shared.auth import Action, Principal, ResourceRelation, get_current_principal, is_authorized

router = APIRouter()


class TransitionPlacementRequest(BaseModel):
    transition: str


@router.post("/{placement_id}/transitions")
def transition_placement(
    placement_id: UUID,
    request: TransitionPlacementRequest,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if request.transition == "approve_academically":
        return approve_academic_placement(placement_id, principal, session)
    if request.transition == "mark_ready_to_activate":
        return mark_ready_to_activate(placement_id, principal, session)
    if request.transition == "activate":
        return activate_placement(placement_id, principal, session)
    raise NotImplementedError


@router.post("/{placement_id}/academic-approval")
def approve_academic_placement(
    placement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    placement = session.get(TransitionPlacement(session)._get_placement(placement_id).__class__, placement_id)
    if placement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Placement not found.")
    relation = ResourceRelation(program_coordinator_id=placement.program_coordinator_id)
    if not is_authorized(principal, Action.APPROVE_ACADEMIC_ADJUSTMENT, relation):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        placement = TransitionPlacement(session).approve_academically(placement_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"status": placement.status.value}


@router.post("/{placement_id}/ready-to-activate")
def mark_ready_to_activate(
    placement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not is_authorized(principal, Action.ACTIVATE_PLACEMENT, ResourceRelation()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        placement = TransitionPlacement(session).mark_ready_to_activate(placement_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"status": placement.status.value}


@router.post("/{placement_id}/activate")
def activate_placement(
    placement_id: UUID,
    principal: Principal = Depends(get_current_principal),
    session: Session = Depends(get_session),
) -> dict[str, str]:
    if not is_authorized(principal, Action.ACTIVATE_PLACEMENT, ResourceRelation()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    try:
        placement = TransitionPlacement(session).activate(placement_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"status": placement.status.value}
        raise NotImplementedError

    try:
        placement = TransitionPlacement(session).mark_ready_to_activate(
            placement_id=placement_id,
            employer_selection_confirmed=request.employer_selection_confirmed,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    session.commit()
    return {"status": placement.status.value}
