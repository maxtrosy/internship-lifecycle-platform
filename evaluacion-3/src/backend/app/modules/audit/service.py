"""C-11 audit (ADR-005): append-only events written in the same transaction as the mutation."""
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.db import current_command
from app.modules.notifications import service as notifications


def write(
    cur: psycopg.Cursor,
    action: str,
    subject_type: str,
    subject_id: int,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    """Insert one audit event. Only callable inside ``command()`` (BR-07).

    The command context supplies the correlation id and actor; the ``command()`` context
    manager then verifies that an accepted mutation wrote at least one event.
    """
    ctx = current_command()
    if ctx is None or cur is not ctx.cur:
        raise RuntimeError("audit.write is only allowed inside command()")
    event = cur.execute(
        """INSERT INTO audit_event(actor_id, action, subject_type, subject_id, before_state, after_state, correlation_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id, occurred_at""",
        (
            ctx.actor_id,
            action,
            subject_type,
            subject_id,
            Jsonb(before) if before is not None else None,
            Jsonb(after) if after is not None else None,
            ctx.correlation_id,
        ),
    )
    event_row = event.fetchone()
    notifications.enqueue_from_audit(
        cur, event_row["id"], action, subject_type, subject_id, after, event_row["occurred_at"]
    )
    ctx.audited = True


def list_history(cur: psycopg.Cursor, placement_id: int) -> list[dict[str, Any]]:
    return cur.execute(
        """SELECT occurred_at, action
           FROM audit_event
           WHERE (subject_type = 'placement' AND subject_id = %s)
              OR (subject_type = 'application' AND subject_id =
                    (SELECT application_id FROM placement WHERE id = %s))
              OR (subject_type = 'checklist_item' AND subject_id IN
                    (SELECT id FROM checklist_item WHERE placement_id = %s))
              OR (subject_type = 'placement_version' AND subject_id IN
                    (SELECT id FROM placement_version WHERE placement_id = %s))
           ORDER BY occurred_at, id""",
        (placement_id, placement_id, placement_id, placement_id),
    ).fetchall()
