"""HTTP endpoints for C-06 lifecycle (Phase 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app import db
from app.deps import requires
from app.modules import audit as audit_service
from app.modules import authz
from app.modules.lifecycle import service as lifecycle

router = APIRouter()


class ApproveAcademicBody(BaseModel):
    required_kinds: list[str]


class ReviewBody(BaseModel):
    decision: str


class EvidenceBody(BaseModel):
    kind: str


class HoursBody(BaseModel):
    hours: float


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
def approve_academic(pid: int, body: ApproveAcademicBody,
                     subject_id: int = Depends(requires("placement:approve_academic"))) -> None:
    with db.command(subject_id) as ctx:
        lifecycle.academic_approve(ctx, pid, body.required_kinds)


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
        lifecycle.review_document(ctx, item_id, body.decision)


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
