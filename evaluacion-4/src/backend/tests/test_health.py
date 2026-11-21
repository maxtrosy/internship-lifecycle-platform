"""Smoke test for the health endpoint (no HTTP client dependency)."""
from __future__ import annotations

from contextlib import contextmanager

from app import main
from fastapi.testclient import TestClient


def test_health():
    assert main.health() == {"status": "ok"}


def test_readiness_endpoint_checks_the_temporary_database(env):
    with TestClient(main.app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_confirms_latest_schema_and_application_role(monkeypatch):
    class Cursor:
        def execute(self, query):
            assert "placement_faculty_assignment_history" in query
            return self

        def fetchone(self):
            return {"schema_ready": True}

    @contextmanager
    def read():
        yield Cursor()

    monkeypatch.setattr(main.db, "read", read)
    assert main.readiness() == {"status": "ready"}


def test_readiness_does_not_expose_database_errors(monkeypatch):
    @contextmanager
    def read():
        raise RuntimeError("database connection details must not be returned")
        yield  # pragma: no cover

    monkeypatch.setattr(main.db, "read", read)
    response = main.readiness()
    assert response.status_code == 503
    assert response.body == b'{"status":"not_ready"}'
