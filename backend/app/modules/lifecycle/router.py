"""HTTP endpoints for C-06 lifecycle (Phase 1)."""
from __future__ import annotations

from urllib.parse import quote
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from app import db
from app.deps import requires
from app.errors import BusinessError
from app.modules.audit import service as audit_service
from app.modules import authz
from app.modules.lifecycle import service as lifecycle

router = APIRouter()


class ReviewBody(BaseModel):
    decision: str
    reason: str


class HoursBody(BaseModel):
    hours: float = Field(gt=0, allow_inf_nan=False)


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
        lifecycle.record_hours(ctx, pid, body.hours)


@router.get("/placements/{pid}/hours")
def list_hours(pid: int, subject_id: int = Depends(requires("progress:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return lifecycle.list_hours(cur, subj, pid)
