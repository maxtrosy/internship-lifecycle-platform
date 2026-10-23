"""C-11 audit (ADR-005): append-only events written in the same transaction as the mutation."""
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.db import current_command


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
    cur.execute(
        """INSERT INTO audit_event(actor_id, action, subject_type, subject_id, before_state, after_state, correlation_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
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
    ctx.audited = True


def list_history(cur: psycopg.Cursor, placement_id: int) -> list[dict[str, Any]]:
    return cur.execute(
        """SELECT id, occurred_at, actor_id, action, subject_type, subject_id, before_state, after_state, correlation_id
           FROM audit_event
           WHERE (subject_type = 'placement' AND subject_id = %s)
              OR (subject_type = 'checklist_item' AND subject_id IN
                    (SELECT id FROM checklist_item WHERE placement_id = %s))
              OR (subject_type = 'placement_version' AND subject_id IN
                    (SELECT id FROM placement_version WHERE placement_id = %s))
           ORDER BY id""",
        (placement_id, placement_id, placement_id),
    ).fetchall()
