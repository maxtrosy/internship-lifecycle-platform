from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from src.contexts.agreements.domain.models import (
    DocumentChecklist,
    DocumentRequirement,
    DocumentReviewStatus,
    DocumentStatus,
)


class DocumentChecklistRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def mandatory_documents_complete_for_placement(self, placement_id: UUID) -> bool:
        checklist_id = self.session.scalar(
            select(DocumentChecklist.id).where(DocumentChecklist.placement_id == placement_id)
        )
        if checklist_id is None:
            return False

        missing_approved_status = (
            select(DocumentRequirement.id)
            .where(DocumentRequirement.checklist_id == checklist_id)
            .where(DocumentRequirement.required.is_(True))
            .where(
                ~exists().where(
                    (DocumentStatus.requirement_id == DocumentRequirement.id)
                    & (DocumentStatus.status == DocumentReviewStatus.APPROVED)
                )
            )
            .limit(1)
        )
        return self.session.scalar(missing_approved_status) is None
