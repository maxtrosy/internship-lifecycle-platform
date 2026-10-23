"""Simulated identity adapter: subjects live in ``user_account`` (synthetic only)."""
from __future__ import annotations

import psycopg


class SimulatedIdentityAdapter:
    def authenticate(self, cur: psycopg.Cursor, user_id: int) -> bool:
        row = cur.execute("SELECT 1 FROM user_account WHERE id = %s", (user_id,)).fetchone()
        return row is not None

    def subject_id(self, cur: psycopg.Cursor, user_id: int) -> int | None:
        row = cur.execute("SELECT id FROM user_account WHERE id = %s", (user_id,)).fetchone()
        return row["id"] if row else None


identity_adapter = SimulatedIdentityAdapter()
