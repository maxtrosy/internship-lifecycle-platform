"""Record the factual reported state for lifecycle incidents and changes."""
from alembic import op

from migrations.schema_sql import UPGRADE_0008_SQL

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0008_SQL)


def downgrade() -> None:
    raise RuntimeError(
        "Migration 0008 is intentionally irreversible; incident status is part of the audit record"
    )
