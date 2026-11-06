"""Support manual eligibility review and its persistent notifications."""
from alembic import op

from migrations.schema_sql import UPGRADE_0014_SQL

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0014_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0014 is intentionally irreversible; review notifications are retained")
