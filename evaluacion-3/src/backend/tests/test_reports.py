"""Operational reporting remains aggregate-only and limited to institutional scope."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_PASSWORD, make_active, make_opportunity, seed_base

ORIGIN = "http://localhost:5173"


def _client(identifier: str) -> TestClient:
    client = TestClient(app, base_url=ORIGIN)
    response = client.post("/auth/login", json={"identifier": identifier, "password": TEST_PASSWORD},
                           headers={"Origin": ORIGIN})
    assert response.status_code == 200
    return client


def test_operational_reports_are_aggregated_and_scoped_to_program(env):
    users = seed_base(env)
    systems = make_opportunity(env, 1, users["P"]["ING-SIS"], "Systems opening")
    business = make_opportunity(env, 2, users["P"]["ADM"], "Business opening")
    systems_placement = make_active(env, users, "s1", systems)
    make_active(env, users, "s3", business)
    env.admin.execute(
        "INSERT INTO placement_incident(placement_id,kind,revision,reporter_id,summary,description) "
        "VALUES (%s,'INCIDENT',1,%s,'Synthetic report','Synthetic body')",
        (systems_placement, users["s1"]),
    )
    env.admin.execute(
        "INSERT INTO checklist_item(placement_id,kind,mandatory,status) VALUES (%s,'DOC_SAMPLE',true,'REQUIRED')",
        (systems_placement,),
    )

    pc = _client("pc_sys")
    ec = _client("ec1")
    employer = _client("hm_alfa")
    try:
        program = pc.get("/reports/operations")
        assert program.status_code == 200, program.text
        data = program.json()
        assert data["active_placements"] == 1
        assert data["mandatory_documents_pending"] == 1
        assert data["reported_incidents"] == 1
        assert [row["program_code"] for row in data["by_program"]] == ["ING-SIS"]
        assert {row["organization"] for row in data["by_organization"]} == {"Org Alfa (synthetic)"}
        assert all("student" not in row and "evaluation" not in row for row in data["by_organization"])
        assert "Synthetic body" not in program.text and "Student One" not in program.text
        filtered = pc.get("/reports/operations", params={"program_id": users["P"]["ING-SIS"], "organization_id": 1,
                                                        "placement_state": "ACTIVE"})
        assert filtered.status_code == 200, filtered.text
        assert filtered.json()["active_placements"] == 1
        assert {row["program_code"] for row in filtered.json()["by_program"]} == {"ING-SIS"}
        assert pc.get("/reports/operations", params={"program_id": users["P"]["ADM"]}).status_code == 403

        institution = ec.get("/reports/operations")
        assert institution.status_code == 200
        assert institution.json()["active_placements"] == 2
        assert {row["program_code"] for row in institution.json()["by_program"]} == {"ING-SIS", "ADM"}
        assert employer.get("/reports/operations").status_code == 403
    finally:
        pc.close()
        ec.close()
        employer.close()
