"""CR-05: audited segment attribute revisions and documentary evidence for segment conditions."""
from alembic import op

from migrations.schema_sql import DOWNGRADE_0019_SQL, UPGRADE_0019_SQL

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0019_SQL)


def downgrade() -> None:
    # Revisions and segment evidence (documents, reviews) are history; the
    # downgrade refuses instead of erasing them (same stance as 0016/0018).
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM placement_segment_revision) OR EXISTS (
           SELECT 1 FROM document_submission ds JOIN checklist_item ci ON ci.id = ds.checklist_item_id
           WHERE ci.segment_condition_id IS NOT NULL) THEN
        RAISE EXCEPTION 'DOWNGRADE_BLOCKED: segment revisions or segment evidence exist; restore from backup instead';
      END IF; END $$;""")
    op.execute(DOWNGRADE_0019_SQL)
