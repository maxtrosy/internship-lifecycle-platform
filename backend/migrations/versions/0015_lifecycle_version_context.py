"""Record the approved placement version used by follow-up records."""
from alembic import op

from migrations.schema_sql import UPGRADE_0015_SQL

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0015_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0015 is intentionally irreversible; version context is audit history")
