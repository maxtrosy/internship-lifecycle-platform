from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class PlacementStatus(StrEnum):
    PROPOSED = "Proposed"
    UNDER_ACADEMIC_REVIEW = "UnderAcademicReview"
    DOCUMENTATION_PENDING = "DocumentationPending"
    READY_TO_ACTIVATE = "ReadyToActivate"
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    INTERRUPTED = "Interrupted"
    PENDING_FINAL_EVALUATION = "PendingFinalEvaluation"
    PENDING_FINAL_EVIDENCE = "PendingFinalEvidence"
    REJECTED = "Rejected"
    WITHDRAWN = "Withdrawn"
    CLOSED_INCOMPLETE = "ClosedIncomplete"
    CLOSED = "Closed"


@dataclass(frozen=True)
class PlacementGuards:
    academic_approval: bool = False
    documents_complete: bool = False
    employer_selection_confirmed: bool = False
    start_date_reached: bool = False
    final_evaluation_present: bool = False
    final_evidence_present: bool = False


class PlacementStateMachine:
    def __init__(self, status: PlacementStatus) -> None:
        self.status = status

    def start_academic_review(self) -> PlacementStatus:
        return self._transition(PlacementStatus.PROPOSED, PlacementStatus.UNDER_ACADEMIC_REVIEW)

    def withdraw_from_proposed(self) -> PlacementStatus:
        return self._transition(PlacementStatus.PROPOSED, PlacementStatus.WITHDRAWN)

    def reject(self) -> PlacementStatus:
        return self._transition(PlacementStatus.UNDER_ACADEMIC_REVIEW, PlacementStatus.REJECTED)

    def approve_academic_review(self, guards: PlacementGuards) -> PlacementStatus:
        if not guards.academic_approval:
            raise ValueError("No se activa sin aprobación académica.")
        return self._transition(PlacementStatus.UNDER_ACADEMIC_REVIEW, PlacementStatus.DOCUMENTATION_PENDING)

    def mark_ready_to_activate(self, guards: PlacementGuards) -> PlacementStatus:
        if not guards.documents_complete:
            raise ValueError("Placement no puede entrar a ReadyToActivate con documentos obligatorios sin Approved.")
        if not guards.employer_selection_confirmed:
            raise ValueError("No se activa sin selección del empleador confirmada.")
        return self._transition(PlacementStatus.DOCUMENTATION_PENDING, PlacementStatus.READY_TO_ACTIVATE)

    def withdraw_before_activation(self) -> PlacementStatus:
        return self._transition(PlacementStatus.DOCUMENTATION_PENDING, PlacementStatus.WITHDRAWN)

    def activate(self, guards: PlacementGuards) -> PlacementStatus:
        if not guards.start_date_reached:
            raise ValueError("ReadyToActivate solo puede pasar a Active con startDate alcanzada.")
        return self._transition(PlacementStatus.READY_TO_ACTIVATE, PlacementStatus.ACTIVE)

    def suspend(self) -> PlacementStatus:
        return self._transition(PlacementStatus.ACTIVE, PlacementStatus.SUSPENDED)

    def resume_from_suspended(self) -> PlacementStatus:
        return self._transition(PlacementStatus.SUSPENDED, PlacementStatus.ACTIVE)

    def interrupt(self) -> PlacementStatus:
        return self._transition(PlacementStatus.ACTIVE, PlacementStatus.INTERRUPTED)

    def resume_from_interrupted(self) -> PlacementStatus:
        return self._transition(PlacementStatus.INTERRUPTED, PlacementStatus.ACTIVE)

    def close_incomplete(self) -> PlacementStatus:
        return self._transition(PlacementStatus.INTERRUPTED, PlacementStatus.CLOSED_INCOMPLETE)

    def start_final_evaluation(self, end_date: date, today: date, coordinator_triggered: bool) -> PlacementStatus:
        if today < end_date and not coordinator_triggered:
            raise ValueError("Active solo pasa a PendingFinalEvaluation con endDate alcanzada o disparo de Coordinator.")
        return self._transition(PlacementStatus.ACTIVE, PlacementStatus.PENDING_FINAL_EVALUATION)

    def submit_final_evaluation(self, guards: PlacementGuards) -> PlacementStatus:
        if not guards.final_evaluation_present:
            raise ValueError("WorkplaceSupervisor debe enviar evaluación final.")
        return self._transition(PlacementStatus.PENDING_FINAL_EVALUATION, PlacementStatus.PENDING_FINAL_EVIDENCE)

    def close(self, guards: PlacementGuards) -> PlacementStatus:
        if not guards.final_evaluation_present or not guards.final_evidence_present:
            raise ValueError("No se cierra sin evaluación final y evidencia final del estudiante.")
        return self._transition(PlacementStatus.PENDING_FINAL_EVIDENCE, PlacementStatus.CLOSED)

    def _transition(self, expected: PlacementStatus, target: PlacementStatus) -> PlacementStatus:
        if self.status != expected:
            raise ValueError(f"Transición inválida: {self.status} -> {target}.")
        self.status = target
        return self.status
