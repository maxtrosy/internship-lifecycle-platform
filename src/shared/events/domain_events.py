import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class DomainEventName(StrEnum):
    OPPORTUNITY_PUBLISHED = "OpportunityPublished"
    OPPORTUNITY_CLOSED = "OpportunityClosed"
    APPLICATION_SUBMITTED = "ApplicationSubmitted"
    ELIGIBILITY_VALIDATED = "EligibilityValidated"
    ELIGIBILITY_REJECTED = "EligibilityRejected"
    APPLICATION_FORWARDED_TO_EMPLOYER = "ApplicationForwardedToEmployer"
    EMPLOYER_ACCEPTED = "EmployerAccepted"
    EMPLOYER_REJECTED = "EmployerRejected"
    DOCUMENT_SUBMITTED = "DocumentSubmitted"
    DOCUMENT_APPROVED = "DocumentApproved"
    DOCUMENT_REJECTED = "DocumentRejected"
    PLACEMENT_PROPOSED = "PlacementProposed"
    ACADEMIC_REVIEW_STARTED = "AcademicReviewStarted"
    PLACEMENT_APPROVED = "PlacementApproved"
    PLACEMENT_REJECTED = "PlacementRejected"
    PLACEMENT_ACTIVATED = "PlacementActivated"
    PLACEMENT_SUSPENDED = "PlacementSuspended"
    PLACEMENT_RESUMED = "PlacementResumed"
    PLACEMENT_INTERRUPTED = "PlacementInterrupted"
    PLACEMENT_CLOSED = "PlacementClosed"
    PLACEMENT_CLOSED_INCOMPLETE = "PlacementClosedIncomplete"
    PLACEMENT_WITHDRAWN = "PlacementWithdrawn"
    SUPERVISOR_CHANGED = "SupervisorChanged"
    SCHEDULE_CHANGED = "ScheduleChanged"
    LOCATION_CHANGED = "LocationChanged"
    INCIDENT_REPORTED = "IncidentReported"
    WORK_PLAN_APPROVED = "WorkPlanApproved"
    PROGRESS_REPORT_SUBMITTED = "ProgressReportSubmitted"
    HOURS_LOGGED = "HoursLogged"
    MIDTERM_EVALUATION_SUBMITTED = "MidtermEvaluationSubmitted"
    FINAL_EVALUATION_SUBMITTED = "FinalEvaluationSubmitted"
    FINAL_EVIDENCE_SUBMITTED = "FinalEvidenceSubmitted"
    DEADLINE_MISSED = "DeadlineMissed"
    RISK_FLAG_RAISED = "RiskFlagRaised"


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[DomainEventName] = mapped_column(Enum(DomainEventName, name="domain_event_name", values_callable=enum_values))
    aggregate_type: Mapped[str] = mapped_column(String(120))
    aggregate_id: Mapped[uuid.UUID]
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
