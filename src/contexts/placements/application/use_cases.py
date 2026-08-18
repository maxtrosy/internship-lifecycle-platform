from uuid import UUID
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.contexts.applications_eligibility.domain.models import Application, ApplicationStatus
from src.contexts.agreements.infrastructure.repositories import DocumentChecklistRepository
from src.contexts.placements.domain.models import Placement
from src.contexts.placements.domain.state_machine import PlacementGuards
from src.shared.events import DomainEventName, EventEnvelope, InProcessEventBus


class TransitionPlacement:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.document_checklists = DocumentChecklistRepository(session)
        self.events = InProcessEventBus(session)

    def approve_academically(self, placement_id: UUID) -> Placement:
        placement = self._get_placement(placement_id)
        placement.apply_status(placement.state_machine().start_academic_review())
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.ACADEMIC_REVIEW_STARTED,
                aggregate_type="Placement",
                aggregate_id=placement.id,
                payload={"program_coordinator_id": str(placement.program_coordinator_id)},
            )
        )
        placement.apply_status(
            placement.state_machine().approve_academic_review(PlacementGuards(academic_approval=True))
        )
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.PLACEMENT_APPROVED,
                aggregate_type="Placement",
                aggregate_id=placement.id,
                payload={"program_coordinator_id": str(placement.program_coordinator_id)},
            )
        )
        return placement

    def mark_ready_to_activate(self, placement_id: UUID) -> Placement:
        placement = self._get_placement(placement_id)

        documents_complete = self.document_checklists.mandatory_documents_complete_for_placement(placement_id)
        employer_selection_confirmed = self.session.scalar(
            select(Application.id)
            .where(Application.student_id == placement.student_id)
            .where(Application.opportunity_id == placement.opportunity_id)
            .where(Application.status == ApplicationStatus.EMPLOYER_ACCEPTED)
            .limit(1)
        )
        placement.transition_to_ready(
            PlacementGuards(
                documents_complete=documents_complete,
                employer_selection_confirmed=employer_selection_confirmed is not None,
            )
        )
        return placement

    def activate(self, placement_id: UUID, today: date | None = None) -> Placement:
        placement = self._get_placement(placement_id)
        current_date = today or date.today()
        placement.activate(PlacementGuards(start_date_reached=current_date >= placement.start_date))
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.PLACEMENT_ACTIVATED,
                aggregate_type="Placement",
                aggregate_id=placement.id,
                payload={"start_date": placement.start_date.isoformat()},
            )
        )
        return placement

    def _get_placement(self, placement_id: UUID) -> Placement:
        placement = self.session.get(Placement, placement_id)
        if placement is None:
            raise LookupError("Placement not found.")
        return placement
