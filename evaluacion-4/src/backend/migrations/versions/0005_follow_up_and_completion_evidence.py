"""Persist follow-up, evaluation, incident, and final evidence records."""
from alembic import op

from migrations.schema_sql import UPGRADE_0005_SQL

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0005_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0005 is intentionally irreversible to preserve submitted lifecycle evidence")
