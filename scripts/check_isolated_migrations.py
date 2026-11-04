"""Verify fresh and incremental upgrades in disposable pgserver databases.

The script never reads or connects to an inherited DATABASE_URL. It creates a
fresh temporary PostgreSQL cluster, inserts one legacy incident at revision
0007, upgrades to head, and verifies the status backfill, closed work-plan guard,
    notification tables, audience-separated conversation tables, and opportunity workflow guard.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parents[1]
    backend = repo / "backend"
    sys.path.insert(0, str(backend))

    try:
        import pgserver
        import psycopg
        from psycopg.rows import dict_row
        from alembic import command
        from alembic.config import Config
    except ImportError as exc:
        raise RuntimeError(
            "Install backend dev dependencies (pgserver, psycopg and Alembic) before checking migrations."
        ) from exc

    with tempfile.TemporaryDirectory(prefix="dh05-migration-check-") as temporary:
        server = pgserver.get_server(str(pathlib.Path(temporary) / "postgres"))
        try:
            database_url = server.get_uri()
            os.environ["DATABASE_URL"] = database_url
            config = Config(str(backend / "alembic.ini"))
            config.set_main_option("script_location", str(backend / "migrations"))

            command.upgrade(config, "0001")
            with psycopg.connect(database_url) as conn:
                initial_status_exists = conn.execute(
                    """SELECT EXISTS (
                         SELECT 1 FROM information_schema.columns
                         WHERE table_name='placement_incident' AND column_name='status'
                       )""",
                ).fetchone()[0]
            if initial_status_exists:
                raise AssertionError("The initial 0001 schema unexpectedly contains incident status.")

            command.upgrade(config, "0007")
            from app.seed import seed

            with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
                users = seed(conn.cursor())
                opportunity_id = conn.execute(
                    """INSERT INTO opportunity(host_org_id,program_id,title)
                       VALUES (1,%s,'Isolated migration fixture') RETURNING id""",
                    (users["programs"]["ING-SIS"],),
                ).fetchone()["id"]
                application_id = conn.execute(
                    """INSERT INTO application(opportunity_id,student_id,state)
                       VALUES (%s,%s,'SELECTED') RETURNING id""",
                    (opportunity_id, users["s1"]),
                ).fetchone()["id"]
                placement_id = conn.execute(
                    "INSERT INTO placement(application_id,state) VALUES (%s,'ACTIVE') RETURNING id",
                    (application_id,),
                ).fetchone()["id"]
                version_id = conn.execute(
                    """INSERT INTO placement_version(placement_id,version_no,workplace_supervisor_id,
                       start_date,end_date,location,responsibilities,status)
                       VALUES (%s,1,%s,'2026-11-02','2027-02-26','Sede temporal',
                       'Relación de prueba aislada','APPROVED') RETURNING id""",
                    (placement_id, users["ws_alfa"]),
                ).fetchone()["id"]
                conn.execute(
                    "UPDATE placement SET current_version_id=%s WHERE id=%s", (version_id, placement_id),
                )
                conn.execute(
                    """INSERT INTO placement_incident(placement_id,kind,revision,reporter_id,summary,description)
                       VALUES (%s,'INCIDENT',1,%s,'Registro anterior a 0008','Fila sintética de migración')""",
                    (placement_id, users["s1"]),
                )

            command.upgrade(config, "head")
            with psycopg.connect(database_url) as conn:
                head = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                migrated_status = conn.execute(
                    "SELECT status FROM placement_incident WHERE placement_id=%s", (placement_id,),
                ).fetchone()[0]
                guard = conn.execute(
                    "SELECT pg_get_functiondef('trg_work_plan_assignment_guard()'::regprocedure)",
                ).fetchone()[0]
                tables = conn.execute(
                    """SELECT table_name FROM information_schema.tables
                       WHERE table_schema='public' AND table_name IN
                         ('user_notification','placement_conversation','placement_message')"""
                ).fetchall()
                opportunity_default = conn.execute(
                    "SELECT column_default FROM information_schema.columns WHERE table_name='opportunity' AND column_name='state'",
                ).fetchone()[0]
                opportunity_guard = conn.execute(
                    "SELECT pg_get_functiondef('trg_opportunity_state_guard()'::regprocedure)",
                ).fetchone()[0]
                notification_constraint = conn.execute(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='user_notification_category_check'",
                ).fetchone()[0]
                assignment_tables = conn.execute(
                    "SELECT to_regclass('public.placement_faculty_assignment_history')",
                ).fetchone()[0]
            if head != "0012":
                raise AssertionError(f"Expected Alembic head 0012, got {head}.")
            if migrated_status != "REPORTED":
                raise AssertionError(f"Existing incident received unexpected status {migrated_status!r}.")
            if "placement closure" not in guard:
                raise AssertionError("The migrated work-plan guard does not reject inserts after closure.")
            if {row[0] for row in tables} != {"user_notification", "placement_conversation", "placement_message"}:
                raise AssertionError("The migrated notification/conversation tables are incomplete.")
            if "DRAFT" not in opportunity_default or "IN_REVIEW" not in opportunity_guard:
                raise AssertionError("The opportunity state default or transition guard is incomplete.")
            if "OPPORTUNITY_PUBLISHED" not in notification_constraint:
                raise AssertionError("The opportunity notification categories are absent from the schema.")
            if assignment_tables is None:
                raise AssertionError("Faculty assignment history table was not installed.")

            print(
                "MIGRATION_CHAIN=0001->0012; initial_status_absent=true; "
                f"legacy_incident_status={migrated_status}; closed_work_plan_guard=true; "
                "notifications_and_audience_scoped_messages=true; opportunity_state_guard=true; "
                "faculty_assignment_history=true"
            )
        finally:
            server.cleanup()
        second = pgserver.get_server(str(pathlib.Path(temporary) / "postgres-0010"))
        try:
            database_url = second.get_uri()
            os.environ["DATABASE_URL"] = database_url
            command.upgrade(config, "0010")
            command.upgrade(config, "0011")
            with psycopg.connect(database_url) as conn:
                head_0011 = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                if head_0011 != "0011":
                    raise AssertionError(f"Expected intermediate Alembic revision 0011, got {head_0011}.")
            command.upgrade(config, "0012")
            with psycopg.connect(database_url) as conn:
                head_0012 = conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]
                state_default_0010 = conn.execute(
                    "SELECT column_default FROM information_schema.columns WHERE table_name='opportunity' AND column_name='state'",
                ).fetchone()[0]
                assignment_history = conn.execute(
                    "SELECT to_regclass('public.placement_faculty_assignment_history')",
                ).fetchone()[0]
            if head_0012 != "0012" or "DRAFT" not in state_default_0010 or assignment_history is None:
                raise AssertionError("Upgrade from the existing 0010 schema did not install 0011/0012.")
            print("MIGRATION_UPGRADE=0010->0011->0012; opportunity_state_guard=true; faculty_assignment_history=true")
        finally:
            second.cleanup()
    print("TEMPORARY_POSTGRES_CLEANED=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
