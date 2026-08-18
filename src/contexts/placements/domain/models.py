import uuid
from datetime import date
from enum import StrEnum

from sqlalchemy import Date, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.contexts.placements.domain.state_machine import PlacementGuards, PlacementStateMachine, PlacementStatus
from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class PlacementChangeType(StrEnum):
    SUPERVISOR_CHANGE = "SupervisorChange"
    SCHEDULE_CHANGE = "ScheduleChange"
    LOCATION_CHANGE = "LocationChange"
    RESPONSIBILITY_CHANGE = "ResponsibilityChange"
    INCIDENT = "Incident"


class ResolutionStatus(StrEnum):
    OPEN = "Open"
    RESOLVED = "Resolved"
    CLOSED_INCOMPLETE = "ClosedIncomplete"


class Placement(Base):
    __tablename__ = "placements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    host_org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    workplace_supervisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    faculty_supervisor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    program_coordinator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    status: Mapped[PlacementStatus] = mapped_column(Enum(PlacementStatus, name="placement_status", values_callable=lambda enum_cls: [member.value for member in enum_cls]))

    def state_machine(self) -> PlacementStateMachine:
        return PlacementStateMachine(self.status)

    def apply_status(self, status: PlacementStatus) -> None:
        self.status = status

    def transition_to_ready(self, guards: PlacementGuards) -> None:
        self.apply_status(self.state_machine().mark_ready_to_activate(guards))

    def approve_academically(self) -> None:
        machine = self.state_machine()
        machine.start_academic_review()
        self.apply_status(machine.approve_academic_review(PlacementGuards(academic_approval=True)))

    def activate(self, guards: PlacementGuards) -> None:
        self.apply_status(self.state_machine().activate(guards))


class PlacementChange(Base):
    __tablename__ = "placement_changes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    placement_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    change_type: Mapped[PlacementChangeType] = mapped_column(Enum(PlacementChangeType, name="placement_change_type", values_callable=enum_values))
    description: Mapped[str] = mapped_column(String(2000))
    reported_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    resolution_status: Mapped[ResolutionStatus] = mapped_column(Enum(ResolutionStatus, name="resolution_status", values_callable=enum_values))
