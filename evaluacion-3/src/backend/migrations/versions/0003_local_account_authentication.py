"""Add local password credentials, active state, sessions and password resets.

Revision ID: 0003
Revises: 0002
"""
from __future__ import annotations

from alembic import op

from migrations.schema_sql import UPGRADE_0003_SQL

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0003_SQL)


def downgrade() -> None:
    op.execute("""
    DROP TABLE IF EXISTS auth_password_reset;
    DROP TABLE IF EXISTS auth_session;
    DROP INDEX IF EXISTS user_account_email_lower_uidx;
    DROP INDEX IF EXISTS user_account_username_lower_uidx;
    ALTER TABLE user_account
      DROP COLUMN IF EXISTS is_active,
      DROP COLUMN IF EXISTS password_hash,
      DROP COLUMN IF EXISTS username;
    """)
