import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class DocumentRequirementType(StrEnum):
    AGREEMENT = "agreement"
    INSURANCE = "insurance"
    CONFIDENTIALITY = "confidentiality"
    OTHER = "other"


class DocumentReviewStatus(StrEnum):
    PENDING = "Pending"
    SUBMITTED = "Submitted"
    UNDER_LEGAL_REVIEW = "UnderLegalReview"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class DocumentChecklist(Base):
    __tablename__ = "document_checklists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("placements.id"), unique=True)


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_checklists.id"))
    requirement_type: Mapped[DocumentRequirementType] = mapped_column(Enum(DocumentRequirementType, name="document_requirement_type", values_callable=enum_values))
    required: Mapped[bool] = mapped_column(Boolean)


class DocumentStatus(Base):
    __tablename__ = "document_statuses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_checklists.id"))
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("document_requirements.id"))
    status: Mapped[DocumentReviewStatus] = mapped_column(Enum(DocumentReviewStatus, name="document_review_status", values_callable=enum_values))
    notes: Mapped[str | None] = mapped_column(String(500))
