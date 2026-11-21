"""CR-05: rotational placement segments, transfers, hour review and combined review."""
from alembic import op

from migrations.schema_sql import UPGRADE_0016_SQL

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0016_SQL)


def downgrade() -> None:
    raise RuntimeError(
        "Migration 0016 is intentionally irreversible; segment, transfer and hour-review history is retained"
    )
