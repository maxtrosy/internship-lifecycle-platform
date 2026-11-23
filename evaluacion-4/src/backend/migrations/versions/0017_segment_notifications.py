"""CR-05: notification category for segment activation, completion, termination and transfer."""
from alembic import op

from migrations.schema_sql import UPGRADE_0014_SQL, UPGRADE_0017_SQL

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0017_SQL)


def downgrade() -> None:
    # Restoring the 0014 category list fails if SEGMENT_CHANGED notices exist,
    # so they are removed first; they carry no source data (only a category).
    op.execute("DELETE FROM user_notification WHERE category = 'SEGMENT_CHANGED'")
    op.execute(UPGRADE_0014_SQL)
