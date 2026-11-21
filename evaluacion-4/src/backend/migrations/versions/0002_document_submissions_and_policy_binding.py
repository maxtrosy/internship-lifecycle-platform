"""Persist document revisions and bind lifecycle policy versions.

Revision ID: 0002
Revises: 0001
"""
from __future__ import annotations

from alembic import op
from migrations.schema_sql import UPGRADE_0002_SQL

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0002_SQL)


def downgrade() -> None:
    op.execute("""
    DROP TRIGGER IF EXISTS trg_policy_version_immutable ON policy_version;
    DROP FUNCTION IF EXISTS trg_policy_version_immutable();
    ALTER TABLE checklist_item DROP CONSTRAINT IF EXISTS fk_checklist_current_submission;
    DROP TABLE IF EXISTS document_review;
    DROP TABLE IF EXISTS document_submission;
    ALTER TABLE checklist_item
      DROP COLUMN IF EXISTS current_submission_id,
      DROP COLUMN IF EXISTS current_review_reason;
    ALTER TABLE placement
      DROP COLUMN IF EXISTS activation_policy_version_id,
      DROP COLUMN IF EXISTS completion_policy_version_id;
    """)
