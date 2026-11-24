"""CR-05: recorded schedule changes (shorten, extend or move) for open segments."""
from alembic import op

from migrations.schema_sql import DOWNGRADE_0018_SQL, UPGRADE_0018_SQL

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0018_SQL)


def downgrade() -> None:
    # Dropping the table would erase the history of period changes, so the
    # downgrade refuses when any change was recorded (same stance as 0016).
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM placement_segment_schedule_change) THEN
        RAISE EXCEPTION 'DOWNGRADE_BLOCKED: segment schedule changes exist; restore from backup instead';
      END IF; END $$;""")
    op.execute(DOWNGRADE_0018_SQL)
