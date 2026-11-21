"""Persist assigned work-plan activities in the placement dossier."""
from alembic import op

from migrations.schema_sql import UPGRADE_0007_SQL

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0007_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0007 is intentionally irreversible to preserve assigned work-plan history")
