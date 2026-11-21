"""Persist recipient-scoped notifications and placement conversations."""
from alembic import op

from migrations.schema_sql import UPGRADE_0010_SQL

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0010_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0010 is intentionally irreversible; message history is retained")
