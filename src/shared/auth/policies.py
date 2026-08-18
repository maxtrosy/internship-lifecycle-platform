from collections.abc import Callable
from enum import StrEnum
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from pydantic import BaseModel

from src.shared.auth.models import Role


class Action(StrEnum):
    PUBLISH_OPPORTUNITY = "Publicar oportunidad"
    APPLY = "Postular"
    VALIDATE_ELIGIBILITY = "Validar elegibilidad"
    SELECT_OR_REJECT_CANDIDATE = "Seleccionar/rechazar candidato"
    APPROVE_ACADEMIC_ADJUSTMENT = "Aprobar ajuste académico"
    UPLOAD_OR_REVIEW_DOCUMENTS = "Subir/revisar documentos"
    ACTIVATE_PLACEMENT = "Activar placement"
    REPORT_CHANGE_OR_INCIDENT = "Reportar cambio/incidente"
    SUBMIT_PROGRESS_OR_HOURS = "Enviar progreso/horas"
    SUBMIT_MIDTERM_OR_FINAL_EVALUATION = "Evaluación midterm/final"
    SUBMIT_FINAL_EVIDENCE = "Enviar evidencia final"
    CONFIRM_CLOSURE = "Confirmar cierre"
    VIEW_INSTITUTIONAL_REPORTS = "Ver reportes institucionales"


class Principal(BaseModel):
    user_id: UUID
    roles: set[Role]


class ResourceRelation(BaseModel):
    student_id: UUID | None = None
    host_org_rep_id: UUID | None = None
    workplace_supervisor_id: UUID | None = None
    faculty_supervisor_id: UUID | None = None
    program_coordinator_id: UUID | None = None


def get_current_principal(
    x_user_id: UUID = Header(..., alias="X-User-Id"),
    x_roles: str = Header(..., alias="X-Roles"),
) -> Principal:
    roles = {Role(role.strip()) for role in x_roles.split(",") if role.strip()}
    return Principal(user_id=x_user_id, roles=roles)


def is_authorized(principal: Principal, action: Action, relation: ResourceRelation) -> bool:
    roles = principal.roles
    user_id = principal.user_id

    if Role.IT_ADMIN in roles:
        return True
    if action == Action.PUBLISH_OPPORTUNITY:
        return Role.EXPERIENTIAL_COORDINATOR in roles or (
            Role.HOST_ORG_REP in roles and relation.host_org_rep_id == user_id
        )
    if action == Action.APPLY:
        return Role.STUDENT in roles and relation.student_id == user_id
    if action in {Action.VALIDATE_ELIGIBILITY, Action.APPROVE_ACADEMIC_ADJUSTMENT}:
        return Role.PROGRAM_COORDINATOR in roles and relation.program_coordinator_id == user_id
    if action == Action.SELECT_OR_REJECT_CANDIDATE:
        return Role.HOST_ORG_REP in roles and relation.host_org_rep_id == user_id
    if action == Action.UPLOAD_OR_REVIEW_DOCUMENTS:
        return (
            (Role.STUDENT in roles and relation.student_id == user_id)
            or (Role.HOST_ORG_REP in roles and relation.host_org_rep_id == user_id)
            or Role.EXPERIENTIAL_COORDINATOR in roles
            or Role.LEGAL_REP in roles
        )
    if action == Action.ACTIVATE_PLACEMENT:
        return Role.EXPERIENTIAL_COORDINATOR in roles
    if action == Action.REPORT_CHANGE_OR_INCIDENT:
        return (
            (Role.STUDENT in roles and relation.student_id == user_id)
            or (Role.HOST_ORG_REP in roles and relation.host_org_rep_id == user_id)
            or (Role.WORKPLACE_SUPERVISOR in roles and relation.workplace_supervisor_id == user_id)
            or (Role.FACULTY_SUPERVISOR in roles and relation.faculty_supervisor_id == user_id)
            or Role.EXPERIENTIAL_COORDINATOR in roles
        )
    if action == Action.SUBMIT_PROGRESS_OR_HOURS:
        return (Role.STUDENT in roles and relation.student_id == user_id) or (
            Role.WORKPLACE_SUPERVISOR in roles and relation.workplace_supervisor_id == user_id
        )
    if action == Action.SUBMIT_MIDTERM_OR_FINAL_EVALUATION:
        return (Role.WORKPLACE_SUPERVISOR in roles and relation.workplace_supervisor_id == user_id) or (
            Role.FACULTY_SUPERVISOR in roles and relation.faculty_supervisor_id == user_id
        )
    if action == Action.SUBMIT_FINAL_EVIDENCE:
        return Role.STUDENT in roles and relation.student_id == user_id
    if action == Action.CONFIRM_CLOSURE:
        return (Role.FACULTY_SUPERVISOR in roles and relation.faculty_supervisor_id == user_id) or (
            Role.PROGRAM_COORDINATOR in roles and relation.program_coordinator_id == user_id
        )
    if action == Action.VIEW_INSTITUTIONAL_REPORTS:
        return bool(
            roles
            & {
                Role.FACULTY_SUPERVISOR,
                Role.PROGRAM_COORDINATOR,
                Role.EXPERIENTIAL_COORDINATOR,
            }
        )
    return False


def require_permission(
    action: Action,
    relation_loader: Callable[..., ResourceRelation],
) -> Callable[..., Principal]:
    def dependency(principal: Principal = Depends(get_current_principal), relation: ResourceRelation = Depends(relation_loader)) -> Principal:
        if not is_authorized(principal, action, relation):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return principal

    return dependency
