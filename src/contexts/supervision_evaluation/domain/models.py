import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Boolean, Date, Enum, Float, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class EvaluationType(StrEnum):
    MIDTERM = "Midterm"
    FINAL = "Final"


class HoursApprovalStatus(StrEnum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class WorkPlan(Base):
    __tablename__ = "work_plans"

    placement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    objectives: Mapped[str] = mapped_column(String(2000))
    responsibilities: Mapped[str] = mapped_column(String(2000))
    approved_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))


class ProgressReport(Base):
    __tablename__ = "progress_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    period: Mapped[str] = mapped_column(String(120))
    hours: Mapped[float] = mapped_column(Float)
    evidence: Mapped[str] = mapped_column(String(1000))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    evaluation_type: Mapped[EvaluationType] = mapped_column(Enum(EvaluationType, name="evaluation_type", values_callable=enum_values))
    evaluator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    rubric: Mapped[dict] = mapped_column(JSON)
    comments: Mapped[str] = mapped_column(String(2000))


class HoursLog(Base):
    __tablename__ = "hours_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    log_date: Mapped[date] = mapped_column(Date)
    hours: Mapped[float] = mapped_column(Float)
    description: Mapped[str] = mapped_column(String(1000))
    approval_status: Mapped[HoursApprovalStatus] = mapped_column(Enum(HoursApprovalStatus, name="hours_approval_status", values_callable=enum_values))
    academic_program_requires_hours: Mapped[bool] = mapped_column(Boolean)

    def countable_hours(self) -> float:
        raise NotImplementedError
