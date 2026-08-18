import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class DeadlineStatus(StrEnum):
    PENDING = "Pending"
    MET = "Met"
    MISSED = "Missed"


class RiskType(StrEnum):
    DELAYED_ACTIVATION = "DelayedActivation"
    OVERDUE_EVALUATION = "OverdueEvaluation"
    MISSING_HOURS = "MissingHours"


class Deadline(Base):
    __tablename__ = "deadlines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    related_entity: Mapped[str] = mapped_column(String(120))
    related_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    due_date: Mapped[date] = mapped_column(Date)
    deadline_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[DeadlineStatus] = mapped_column(Enum(DeadlineStatus, name="deadline_status", values_callable=enum_values))


class RiskFlag(Base):
    __tablename__ = "risk_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    risk_type: Mapped[RiskType] = mapped_column(Enum(RiskType, name="risk_type", values_callable=enum_values))
    flagged_at: Mapped[date] = mapped_column(Date)
