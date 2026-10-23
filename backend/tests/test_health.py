"""Smoke test for the health endpoint (no HTTP client dependency)."""
from __future__ import annotations

from app.main import health


def test_health():
    assert health() == {"status": "ok"}
