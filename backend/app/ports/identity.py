"""C-01 identity port (ADR-007, OPEN-21 proposal)."""
from __future__ import annotations

from typing import Protocol

import psycopg


class IdentityPort(Protocol):
    """Resolve a subject from the simulated identity store.

    Real deployments would authenticate against the university identity service
    (or an equivalent simulated adapter); roles are NOT returned here — they are
    evaluated in the database on every request (BR-03/ADR-004).
    """

    def authenticate(self, cur: psycopg.Cursor, user_id: int) -> bool:
        """True when the subject exists and may log in."""

    def subject_id(self, cur: psycopg.Cursor, user_id: int) -> int | None:
        """Return the subject id if it exists, else None."""
