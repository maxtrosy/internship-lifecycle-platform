"""Record faculty supervisor assignment changes without inventing history."""
from alembic import op

from migrations.schema_sql import UPGRADE_0012_SQL

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0012_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0012 is intentionally irreversible; assignment history is retained")
