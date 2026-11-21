"""Add a guarded draft, review, approval, publication, and closure lifecycle."""
from alembic import op

from migrations.schema_sql import UPGRADE_0011_SQL

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0011_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0011 is intentionally irreversible; opportunity decisions are retained")
