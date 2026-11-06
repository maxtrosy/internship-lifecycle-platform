"""T-07 port: audit history is append-only for the app role and the table owner."""
from __future__ import annotations

import psycopg
import pytest

from app import db
from app.modules.lifecycle import service as lc
from tests.conftest import make_doc_pending, make_opportunity, seed_base


def test_t07_audit_append_only(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_doc_pending(env, U, "s1", opp)
    with db.command(U["ec1"]) as ctx:
        lc.activate(ctx, p)

    app = env.conn()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app.execute("UPDATE audit_event SET action='x' WHERE subject_id=%s", (p,))
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        app.execute("DELETE FROM audit_event WHERE subject_id=%s", (p,))
    app.close()

    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("UPDATE audit_event SET action='x' WHERE subject_id=%s", (p,))
    with pytest.raises(psycopg.errors.RaiseException):
        env.admin.execute("DELETE FROM audit_event WHERE subject_id=%s", (p,))

    intact = env.admin.execute(
        "SELECT count(*) AS n FROM audit_event WHERE subject_id=%s AND action='placement.activated'", (p,)
    ).fetchone()["n"]
    assert intact == 1
