"""Initial schema: PoC schema ported (ADR-003/005) with role_assignment + invitation.

Revision ID: 0001
"""
from __future__ import annotations

from alembic import op

from migrations.schema_sql import SCHEMA

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(SCHEMA)


def downgrade() -> None:
    op.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
