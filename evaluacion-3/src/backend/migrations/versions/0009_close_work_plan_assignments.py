"""Stop work-plan inserts after closure and serialize them with the state change."""
from alembic import op

from migrations.schema_sql import UPGRADE_0009_SQL

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0009_SQL)


def downgrade() -> None:
    raise RuntimeError(
        "Migration 0009 is intentionally irreversible; reopening writes after closure would weaken auditability"
    )
