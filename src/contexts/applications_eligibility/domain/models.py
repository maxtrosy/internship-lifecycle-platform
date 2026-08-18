import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class ApplicationStatus(StrEnum):
    DRAFT = "Draft"
    SUBMITTED = "Submitted"
    ELIGIBILITY_VALIDATED = "EligibilityValidated"
    ELIGIBILITY_REJECTED = "EligibilityRejected"
    FORWARDED_TO_EMPLOYER = "ForwardedToEmployer"
    EMPLOYER_ACCEPTED = "EmployerAccepted"
    EMPLOYER_REJECTED = "EmployerRejected"
    WITHDRAWN = "Withdrawn"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    opportunity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("internship_opportunities.id"))
    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus, name="application_status", values_callable=enum_values))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (
        # PostgreSQL partial unique index enforces "one active application" at the database boundary.
        Index(
            "uq_applications_active_student_opportunity",
            "student_id",
            "opportunity_id",
            unique=True,
            postgresql_where=~status.in_(
                [
                    ApplicationStatus.ELIGIBILITY_REJECTED,
                    ApplicationStatus.WITHDRAWN,
                    ApplicationStatus.EMPLOYER_REJECTED,
                ]
            ),
        ),
    )

    def forward_to_employer(self) -> None:
        if self.status != ApplicationStatus.ELIGIBILITY_VALIDATED:
            raise ValueError("No puede enviarse al empleador sin elegibilidad validada.")
        self.status = ApplicationStatus.FORWARDED_TO_EMPLOYER


class EligibilityCheck(Base):
    __tablename__ = "eligibility_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("applications.id"))
    evaluated_criteria: Mapped[dict] = mapped_column(JSON)
    result: Mapped[bool]
    evaluator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
