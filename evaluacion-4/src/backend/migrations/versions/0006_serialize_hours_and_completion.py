"""Serialize hours writes with completion transitions."""
from alembic import op

from migrations.schema_sql import DOWNGRADE_0006_SQL, UPGRADE_0006_SQL

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0006_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_0006_SQL)
