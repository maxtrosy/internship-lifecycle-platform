"""Restrict app_user to the DML used by application services."""
from alembic import op

from migrations.schema_sql import UPGRADE_0013_SQL

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0013_SQL)


def downgrade() -> None:
    raise RuntimeError("Migration 0013 is intentionally irreversible; broad grants are not restored")
