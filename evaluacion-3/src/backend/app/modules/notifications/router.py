"""HTTP API for notification inboxes and contextual placement communication."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app import db
from app.deps import requires
from app.modules import authz
from app.modules.notifications import service

router = APIRouter()


class MessageBody(BaseModel):
    audience: Literal["JOINT", "ACADEMIC"]
    content: str = Field(min_length=1, max_length=4000)


@router.get("/notifications")
def list_notifications(subject_id: int = Depends(requires("notification:read"))) -> list[dict]:
    with db.read() as cur:
        return service.list_inbox(cur, subject_id)


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int,
                           subject_id: int = Depends(requires("notification:read"))) -> dict:
    with db.command(subject_id) as ctx:
        return service.mark_read(ctx, notification_id)


@router.get("/placements/{pid}/messages")
def list_messages(pid: int, audience: Literal["JOINT", "ACADEMIC"],
                  subject_id: int = Depends(requires("placement:read"))) -> list[dict]:
    with db.read() as cur:
        subj = authz.subject(cur, subject_id)
        return service.list_messages(cur, subj, pid, audience)


@router.post("/placements/{pid}/messages", status_code=201)
def create_message(pid: int, body: MessageBody,
                   subject_id: int = Depends(requires("placement:read"))) -> dict:
    with db.command(subject_id) as ctx:
        return service.create_message(ctx, pid, body.audience, body.content)
