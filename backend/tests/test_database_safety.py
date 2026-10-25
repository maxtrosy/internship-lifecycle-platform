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
