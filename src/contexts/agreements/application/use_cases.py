from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.contexts.agreements.domain.models import (
    DocumentChecklist,
    DocumentRequirement,
    DocumentRequirementType,
    DocumentReviewStatus,
    DocumentStatus,
)
from src.shared.events import DomainEventName, EventEnvelope, InProcessEventBus


class SubmitDocument:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = InProcessEventBus(session)

    def execute(self, placement_id: UUID, requirement_type: DocumentRequirementType, required: bool) -> DocumentStatus:
        checklist = self.session.scalar(
            select(DocumentChecklist).where(DocumentChecklist.placement_id == placement_id)
        )
        if checklist is None:
            checklist = DocumentChecklist(placement_id=placement_id)
            self.session.add(checklist)
            self.session.flush()

        requirement = DocumentRequirement(
            checklist_id=checklist.id,
            requirement_type=requirement_type,
            required=required,
        )
        self.session.add(requirement)
        self.session.flush()

        status = DocumentStatus(
            checklist_id=checklist.id,
            requirement_id=requirement.id,
            status=DocumentReviewStatus.SUBMITTED,
            notes=None,
        )
        self.session.add(status)
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.DOCUMENT_SUBMITTED,
                aggregate_type="DocumentStatus",
                aggregate_id=status.id,
                payload={"placement_id": str(placement_id), "requirement_id": str(requirement.id)},
            )
        )
        return status


class ReviewDocument:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = InProcessEventBus(session)

    def approve(self, document_status_id: UUID) -> DocumentStatus:
        status = self.session.get(DocumentStatus, document_status_id)
        if status is None:
            raise LookupError("Document status not found.")
        status.status = DocumentReviewStatus.APPROVED
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.DOCUMENT_APPROVED,
                aggregate_type="DocumentStatus",
                aggregate_id=status.id,
                payload={"requirement_id": str(status.requirement_id)},
            )
        )
        return status
