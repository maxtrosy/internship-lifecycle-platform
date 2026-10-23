"""HTTP authorization and projection checks for relationship-scoped endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app.main import app
from tests.conftest import TEST_PASSWORD, make_doc_pending, make_opportunity, make_placement, seed_base

ORIGIN = "http://localhost:5173"


def _client(identifier: str) -> TestClient:
    client = TestClient(app, base_url=ORIGIN)
    response = client.post(
        "/auth/login",
        json={"identifier": identifier, "password": TEST_PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return client


def _item(env, placement_id: int, kind: str) -> int:
    return env.admin.execute(
        "SELECT id FROM checklist_item WHERE placement_id=%s AND kind=%s",
        (placement_id, kind),
    ).fetchone()["id"]


def test_http_authorization_matrix_crosses_roles_organizations_and_programs(env):
    users = seed_base(env)
    alfa = make_opportunity(env, 1, users["P"]["ING-SIS"], "Alfa")
    beta = make_opportunity(env, 2, users["P"]["ADM"], "Beta")
    pending_docs = make_doc_pending(env, users, "s1", alfa, docs_approved=False, supervisor="ws_alfa")
    pending_alfa = make_placement(env, users["s2"], alfa, supervisor_id=users["ws_alfa"])
    pending_beta = make_placement(env, users["s3"], beta, supervisor_id=users["ws_beta"])
    first_application = env.admin.execute(
        "SELECT id FROM application WHERE student_id=%s AND opportunity_id=%s",
        (users["s1"], alfa),
    ).fetchone()["id"]
    env.admin.execute(
        "UPDATE application SET eligibility_result=%s WHERE id=%s",
        (Jsonb({"result": "NOT_ELIGIBLE", "inputs": {"credits": 105, "academic_level": 7},
                "reasons": ["credits 105 < 110", "missing prerequisites ['MAT201']"]}),
         first_application),
    )

    clients = {name: _client(name) for name in (
        "s1", "s2", "s3", "hm_alfa", "hm_beta", "ws_alfa", "ws_alfa2",
        "pc_sys", "pc_adm", "ec1", "legal1",
    )}
    try:
        # Student lists are self-scoped; employers do not get a student-style list.
        assert [row["id"] for row in clients["s1"].get("/applications").json()] == [first_application]
        assert [row["id"] for row in clients["s2"].get("/applications").json()] == [
            env.admin.execute("SELECT id FROM application WHERE student_id=%s", (users["s2"],)).fetchone()["id"]
        ]
        assert clients["hm_alfa"].get("/applications").json() == []

        # Organization scoping applies to both the list and selection endpoints.
        received = clients["hm_alfa"].get(f"/opportunities/{alfa}/applications")
        assert received.status_code == 200
        first_row = next(row for row in received.json() if row["id"] == first_application)
        assert first_row["eligibility_result"] == {"result": "NOT_ELIGIBLE"}
        assert clients["hm_beta"].get(f"/opportunities/{alfa}/applications").status_code == 403
        assert clients["hm_beta"].post(
            f"/applications/{first_application}/select",
            json={"start_date": "2026-11-02", "end_date": "2027-02-26",
                  "location": "Site A", "responsibilities": "Synthetic"},
            headers={"Origin": ORIGIN},
        ).status_code == 403
        assert clients["hm_alfa"].post(
            f"/opportunities/{alfa}/apply", headers={"Origin": ORIGIN},
        ).status_code == 403

        # Direct object reads use student, organization, supervisor assignment, and program relations.
        assert clients["s1"].get(f"/placements/{pending_docs}").status_code == 200
        assert clients["s2"].get(f"/placements/{pending_docs}").status_code == 403
        assert clients["hm_beta"].get(f"/placements/{pending_docs}").status_code == 404
        assert clients["ws_alfa"].get(f"/placements/{pending_docs}").status_code == 200
        assert clients["ws_alfa2"].get(f"/placements/{pending_docs}").status_code == 404
        assert clients["pc_sys"].get(f"/placements/{pending_docs}").status_code == 200
        assert clients["pc_adm"].get(f"/placements/{pending_docs}").status_code == 403
        assert clients["legal1"].get(f"/placements/{pending_docs}").status_code == 200

        academic_sys = clients["pc_sys"].get("/placements/pending-academic")
        academic_adm = clients["pc_adm"].get("/placements/pending-academic")
        assert academic_sys.status_code == academic_adm.status_code == 200
        assert {row["id"] for row in academic_sys.json()} == {pending_alfa}
        assert {row["id"] for row in academic_adm.json()} == {pending_beta}
        assert clients["pc_adm"].post(
            f"/placements/{pending_alfa}/approve-academic", headers={"Origin": ORIGIN},
        ).status_code == 403
        assert clients["s1"].post(
            f"/placements/{pending_alfa}/approve-academic", headers={"Origin": ORIGIN},
        ).status_code == 403

        # Upload/read/review/download combine role and resource authorization.
        document_id = _item(env, pending_docs, "DOC_INSURANCE")
        upload = clients["s1"].post(
            f"/placements/{pending_docs}/items/{document_id}/submit?filename=insurance.pdf",
            content=b"%PDF-1.7 synthetic document",
            headers={"Origin": ORIGIN, "Content-Type": "application/pdf"},
        )
        assert upload.status_code == 201
        submissions_path = f"/placements/{pending_docs}/items/{document_id}/submissions"
        assert clients["s1"].get(submissions_path).status_code == 200
        assert clients["legal1"].get(submissions_path).status_code == 200
        assert clients["hm_alfa"].get(submissions_path).status_code == 403
        assert clients["s2"].get(submissions_path).status_code == 403

        legal_queue = clients["legal1"].get("/placements/documents-pending")
        assert legal_queue.status_code == 200
        assert any(row["id"] == pending_docs for row in legal_queue.json())
        assert clients["ec1"].get("/placements/documents-pending").status_code == 403
        assert clients["ec1"].get("/placements/pending-activation").status_code == 200
        assert clients["legal1"].get("/placements/pending-activation").status_code == 403

        submission_id = upload.json()["id"]
        download_path = f"{submissions_path}/{submission_id}/download"
        assert clients["legal1"].get(download_path).content.startswith(b"%PDF-")
        assert clients["hm_alfa"].get(download_path).status_code == 403
    finally:
        for client in clients.values():
            client.close()


def test_http_protected_endpoints_require_active_session(env):
    seed_base(env)
    from fastapi.testclient import TestClient

    with TestClient(app, base_url=ORIGIN) as client:
        assert client.get("/applications").status_code == 401
        assert client.get("/opportunities").status_code == 401
        assert client.get("/placements/pending-activation").status_code == 401
