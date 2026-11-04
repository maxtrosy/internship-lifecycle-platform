"""The database-backed suite must never truncate a shared database by accident."""

import pytest

from tests.conftest import DbEnv, is_test_database_url


def test_only_the_isolated_compose_test_database_is_accepted():
    assert is_test_database_url("postgresql://postgres:dh05-test-only@db:5432/dh05_http_test")


def test_shared_database_names_are_rejected():
    assert not is_test_database_url("postgresql://postgres:postgres@db:5432/postgres")
    assert not is_test_database_url("dbname=dh05_demo user=postgres")
    assert not is_test_database_url("postgresql://postgres:secret@localhost:5432/dh05_release_test")
    assert not is_test_database_url("postgresql://postgres:secret@shared-db:5432/dh05_http_test")


def test_database_fixture_refuses_a_shared_database(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/dh05_demo")

    with pytest.raises(RuntimeError, match="Refusing to run destructive tests"):
        DbEnv()


def test_application_role_has_only_service_dml_and_required_sequences(env):
    role = env.admin.execute(
        """SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                  rolreplication, rolbypassrls
           FROM pg_roles WHERE rolname='app_user'"""
    ).fetchone()
    assert role == {
        "rolcanlogin": False,
        "rolsuper": False,
        "rolcreatedb": False,
        "rolcreaterole": False,
        "rolreplication": False,
        "rolbypassrls": False,
    }

    with env.conn() as conn:
        assert conn.execute("SELECT current_user AS role_name").fetchone()["role_name"] == "app_user"

        def has_permission(query: str, *params: str) -> bool:
            return conn.execute(query + " AS allowed", params or None).fetchone()["allowed"]

        assert has_permission("SELECT has_table_privilege('app_user','opportunity','INSERT')")
        assert has_permission("SELECT has_table_privilege('app_user','placement','UPDATE')")
        assert has_permission("SELECT has_table_privilege('app_user','supervisor_assignment','DELETE')")
        assert has_permission(
            "SELECT has_table_privilege('app_user','v_placement_activation_compliance','SELECT')"
        )
        assert conn.execute(
            "SELECT has_table_privilege('app_user','audit_event','INSERT') AS allowed"
        ).fetchone()["allowed"]
        for privilege in ("UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            assert not has_permission(
                "SELECT has_table_privilege('app_user','audit_event',%s)", privilege
            )
        assert has_permission("SELECT has_sequence_privilege('app_user','application_id_seq','USAGE')")
        assert not has_permission("SELECT has_sequence_privilege('app_user','academic_program_id_seq','USAGE')")
        assert not has_permission("SELECT has_schema_privilege('app_user','public','CREATE')")
        assert not has_permission(
            "SELECT has_database_privilege('app_user',current_database(),'CREATE')"
        )
