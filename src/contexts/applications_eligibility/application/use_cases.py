import uuid
from datetime import datetime
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.contexts.applications_eligibility.domain.models import Application, ApplicationStatus, EligibilityCheck
from src.contexts.placements.domain.models import Placement
from src.contexts.placements.domain.state_machine import PlacementStatus
from src.shared.events import DomainEventName, EventEnvelope, InProcessEventBus


ACTIVE_APPLICATION_TERMINAL_STATUSES = {
    ApplicationStatus.ELIGIBILITY_REJECTED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.EMPLOYER_REJECTED,
}


class SubmitApplication:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = InProcessEventBus(session)

    def execute(self, student_id: UUID, opportunity_id: UUID) -> Application:
        existing_active = self.session.scalar(
            select(Application.id)
            .where(Application.student_id == student_id)
            .where(Application.opportunity_id == opportunity_id)
            .where(Application.status.notin_(ACTIVE_APPLICATION_TERMINAL_STATUSES))
            .limit(1)
        )
        if existing_active is not None:
            raise ValueError("Un estudiante no puede tener dos aplicaciones activas a la misma oportunidad.")

        application = Application(
            student_id=student_id,
            opportunity_id=opportunity_id,
            status=ApplicationStatus.SUBMITTED,
            submitted_at=datetime.utcnow(),
        )
        self.session.add(application)
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.APPLICATION_SUBMITTED,
                aggregate_type="Application",
                aggregate_id=application.id,
                payload={"student_id": str(student_id), "opportunity_id": str(opportunity_id)},
            )
        )
        return application


class ValidateEligibility:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = InProcessEventBus(session)

    def approve(self, application_id: UUID, evaluator_id: UUID, evaluated_criteria: dict) -> Application:
        application = self.session.get(Application, application_id)
        if application is None:
            raise LookupError("Application not found.")
        if application.status != ApplicationStatus.SUBMITTED:
            raise ValueError("Eligibility can only be validated for a submitted application.")

        application.status = ApplicationStatus.ELIGIBILITY_VALIDATED
        self.session.add(
            EligibilityCheck(
                application_id=application.id,
                evaluated_criteria=evaluated_criteria,
                result=True,
                evaluator_id=evaluator_id,
                evaluated_at=datetime.utcnow(),
            )
        )
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.ELIGIBILITY_VALIDATED,
                aggregate_type="Application",
                aggregate_id=application.id,
                payload={"evaluator_id": str(evaluator_id)},
            )
        )
        application.forward_to_employer()
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.APPLICATION_FORWARDED_TO_EMPLOYER,
                aggregate_type="Application",
                aggregate_id=application.id,
                payload={"evaluator_id": str(evaluator_id)},
            )
        )
        return application


class EmployerAcceptCandidate:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = InProcessEventBus(session)

    def execute(
        self,
        application_id: UUID,
        host_org_id: UUID,
        workplace_supervisor_id: UUID,
        faculty_supervisor_id: UUID,
        program_coordinator_id: UUID,
        start_date: date,
        end_date: date,
    ) -> Placement:
        application = self.session.get(Application, application_id)
        if application is None:
            raise LookupError("Application not found.")
        if application.status != ApplicationStatus.FORWARDED_TO_EMPLOYER:
            raise ValueError("Employer cannot accept before application is forwarded to employer.")

        application.status = ApplicationStatus.EMPLOYER_ACCEPTED
        placement = Placement(
            id=uuid.uuid4(),
            student_id=application.student_id,
            opportunity_id=application.opportunity_id,
            host_org_id=host_org_id,
            workplace_supervisor_id=workplace_supervisor_id,
            faculty_supervisor_id=faculty_supervisor_id,
            program_coordinator_id=program_coordinator_id,
            start_date=start_date,
            end_date=end_date,
            status=PlacementStatus.PROPOSED,
        )
        self.session.add(placement)
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.EMPLOYER_ACCEPTED,
                aggregate_type="Application",
                aggregate_id=application.id,
                payload={"placement_id": str(placement.id)},
            )
        )
        self.events.publish(
            EventEnvelope(
                name=DomainEventName.PLACEMENT_PROPOSED,
                aggregate_type="Placement",
                aggregate_id=placement.id,
                payload={"application_id": str(application.id)},
            )
        )
        return placement
