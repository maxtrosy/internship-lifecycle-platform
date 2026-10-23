"""HTTP endpoints for C-06 lifecycle (Phase 1)."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app import db
from app.deps import requires
from app.errors import BusinessError
from app.modules import audit as audit_service
from app.modules import authz
from app.modules.lifecycle import service as lifecycle

router = APIRouter()


class ReviewBody(BaseModel):
    decision: str
    reason: str


class EvidenceBody(BaseModel):
    kind: str


class HoursBody(BaseModel):
    hours: float


class RejectAcademicBody(BaseModel):
    reason: str


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


@router.get("/placements/{pid}/history")
def history(pid: int, subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        authz.authorize(cur, subj, "placement:read", pid)
        return audit_service.list_history(cur, pid)


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


@router.post("/placements/{pid}/submit-evidence", status_code=204)
def submit_evidence(pid: int, body: EvidenceBody,
                    subject_id: int = Depends(requires("evidence:submit"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.submit_evidence(ctx, pid, body.kind)


@router.post("/placements/{pid}/hours", status_code=204)
def record_hours(pid: int, body: HoursBody,
                 subject_id: int = Depends(requires("progress:create"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.record_hours(ctx, pid, body.hours)
