import uuid
from enum import StrEnum

from sqlalchemy import ARRAY, Enum, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.db import Base


def enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_cls]


class Role(StrEnum):
    STUDENT = "Student"
    HOST_ORG_REP = "HostOrgRep"
    WORKPLACE_SUPERVISOR = "WorkplaceSupervisor"
    FACULTY_SUPERVISOR = "FacultySupervisor"
    PROGRAM_COORDINATOR = "ProgramCoordinator"
    EXPERIENTIAL_COORDINATOR = "ExperientialCoordinator"
    LEGAL_REP = "LegalRep"
    IT_ADMIN = "ITAdmin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sso_subject: Mapped[str] = mapped_column(String(255), unique=True)
    roles: Mapped[list[Role]] = mapped_column(ARRAY(Enum(Role, name="role", values_callable=enum_values)))
