"""HTTP behavior for durable notifications and audience-scoped practice messages."""
from __future__ import annotations

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app.main import app
from tests.conftest import TEST_PASSWORD, make_active, make_opportunity, seed_base

ORIGIN = "http://localhost:5173"


def client(identifier: str) -> TestClient:
    session = TestClient(app, base_url=ORIGIN)
    response = session.post(
        "/auth/login", json={"identifier": identifier, "password": TEST_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return session


def test_notifications_are_persistent_private_and_relationship_scoped(env):
    users = seed_base(env)
    opportunity_id = make_opportunity(env, 1, users["P"]["ING-SIS"])
    placement_id = make_active(env, users, "s1", opportunity_id)
    env.admin.execute(
        "INSERT INTO supervisor_assignment(placement_id,user_id,kind) VALUES (%s,%s,'FACULTY')",
        (placement_id, users["f1"]),
    )
    clients = {name: client(name) for name in ("s1", "s2", "ws_alfa", "f1", "pc_sys", "ec1", "hm_alfa")}
    try:
        response = clients["s1"].post(
            f"/placements/{placement_id}/progress-reports",
            json={"content": "Progreso persistido para aviso."}, headers={"Origin": ORIGIN},
        )
        assert response.status_code == 201, response.text

        for recipient in ("ws_alfa", "f1", "pc_sys", "ec1"):
            inbox = clients[recipient].get("/notifications")
            assert inbox.status_code == 200
            notice = next(row for row in inbox.json() if row["category"] == "PROGRESS_REPORTED")
            assert notice["placement_id"] == placement_id
            assert notice["is_read"] is False
            assert set(notice) == {"id", "category", "placement_id", "opportunity_id", "created_at", "read_at", "is_read"}
        assert clients["s1"].get("/notifications").json() == []
        assert clients["hm_alfa"].get("/notifications").json() == []
        assert clients["s2"].get("/notifications").json() == []

        ws_notice = next(row for row in clients["ws_alfa"].get("/notifications").json()
                         if row["category"] == "PROGRESS_REPORTED")
        denied = clients["s2"].post(
            f"/notifications/{ws_notice['id']}/read", headers={"Origin": ORIGIN},
        )
        assert denied.status_code == 404
        assert next(row for row in clients["ws_alfa"].get("/notifications").json()
                    if row["id"] == ws_notice["id"])["is_read"] is False

        read = clients["ws_alfa"].post(
            f"/notifications/{ws_notice['id']}/read", headers={"Origin": ORIGIN},
        )
        assert read.status_code == 200
        assert read.json()["id"] == ws_notice["id"]
        assert clients["ws_alfa"].get("/notifications").json()[0]["is_read"] is True
        assert clients["ws_alfa"].post(
            f"/notifications/{ws_notice['id']}/read", headers={"Origin": ORIGIN},
        ).status_code == 200
    finally:
        for session in clients.values():
            session.close()


def test_application_notice_skips_inactive_host_account(env):
    users = seed_base(env)
    opportunity_id = make_opportunity(env, 1, users["P"]["ING-SIS"])
    env.admin.execute(
        "INSERT INTO policy_version(policy_key,version_no,conditions,created_by) VALUES (%s,1,%s,%s)",
        ("ELIGIBILITY:ING-SIS", Jsonb([{"type": "CREDITS_MIN", "value": 0}]), users["pc_sys"]),
    )
    env.admin.execute("UPDATE user_account SET is_active=false WHERE id=%s", (users["hm_alfa"],))
    student = client("s1")
    try:
        response = student.post(f"/opportunities/{opportunity_id}/apply", headers={"Origin": ORIGIN})
        assert response.status_code == 201, response.text
        count = env.admin.execute(
            "SELECT count(*) AS count FROM user_notification WHERE recipient_id=%s", (users["hm_alfa"],)
        ).fetchone()["count"]
        assert count == 0
    finally:
        student.close()


def test_practice_messages_separate_academic_and_joint_audiences(env):
    users = seed_base(env)
    opportunity_id = make_opportunity(env, 1, users["P"]["ING-SIS"])
    placement_id = make_active(env, users, "s1", opportunity_id)
    env.admin.execute(
        "INSERT INTO supervisor_assignment(placement_id,user_id,kind) VALUES (%s,%s,'FACULTY')",
        (placement_id, users["f1"]),
    )
    clients = {name: client(name) for name in (
        "s1", "s2", "ws_alfa", "ws_alfa2", "f1", "pc_sys", "ec1", "hm_alfa", "legal1",
    )}
    try:
        base = f"/placements/{placement_id}/messages"
        academic = clients["s1"].post(
            base, json={"audience": "ACADEMIC", "content": "Consulta academica reservada."},
            headers={"Origin": ORIGIN},
        )
        assert academic.status_code == 201, academic.text
        for reader in ("f1", "pc_sys", "ec1"):
            result = clients[reader].get(base, params={"audience": "ACADEMIC"})
            assert result.status_code == 200
            assert result.json()[0]["content"] == "Consulta academica reservada."
        assert clients["ws_alfa"].get(base, params={"audience": "ACADEMIC"}).status_code == 403
        assert clients["ws_alfa"].post(
            base, json={"audience": "ACADEMIC", "content": "No autorizado."}, headers={"Origin": ORIGIN},
        ).status_code == 403
        assert clients["hm_alfa"].get(base, params={"audience": "ACADEMIC"}).status_code == 403
        assert clients["legal1"].get(base, params={"audience": "ACADEMIC"}).status_code == 403
        assert clients["s2"].get(base, params={"audience": "ACADEMIC"}).status_code == 403

        joint = clients["ws_alfa"].post(
            base, json={"audience": "JOINT", "content": "Coordinar el avance de práctica."},
            headers={"Origin": ORIGIN},
        )
        assert joint.status_code == 201, joint.text
        assert clients["s1"].get(base, params={"audience": "JOINT"}).json()[-1]["content"] == "Coordinar el avance de práctica."
        assert clients["f1"].get(base, params={"audience": "JOINT"}).status_code == 200
        assert clients["ws_alfa2"].get(base, params={"audience": "JOINT"}).status_code == 404
        assert clients["hm_alfa"].get(base, params={"audience": "JOINT"}).status_code == 403
        assert clients["s2"].post(
            base, json={"audience": "JOINT", "content": "Cruce."}, headers={"Origin": ORIGIN},
        ).status_code == 403

        reloaded = client("s1")
        try:
            assert reloaded.get(base, params={"audience": "ACADEMIC"}).json()[0]["author_name"] == "Student One"
            assert len(reloaded.get(base, params={"audience": "JOINT"}).json()) == 1
        finally:
            reloaded.close()
    finally:
        for session in clients.values():
            session.close()
