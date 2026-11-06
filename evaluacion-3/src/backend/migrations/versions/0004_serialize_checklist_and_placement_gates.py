"""Serialize lifecycle state changes with checklist requirement updates."""
from alembic import op

from migrations.schema_sql import UPGRADE_0004_SQL

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(UPGRADE_0004_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_checklist_parent_lock ON checklist_item")
    op.execute("DROP FUNCTION IF EXISTS trg_checklist_parent_lock()")
    op.execute("""
        CREATE OR REPLACE FUNCTION trg_placement_gate() RETURNS trigger AS $$
        DECLARE n int;
        BEGIN
          IF NEW.state IS DISTINCT FROM OLD.state THEN
            IF NEW.state = 'ACTIVE' THEN
              IF OLD.state <> 'DOCUMENTATION_PENDING' THEN
                RAISE EXCEPTION 'GATE: illegal transition % -> ACTIVE', OLD.state; END IF;
              IF NOT NEW.activation_requirements_instantiated THEN
                RAISE EXCEPTION 'GATE: activation requirements not instantiated'; END IF;
              SELECT count(*) INTO n FROM checklist_item
                WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
              IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
            ELSIF NEW.state = 'COMPLETED' THEN
              IF OLD.state <> 'ACTIVE' THEN RAISE EXCEPTION 'GATE: illegal transition % -> COMPLETED', OLD.state; END IF;
              SELECT count(*) INTO n FROM checklist_item
                WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
              IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
              IF NOT NEW.completion_requirements_instantiated THEN
                RAISE EXCEPTION 'GATE: completion requirements not instantiated'; END IF;
              SELECT count(*) INTO n FROM completion_requirement
                WHERE placement_id = NEW.id AND mandatory AND NOT satisfied;
              IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
            ELSIF NEW.state = 'CLOSED' THEN
              IF OLD.state <> 'COMPLETED' THEN RAISE EXCEPTION 'GATE: illegal transition % -> CLOSED', OLD.state; END IF;
              SELECT count(*) INTO n FROM checklist_item
                WHERE placement_id = NEW.id AND mandatory AND status <> 'APPROVED';
              IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory activation requirement(s) not approved', n; END IF;
              SELECT count(*) INTO n FROM completion_requirement
                WHERE placement_id = NEW.id AND mandatory AND NOT satisfied;
              IF n > 0 THEN RAISE EXCEPTION 'GATE: % mandatory completion requirement(s) unsatisfied', n; END IF;
            END IF;
          END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
    """)
