import uuid
from enum import StrEnum

from sqlalchemy import ARRAY, Boolean, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class VerificationStatus(StrEnum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class Modality(StrEnum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class CompensationType(StrEnum):
    PAID = "paid"
    UNPAID = "unpaid"
    STIPEND = "stipend"


class OpportunityStatus(StrEnum):
    DRAFT = "Draft"
    UNDER_REVIEW = "UnderReview"
    PUBLISHED = "Published"
    CLOSED = "Closed"
    CANCELLED = "Cancelled"


class HostOrganization(Base):
    __tablename__ = "host_organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    organization_type: Mapped[str] = mapped_column(String(120))
    institutional_verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus, name="verification_status", values_callable=enum_values))


class InternshipOpportunity(Base):
    __tablename__ = "internship_opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    host_org_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("host_organizations.id"))
    title: Mapped[str] = mapped_column(String(255))
    modality: Mapped[Modality] = mapped_column(Enum(Modality, name="modality", values_callable=enum_values))
    compensation_type: Mapped[CompensationType] = mapped_column(Enum(CompensationType, name="compensation_type", values_callable=enum_values))
    capacity: Mapped[int] = mapped_column(Integer)
    eligible_programs: Mapped[list[str]] = mapped_column(ARRAY(String))
    status: Mapped[OpportunityStatus] = mapped_column(Enum(OpportunityStatus, name="opportunity_status", values_callable=enum_values))

    def publish(self, host_org: HostOrganization) -> None:
        if host_org.institutional_verification_status != VerificationStatus.APPROVED:
            raise ValueError("No se puede publicar sin revisión institucional aprobada.")
        self.status = OpportunityStatus.PUBLISHED

    def close_when_full_or_deadline_passed(self, is_full: bool, deadline_passed: bool) -> None:
        if is_full or deadline_passed:
            self.status = OpportunityStatus.CLOSED
