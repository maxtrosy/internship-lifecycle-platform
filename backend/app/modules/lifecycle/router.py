"""HTTP endpoints for C-06 lifecycle (Phase 1)."""
from __future__ import annotations

from urllib.parse import quote
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app import db
from app.deps import requires
from app.errors import BusinessError
from app.modules.audit import service as audit_service
from app.modules import authz
from app.modules.lifecycle import segments as segment_service
from app.modules.lifecycle import service as lifecycle

router = APIRouter()


class ReviewBody(BaseModel):
    decision: str
    reason: str


class HoursBody(BaseModel):
    hours: float = Field(gt=0, allow_inf_nan=False)
    work_date: date | None = None
    description: str | None = Field(default=None, max_length=1000)


class SegmentBody(BaseModel):
    host_org_id: int = Field(ge=1)
    unit: str = Field(min_length=1, max_length=160)
    workplace_supervisor_id: int = Field(ge=1)
    start_date: date
    end_date: date
    modality: Literal["ONSITE", "REMOTE", "HYBRID"]
    responsibilities: str = Field(min_length=1, max_length=5000)
    expected_hours: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class SegmentConditionBody(BaseModel):
    reference: str = Field(min_length=1, max_length=500)


class SegmentCompleteBody(BaseModel):
    ended_on: date | None = None


class SegmentTerminateBody(BaseModel):
    ended_on: date
    reason_shared: str = Field(min_length=1, max_length=1000)
    reason_internal: str | None = Field(default=None, max_length=3000)
    work_recognition: Literal["ACCEPTED_HOURS_RECOGNIZED", "NOT_RECOGNIZED"]
    recognition_note: str | None = Field(default=None, max_length=1000)


class SegmentCancelBody(BaseModel):
    reason_shared: str = Field(min_length=1, max_length=1000)


class SegmentScheduleBody(BaseModel):
    start_date: date | None = None
    end_date: date
    reason_shared: str = Field(min_length=1, max_length=1000)


class TransferBody(BaseModel):
    effective_date: date
    reason_shared: str = Field(min_length=1, max_length=1000)
    reason_internal: str | None = Field(default=None, max_length=3000)
    prior_work_treatment: Literal["ACCEPTED_HOURS_RECOGNIZED", "NOT_RECOGNIZED"]
    destination: SegmentBody


class HoursReviewBody(BaseModel):
    decision: Literal["ACCEPTED", "REJECTED", "DISPUTED"]
    accepted_hours: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    reason_code: Literal["DUPLICATE", "OUTSIDE_SEGMENT", "NOT_VERIFIABLE", "OTHER"] | None = None
    reason: str | None = Field(default=None, max_length=1000)


class ExperienceReviewBody(BaseModel):
    decision: Literal["APPROVED", "CHANGES_REQUIRED"]
    rationale: str = Field(min_length=1, max_length=3000)


class RejectAcademicBody(BaseModel):
    reason: str


class ProgressReportBody(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class EvaluationBody(BaseModel):
    kind: Literal["MIDTERM", "FINAL"]
    narrative: str = Field(min_length=1, max_length=8000)


class IncidentBody(BaseModel):
    kind: Literal["INCIDENT", "CHANGE"]
    summary: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=5000)


class WorkPlanItemBody(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=3000)


class FacultySupervisorBody(BaseModel):
    user_id: int = Field(ge=1)


class PlacementChangeBody(BaseModel):
    """Only supplied fields are copied into a new immutable proposed version."""
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = Field(default=None, min_length=1, max_length=240)
    responsibilities: str | None = Field(default=None, min_length=1, max_length=5000)


class VersionApprovalBody(BaseModel):
    version_id: int = Field(ge=1)


@router.get("/placements/pending-academic")
def pending_academic(subject_id: int = Depends(requires("placement:list"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_pending_academic(cur, subj)


@router.get("/placements/documents-pending")
def documents_pending(subject_id: int = Depends(requires("document:review"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_documents_pending(cur, subj)


@router.get("/placements/pending-activation")
def pending_activation(subject_id: int = Depends(requires("placement:activate"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_pending_activation(cur, subj)


@router.get("/placements")
def visible_placements(subject_id: int = Depends(requires("placement:list"))) -> list[dict]:
    """Return the caller's relation-scoped practice list for the integrated dossier."""
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_visible_placements(cur, subj)


@router.get("/placements/{pid}/checklist")
def checklist(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_checklist(cur, subj, pid)


@router.get("/placements/{pid}/activation-status")
def activation_status(pid: int, subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.activation_status(cur, subj, pid)


@router.post("/placements/{pid}/items/{item_id}/submit", status_code=201)
async def submit_document(pid: int, item_id: int, request: Request,
                          subject_id: int = Depends(requires("document:submit"))) -> dict:
    filename = request.query_params.get("filename", "")
    content_type = request.headers.get("content-type", "application/octet-stream")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = 0
        if declared_size > lifecycle.MAX_DOCUMENT_BYTES:
            raise BusinessError("DOCUMENT_TOO_LARGE", {"max_bytes": lifecycle.MAX_DOCUMENT_BYTES})

    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > lifecycle.MAX_DOCUMENT_BYTES:
            raise BusinessError("DOCUMENT_TOO_LARGE", {"max_bytes": lifecycle.MAX_DOCUMENT_BYTES})
        content.extend(chunk)
    with db.command(subject_id) as ctx:
        return lifecycle.submit_document(ctx, pid, item_id, filename, content_type, bytes(content))


@router.get("/placements/{pid}/items/{item_id}/submissions")
def submissions(pid: int, item_id: int,
                subject_id: int = Depends(requires("document:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_submissions(cur, subj, pid, item_id)


@router.get("/placements/{pid}/items/{item_id}/submissions/{submission_id}/download")
def download_submission(pid: int, item_id: int, submission_id: int,
                        subject_id: int = Depends(requires("document:read"))) -> Response:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        document = lifecycle.get_submission(cur, subj, pid, item_id, submission_id)
    filename = quote(document["original_filename"], safe="")
    return Response(
        content=bytes(document["content"]),
        media_type=document["content_type"],
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/placements/{pid}")
def get_placement(pid: int, subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        authz.authorize(cur, subj, "placement:read", pid)
        return lifecycle.get_placement(cur, pid)


@router.get("/placements/{pid}/dossier")
def placement_dossier(pid: int, subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.get_dossier(cur, subj, pid)


@router.get("/placements/{pid}/faculty-supervisors")
def faculty_supervisor_options(pid: int,
                               subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.faculty_assignment_options(cur, subj, pid)


@router.post("/placements/{pid}/faculty-supervisors", status_code=204)
def assign_faculty_supervisor(pid: int, body: FacultySupervisorBody,
                              subject_id: int = Depends(requires("placement:read"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.assign_faculty_supervisor(ctx, pid, body.user_id)


@router.delete("/placements/{pid}/faculty-supervisors/{faculty_user_id}", status_code=204)
def unassign_faculty_supervisor(pid: int, faculty_user_id: int,
                                subject_id: int = Depends(requires("placement:read"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.unassign_faculty_supervisor(ctx, pid, faculty_user_id)


@router.get("/placements/{pid}/history")
def history(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        authz.authorize(cur, subj, "placement:read", pid)
        return audit_service.list_history(cur, pid)


@router.post("/placements/{pid}/changes", status_code=201)
def propose_placement_change(pid: int, body: PlacementChangeBody,
                             subject_id: int = Depends(requires("placement:read"))) -> dict:
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise BusinessError("CHANGE_EMPTY", "Indica al menos un campo para proponer un cambio.")
    with db.command(subject_id) as ctx:
        version_id = lifecycle.propose_change(ctx, pid, **changes)
    return {"version_id": version_id, "status": "PROPOSED"}


@router.post("/placements/{pid}/changes/approve", status_code=204)
def approve_placement_change(pid: int, body: VersionApprovalBody,
                             subject_id: int = Depends(requires("placement:read"))) -> None:
    with db.command(subject_id) as ctx:
        version = ctx.execute(
            "SELECT placement_id FROM placement_version WHERE id=%s", (body.version_id,)
        ).fetchone()
        if version is None or version["placement_id"] != pid:
            raise BusinessError("VERSION_NOT_FOUND", "La versión no pertenece a esta práctica.")
        lifecycle.approve_version(ctx, body.version_id)


@router.get("/placements/{pid}/progress-reports")
def progress_reports(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_progress_reports(cur, subj, pid)


@router.post("/placements/{pid}/progress-reports", status_code=201)
def create_progress_report(pid: int, body: ProgressReportBody,
                           subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.command(subject_id) as ctx:
        return lifecycle.create_progress_report(ctx, pid, body.content)


@router.get("/placements/{pid}/work-plan")
def work_plan(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_work_plan(cur, subj, pid)


@router.post("/placements/{pid}/work-plan", status_code=201)
def assign_work_plan_item(pid: int, body: WorkPlanItemBody,
                          subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.command(subject_id) as ctx:
        return lifecycle.assign_work_plan_item(ctx, pid, body.title, body.description)


@router.get("/placements/{pid}/evaluations")
def evaluations(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_evaluations(cur, subj, pid)


@router.post("/placements/{pid}/evaluations", status_code=201)
def create_evaluation(pid: int, body: EvaluationBody,
                      subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.command(subject_id) as ctx:
        return lifecycle.create_evaluation(ctx, pid, body.kind, body.narrative)


@router.get("/placements/{pid}/incidents")
def incidents(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_incidents(cur, subj, pid)


@router.post("/placements/{pid}/incidents", status_code=201)
def create_incident(pid: int, body: IncidentBody,
                    subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.command(subject_id) as ctx:
        return lifecycle.create_incident(ctx, pid, body.kind, body.summary, body.description)


@router.get("/placements/{pid}/completion-evidence")
def completion_evidence(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_completion_evidence(cur, subj, pid)


@router.post("/placements/{pid}/completion-evidence/{kind}", status_code=201)
async def submit_completion_evidence(pid: int, kind: str, request: Request,
                                     subject_id: int = Depends(requires("placement:read"))) -> dict:
    filename = request.query_params.get("filename", "")
    content_type = request.headers.get("content-type", "application/octet-stream")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared_size = int(content_length)
        except ValueError:
            declared_size = 0
        if declared_size > lifecycle.MAX_DOCUMENT_BYTES:
            raise BusinessError("DOCUMENT_TOO_LARGE", {"max_bytes": lifecycle.MAX_DOCUMENT_BYTES})
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > lifecycle.MAX_DOCUMENT_BYTES:
            raise BusinessError("DOCUMENT_TOO_LARGE", {"max_bytes": lifecycle.MAX_DOCUMENT_BYTES})
        content.extend(chunk)
    with db.command(subject_id) as ctx:
        return lifecycle.submit_completion_evidence(
            ctx, pid, kind, filename, content_type, bytes(content),
        )


@router.get("/placements/{pid}/completion-evidence/{kind}/{revision}/download")
def download_completion_evidence(pid: int, kind: str, revision: int,
                                 subject_id: int = Depends(requires("placement:read"))) -> Response:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        evidence = lifecycle.get_completion_evidence(cur, subj, pid, kind, revision)
    filename = quote(evidence["original_filename"], safe="")
    return Response(
        content=bytes(evidence["content"]),
        media_type=evidence["content_type"],
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/placements/{pid}/approve-academic", status_code=204)
def approve_academic(pid: int,
                     subject_id: int = Depends(requires("placement:approve_academic"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.academic_approve(ctx, pid)


@router.post("/placements/{pid}/reject-academic", status_code=204)
def reject_academic(pid: int, body: RejectAcademicBody,
                    subject_id: int = Depends(requires("placement:reject_academic"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.academic_reject(ctx, pid, body.reason)


@router.post("/placements/{pid}/activate", status_code=204)
def activate(pid: int, subject_id: int = Depends(requires("placement:activate"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.activate(ctx, pid)


@router.post("/placements/{pid}/confirm-completion", status_code=204)
def confirm_completion(pid: int,
                       subject_id: int = Depends(requires("placement:confirm_completion"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.confirm_completion(ctx, pid)


@router.post("/placements/{pid}/close", status_code=204)
def close(pid: int, subject_id: int = Depends(requires("placement:close"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.close_placement(ctx, pid)


@router.post("/placements/{pid}/items/{item_id}/review", status_code=204)
def review(pid: int, item_id: int, body: ReviewBody,
           subject_id: int = Depends(requires("document:review"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.review_document(ctx, pid, item_id, body.decision, body.reason)


@router.post("/placements/{pid}/hours", status_code=204)
def record_hours(pid: int, body: HoursBody,
                 subject_id: int = Depends(requires("progress:create"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.record_hours(ctx, pid, body.hours, work_date=body.work_date,
                               description=body.description)


@router.get("/placements/{pid}/hours")
def list_hours(pid: int, subject_id: int = Depends(requires("progress:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_hours(cur, subj, pid)


# ----------------------------------------------------------------- CR-05 segments

@router.get("/placements/{pid}/segments")
def list_segments(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return segment_service.list_segments(cur, subj, pid)


@router.get("/placements/{pid}/segment-options")
def segment_options(pid: int, subject_id: int = Depends(requires("segment:manage"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return segment_service.segment_options(cur, subj, pid)


@router.post("/placements/{pid}/segments", status_code=201)
def create_segment(pid: int, body: SegmentBody,
                   subject_id: int = Depends(requires("segment:manage"))) -> dict:
    with db.command(subject_id) as ctx:
        return segment_service.create_segment(ctx, pid, body.model_dump())


@router.post("/placements/{pid}/segments/{sid}/conditions/{condition_id}/confirm", status_code=204)
def confirm_segment_condition(pid: int, sid: int, condition_id: int, body: SegmentConditionBody,
                              subject_id: int = Depends(requires("segment_condition:confirm"))) -> None:
    with db.command(subject_id) as ctx:
        segment_service.confirm_condition(ctx, pid, sid, condition_id, body.reference)


@router.post("/placements/{pid}/segments/{sid}/activate", status_code=204)
def activate_segment(pid: int, sid: int, subject_id: int = Depends(requires("segment:manage"))) -> None:
    with db.command(subject_id) as ctx:
        segment_service.activate_segment(ctx, pid, sid)


@router.post("/placements/{pid}/segments/{sid}/complete", status_code=204)
def complete_segment(pid: int, sid: int, body: SegmentCompleteBody,
                     subject_id: int = Depends(requires("segment:manage"))) -> None:
    with db.command(subject_id) as ctx:
        segment_service.complete_segment(ctx, pid, sid, body.ended_on)


@router.post("/placements/{pid}/segments/{sid}/terminate", status_code=204)
def terminate_segment(pid: int, sid: int, body: SegmentTerminateBody,
                      subject_id: int = Depends(requires("segment:manage"))) -> None:
    with db.command(subject_id) as ctx:
        segment_service.terminate_segment(
            ctx, pid, sid, ended_on=body.ended_on, reason_shared=body.reason_shared,
            reason_internal=body.reason_internal, work_recognition=body.work_recognition,
            recognition_note=body.recognition_note,
        )


@router.post("/placements/{pid}/segments/{sid}/cancel", status_code=204)
def cancel_segment(pid: int, sid: int, body: SegmentCancelBody,
                   subject_id: int = Depends(requires("segment:manage"))) -> None:
    with db.command(subject_id) as ctx:
        segment_service.cancel_segment(ctx, pid, sid, body.reason_shared)


@router.post("/placements/{pid}/segments/{sid}/schedule")
def reschedule_segment(pid: int, sid: int, body: SegmentScheduleBody,
                       subject_id: int = Depends(requires("segment:manage"))) -> dict:
    with db.command(subject_id) as ctx:
        return segment_service.reschedule_segment(
            ctx, pid, sid, start_date=body.start_date, end_date=body.end_date,
            reason_shared=body.reason_shared,
        )


@router.post("/placements/{pid}/segments/{sid}/transfer", status_code=201)
def transfer_segment(pid: int, sid: int, body: TransferBody,
                     subject_id: int = Depends(requires("segment:manage"))) -> dict:
    with db.command(subject_id) as ctx:
        return segment_service.transfer(
            ctx, pid, sid, effective_date=body.effective_date, reason_shared=body.reason_shared,
            reason_internal=body.reason_internal, prior_work_treatment=body.prior_work_treatment,
            destination=body.destination.model_dump(),
        )


@router.get("/placements/{pid}/transfers")
def list_transfers(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return segment_service.list_transfers(cur, subj, pid)


@router.get("/placements/{pid}/hours/summary")
def hours_summary(pid: int, subject_id: int = Depends(requires("progress:read"))) -> dict:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        authz.authorize(cur, subj, "progress:read", pid)
        return segment_service.hours_summary(cur, pid, segment_service.visible_segment_ids(cur, subj, pid))


@router.post("/placements/{pid}/hours/{entry_id}/review", status_code=201)
def review_hours(pid: int, entry_id: int, body: HoursReviewBody,
                 subject_id: int = Depends(requires("hours:review"))) -> dict:
    with db.command(subject_id) as ctx:
        return segment_service.review_hours(
            ctx, pid, entry_id, decision=body.decision, accepted_hours=body.accepted_hours,
            reason_code=body.reason_code, reason=body.reason,
        )


@router.post("/placements/{pid}/experience-review", status_code=201)
def experience_review(pid: int, body: ExperienceReviewBody,
                      subject_id: int = Depends(requires("experience:review"))) -> dict:
    with db.command(subject_id) as ctx:
        return segment_service.record_experience_review(ctx, pid, body.decision, body.rationale)
