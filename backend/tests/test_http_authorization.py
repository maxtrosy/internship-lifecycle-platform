"""HTTP authorization and projection checks for relationship-scoped endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app.main import app
from tests.conftest import TEST_PASSWORD, make_active, make_doc_pending, make_opportunity, make_placement, seed_base

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
    env.admin.execute(
        """INSERT INTO audit_event(actor_id, action, subject_type, subject_id, before_state, after_state, correlation_id)
           VALUES (%s, 'placement.history_projection_test', 'placement', %s, %s, %s, 'test-correlation')""",
        (users["s1"], pending_docs, Jsonb({"private": "before payload"}), Jsonb({"private": "after payload"})),
    )
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
        "s1", "s2", "s3", "hm_alfa", "hm_beta", "ws_alfa", "ws_alfa2", "ws_beta",
        "pc_sys", "pc_adm", "ec1", "legal1",
    )}
    try:
        # Creation catalogs are scoped to the caller's creator relationships.
        employer_catalogs = clients["hm_alfa"].get("/opportunities/catalogs")
        assert employer_catalogs.status_code == 200
        assert [row["id"] for row in employer_catalogs.json()["organizations"]] == [1]
        assert {row["code"] for row in employer_catalogs.json()["programs"]} == {"ING-SIS", "ADM"}
        coordinator_catalogs = clients["pc_sys"].get("/opportunities/catalogs")
        assert coordinator_catalogs.status_code == 200
        assert {row["id"] for row in coordinator_catalogs.json()["organizations"]} == {1, 2}
        assert [row["code"] for row in coordinator_catalogs.json()["programs"]] == ["ING-SIS"]
        assert clients["s1"].get("/opportunities/catalogs").status_code == 403
        assert clients["ws_alfa"].get("/opportunities/catalogs").status_code == 403

        supervisor_catalog = clients["hm_alfa"].get(f"/opportunities/{alfa}/workplace-supervisors")
        assert supervisor_catalog.status_code == 200
        assert {row["id"] for row in supervisor_catalog.json()} == {users["ws_alfa"], users["ws_alfa2"]}
        assert clients["hm_beta"].get(f"/opportunities/{alfa}/workplace-supervisors").status_code == 403
        assert clients["ws_beta"].get(f"/opportunities/{alfa}/workplace-supervisors").status_code == 403
        assert clients["s1"].get(f"/opportunities/{alfa}/workplace-supervisors").status_code == 403

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
        student_history = clients["s1"].get(f"/placements/{pending_docs}/history")
        assert student_history.status_code == 200
        assert [event["action"] for event in student_history.json()] == ["placement.history_projection_test"]
        assert all(set(event) == {"occurred_at", "action"} for event in student_history.json())
        assert "private" not in student_history.text and "test-correlation" not in student_history.text
        assert clients["s2"].get(f"/placements/{pending_docs}/history").status_code == 403
        assert clients["hm_beta"].get(f"/placements/{pending_docs}/history").status_code == 404
        assert clients["ws_alfa2"].get(f"/placements/{pending_docs}/history").status_code == 404
        assert clients["pc_adm"].get(f"/placements/{pending_docs}/history").status_code == 403
        assert clients["legal1"].get(f"/placements/{pending_docs}/history").status_code == 200

        # Progress is student-owned and cannot be entered before activation.
        hours_path = f"/placements/{pending_docs}/hours"
        own_hours = clients["s1"].get(hours_path)
        assert own_hours.status_code == 200 and own_hours.json() == []
        assert clients["s2"].get(hours_path).status_code == 403
        assert clients["hm_alfa"].get(hours_path).status_code == 403
        assert clients["s2"].post(hours_path, json={"hours": 2}, headers={"Origin": ORIGIN}).status_code == 403
        assert clients["hm_alfa"].post(hours_path, json={"hours": 2}, headers={"Origin": ORIGIN}).status_code == 403
        assert clients["s1"].post(hours_path, json={"hours": 0}, headers={"Origin": ORIGIN}).status_code == 422
        inactive_hours = clients["s1"].post(hours_path, json={"hours": 2}, headers={"Origin": ORIGIN})
        assert inactive_hours.status_code == 409
        assert inactive_hours.json()["error"] == "PLACEMENT_NOT_ACTIVE"
        assert env.admin.execute("SELECT count(*) AS n FROM progress_entry WHERE placement_id=%s", (pending_docs,)).fetchone()["n"] == 0

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


def test_placement_dossier_is_persisted_and_scoped_by_relationship(env):
    users = seed_base(env)
    alfa = make_opportunity(env, 1, users["P"]["ING-SIS"], "Dossier Alfa")
    beta = make_opportunity(env, 2, users["P"]["ADM"], "Dossier Beta")
    active = make_active(env, users, "s1", alfa)
    pending_same_org = make_placement(env, users["s2"], alfa, supervisor_id=users["ws_alfa"])
    other_org = make_placement(env, users["s3"], beta, supervisor_id=users["ws_beta"])
    env.admin.execute(
        "INSERT INTO supervisor_assignment VALUES (%s,%s,'FACULTY')", (active, users["f1"]),
    )
    application_id = env.admin.execute(
        "SELECT application_id FROM placement WHERE id=%s", (active,),
    ).fetchone()["application_id"]
    env.admin.execute(
        "UPDATE application SET eligibility_result=%s WHERE id=%s",
        (Jsonb({"result": "ELIGIBLE", "unexpected_private_payload": "must not be returned"}), application_id),
    )
    pending_application_id = env.admin.execute(
        "SELECT application_id FROM placement WHERE id=%s", (pending_same_org,),
    ).fetchone()["application_id"]
    env.admin.execute(
        "UPDATE application SET eligibility_result=%s WHERE id=%s",
        (Jsonb({"future_shape": ["unknown"]}), pending_application_id),
    )
    item_id = _item(env, active, "DOC_INSURANCE")
    first = env.admin.execute(
        """INSERT INTO document_submission(checklist_item_id,revision,submitted_by,original_filename,
           content_type,content,byte_size,sha256) VALUES (%s,1,%s,'insurance-v1.pdf','application/pdf',
           %s,5,'hash-one') RETURNING id""",
        (item_id, users["s1"], b"%PDF-"),
    ).fetchone()["id"]
    second = env.admin.execute(
        """INSERT INTO document_submission(checklist_item_id,revision,submitted_by,original_filename,
           content_type,content,byte_size,sha256) VALUES (%s,2,%s,'insurance-v2.pdf','application/pdf',
           %s,5,'hash-two') RETURNING id""",
        (item_id, users["s1"], b"%PDF-"),
    ).fetchone()["id"]
    env.admin.execute("UPDATE checklist_item SET current_submission_id=%s WHERE id=%s", (second, item_id))
    env.admin.execute(
        "INSERT INTO document_review(checklist_item_id,submission_id,reviewer_id,decision,reason) "
        "VALUES (%s,%s,%s,'REJECTED','Versión anterior incompleta.')",
        (item_id, first, users["legal1"]),
    )
    env.admin.execute("INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,4.5)",
                      (active, users["s1"]))
    for action in ("application.submitted", "application.selected"):
        env.admin.execute(
            """INSERT INTO audit_event(actor_id,action,subject_type,subject_id,correlation_id)
               VALUES (%s,%s,'application',%s,'dossier-test')""",
            (users["s1"], action, application_id),
        )

    clients = {name: _client(name) for name in (
        "s1", "s2", "s3", "hm_alfa", "hm_beta", "ws_alfa", "ws_alfa2", "ws_beta",
        "pc_sys", "pc_adm", "f1", "ec1", "legal1",
    )}
    try:
        # Collection projections are scoped in the query itself.
        assert [row["id"] for row in clients["s1"].get("/placements").json()] == [active]
        assert {row["id"] for row in clients["hm_alfa"].get("/placements").json()} == {active, pending_same_org}
        assert [row["id"] for row in clients["hm_beta"].get("/placements").json()] == [other_org]
        assert {row["id"] for row in clients["pc_sys"].get("/placements").json()} == {active, pending_same_org}
        assert [row["id"] for row in clients["f1"].get("/placements").json()] == [active]
        assert clients["ws_alfa"].get("/placements").status_code == 200
        assert clients["ws_alfa2"].get("/placements").json() == []

        own = clients["s1"].get(f"/placements/{active}/dossier")
        assert own.status_code == 200
        data = own.json()
        assert data["opportunity"]["title"] == "Dossier Alfa"
        assert data["application"]["state"] == "SELECTED"
        assert data["application"]["eligibility_result"] == "ELIGIBLE"
        assert data["application"]["eligibility_policy_version"] is None
        assert data["placement"]["state"] == "ACTIVE"
        assert data["current_version"]["workplace_supervisor_name"] == "Workplace Sup Alfa"
        assert data["responsibles"]["faculty_supervisors"] == ["Faculty Sup 1"]
        assert data["documents"] is not None
        insurance = next(entry for entry in data["documents"] if entry["kind"] == "DOC_INSURANCE")
        assert [version["revision"] for version in insurance["versions"]] == [2, 1]
        assert insurance["versions"][1]["reason"] == "Versión anterior incompleta."
        assert float(data["hours_total"]) == 4.5
        assert data["capabilities"]["read_documents"] is True
        assert data["capabilities"]["submit_documents"] is False
        assert data["capabilities"]["record_hours"] is True
        assert data["capabilities"]["review_documents"] is False
        assert data["capabilities"]["activate"] is False
        assert data["capabilities"]["confirm_completion"] is False
        assert data["capabilities"]["close_placement"] is False
        assert data["completion_requirements"] is not None
        assert [event["action"] for event in data["activity"][:2]] == [
            "application.submitted", "application.selected",
        ]
        assert "unexpected_private_payload" not in own.text
        assert "dossier-test" not in own.text

        work_plan_path = f"/placements/{active}/work-plan"
        assert clients["s1"].get(work_plan_path).json() == []
        assert clients["s1"].post(
            work_plan_path, json={"title": "No autorizado", "description": "El estudiante no asigna actividades."},
            headers={"Origin": ORIGIN},
        ).status_code == 403
        assert clients["ws_alfa2"].post(
            work_plan_path, json={"title": "No asignado", "description": "Supervisor de otra práctica."},
            headers={"Origin": ORIGIN},
        ).status_code == 404
        assert clients["hm_alfa"].post(
            work_plan_path, json={"title": "No autorizado", "description": "Miembro anfitrión sin asignación WPS."},
            headers={"Origin": ORIGIN},
        ).status_code == 403
        assert clients["ws_alfa"].post(
            work_plan_path, json={"title": "   ", "description": "   "}, headers={"Origin": ORIGIN},
        ).status_code == 409
        assert clients["ws_alfa"].post(
            work_plan_path, json={"title": "t" * 161, "description": "Descripción válida."},
            headers={"Origin": ORIGIN},
        ).status_code == 422
        assigned = clients["ws_alfa"].post(
            work_plan_path,
            json={"title": "Preparar inventario", "description": "Documentar los pasos observados en el proceso."},
            headers={"Origin": ORIGIN},
        )
        assert assigned.status_code == 201, assigned.text
        assert set(assigned.json()) == {"revision", "assigned_at"}
        assert assigned.json()["revision"] == 1
        assigned_second = clients["ws_alfa"].post(
            work_plan_path,
            json={"title": "Analizar resultados", "description": "Resumir hallazgos para la siguiente reunión."},
            headers={"Origin": ORIGIN},
        )
        assert assigned_second.status_code == 201, assigned_second.text
        assert assigned_second.json()["revision"] == 2
        plan = clients["s1"].get(work_plan_path)
        assert plan.status_code == 200
        first_plan_item = plan.json()[0]
        assert set(first_plan_item) == {"revision", "title", "description", "assigned_at", "assigned_by"}
        assert first_plan_item["revision"] == 1
        assert first_plan_item["title"] == "Preparar inventario"
        assert first_plan_item["description"] == "Documentar los pasos observados en el proceso."
        assert first_plan_item["assigned_at"] is not None
        assert first_plan_item["assigned_by"] == "Workplace Sup Alfa"
        assert clients["f1"].get(work_plan_path).status_code == 200
        assert clients["pc_sys"].get(work_plan_path).status_code == 200
        assert clients["ec1"].get(work_plan_path).status_code == 200
        assert clients["legal1"].get(work_plan_path).status_code == 403
        assert clients["hm_alfa"].get(work_plan_path).status_code == 403
        assert clients["ws_beta"].get(work_plan_path).status_code == 404
        plan_dossier = clients["s1"].get(f"/placements/{active}/dossier").json()
        assert [item["revision"] for item in plan_dossier["work_plan"]] == [1, 2]
        assert plan_dossier["capabilities"]["read_work_plan"] is True
        assert plan_dossier["capabilities"]["assign_work_plan_item"] is False
        host = clients["hm_alfa"].get(f"/placements/{active}/dossier").json()
        assert host["work_plan"] is None
        assert host["capabilities"]["read_work_plan"] is False
        assert "work_plan.activity_assigned" in [event["action"] for event in plan_dossier["activity"]]

        # Organization readers get only their linked practices and no document, hour,
        # or completion evidence projection. External student identity follows BR-13.
        host = clients["hm_alfa"].get(f"/placements/{active}/dossier")
        assert host.status_code == 200
        host_data = host.json()
        assert host_data["student"] == {"display_name": "Student One", "program_code": "ING-SIS"}
        assert host_data["documents"] is None and host_data["hours"] is None
        assert host_data["completion_requirements"] is None
        assert host_data["capabilities"]["read_documents"] is False
        assert host_data["capabilities"]["record_hours"] is False
        assert host_data["capabilities"]["confirm_completion"] is False
        assert host_data["capabilities"]["close_placement"] is False

        pending_data = clients["pc_sys"].get(f"/placements/{pending_same_org}/dossier").json()
        assert pending_data["application"]["eligibility_result"] is None
        assert pending_data["placement"]["activation_ready"] is False
        assert pending_data["capabilities"]["decide_academically"] is True
        assert pending_data["capabilities"]["activate"] is False
        assert pending_data["capabilities"]["confirm_completion"] is False
        assert pending_data["capabilities"]["close_placement"] is False

        active_coordinator = clients["pc_sys"].get(f"/placements/{active}/dossier").json()
        assert active_coordinator["capabilities"]["confirm_completion"] is True
        assert active_coordinator["capabilities"]["close_placement"] is False
        active_ec = clients["ec1"].get(f"/placements/{active}/dossier").json()
        assert active_ec["capabilities"]["confirm_completion"] is False
        assert active_ec["capabilities"]["close_placement"] is False

        assert clients["s2"].get(f"/placements/{active}/dossier").status_code == 403
        assert clients["hm_beta"].get(f"/placements/{active}/dossier").status_code == 404
        assert clients["ws_alfa2"].get(f"/placements/{active}/dossier").status_code == 404
        assert clients["pc_adm"].get(f"/placements/{active}/dossier").status_code == 403
        assert clients["pc_sys"].get(f"/placements/{active}/dossier").status_code == 200
        assert clients["f1"].get(f"/placements/{active}/dossier").status_code == 200
        legal_data = clients["legal1"].get(f"/placements/{active}/dossier").json()
        assert legal_data["documents"] is not None
        assert legal_data["hours"] is None
        assert legal_data["capabilities"]["review_documents"] is True

        # Progress, evaluation, incident/change reporting and final evidence are
        # persisted records with relationship-scoped access and append-only history.
        progress_path = f"/placements/{active}/progress-reports"
        progress = clients["s1"].post(
            progress_path, json={"content": "Avance sintético de la actividad asignada."},
            headers={"Origin": ORIGIN},
        )
        assert progress.status_code == 201, progress.text
        progress_projection = clients["ws_alfa"].get(progress_path)
        assert progress_projection.status_code == 200
        assert set(progress_projection.json()[0]) == {"revision", "content", "created_at", "author"}
        assert progress_projection.json()[0]["content"].startswith("Avance")
        assert clients["f1"].get(progress_path).status_code == 200
        assert clients["hm_alfa"].get(progress_path).status_code == 403
        assert clients["s2"].get(progress_path).status_code == 403

        incident_path = f"/placements/{active}/incidents"
        incident = clients["s1"].post(
            incident_path,
            json={"kind": "CHANGE", "summary": "Cambio de horario propuesto",
                  "description": "Se reporta una modificación para revisión por las personas relacionadas."},
            headers={"Origin": ORIGIN},
        )
        assert incident.status_code == 201, incident.text
        assert incident.json()["status"] == "REPORTED"
        incident_projection = clients["pc_sys"].get(incident_path)
        assert set(incident_projection.json()[0]) == {
            "kind", "revision", "status", "summary", "description", "reported_at", "reporter",
        }
        assert incident_projection.json()[0]["kind"] == "CHANGE"
        assert incident_projection.json()[0]["status"] == "REPORTED"
        assert clients["ws_alfa"].get(incident_path).status_code == 200
        assert clients["hm_alfa"].get(incident_path).status_code == 403
        assert clients["s2"].get(incident_path).status_code == 403

        evaluations_path = f"/placements/{active}/evaluations"
        assert clients["s1"].post(
            evaluations_path, json={"kind": "FINAL", "narrative": "No autorizado."},
            headers={"Origin": ORIGIN},
        ).status_code == 403
        assert clients["ws_alfa2"].post(
            evaluations_path, json={"kind": "FINAL", "narrative": "Supervisor no asignado."},
            headers={"Origin": ORIGIN},
        ).status_code == 404
        final_evaluation = clients["ws_alfa"].post(
            evaluations_path,
            json={"kind": "FINAL", "narrative": "Evaluación final narrativa basada en evidencia de la práctica."},
            headers={"Origin": ORIGIN},
        )
        assert final_evaluation.status_code == 201, final_evaluation.text
        evaluation_projection = clients["s1"].get(evaluations_path)
        assert set(evaluation_projection.json()[0]) == {
            "kind", "revision", "narrative", "submitted_at", "evaluator",
        }
        assert evaluation_projection.json()[0]["kind"] == "FINAL"
        assert clients["f1"].get(evaluations_path).status_code == 200
        assert clients["hm_alfa"].get(evaluations_path).status_code == 403

        final_evidence_path = f"/placements/{active}/completion-evidence"
        assert clients["s1"].post(
            f"/placements/{active}/submit-evidence", json={"kind": "FINAL_REPORT"},
            headers={"Origin": ORIGIN},
        ).status_code == 404
        final_report = clients["s1"].post(
            f"{final_evidence_path}/FINAL_REPORT?filename=informe-final.pdf",
            content=b"%PDF-1.7 synthetic final report",
            headers={"Origin": ORIGIN, "Content-Type": "application/pdf"},
        )
        assert final_report.status_code == 201, final_report.text
        report_revision = final_report.json()["revision"]
        report_rows = clients["s1"].get(final_evidence_path)
        assert report_rows.status_code == 200
        assert set(report_rows.json()[0]) == {
            "kind", "revision", "original_filename", "content_type", "byte_size",
            "sha256", "submitted_at", "submitted_by",
        }
        assert report_rows.json()[0]["revision"] == report_revision
        assert clients["s1"].get(
            f"{final_evidence_path}/FINAL_REPORT/{report_revision}/download",
        ).content.startswith(b"%PDF-")
        assert clients["ws_alfa"].get(final_evidence_path).status_code == 403
        assert clients["hm_alfa"].get(final_evidence_path).status_code == 403
        assert clients["pc_sys"].get(final_evidence_path).status_code == 200
        assert clients["s2"].get(final_evidence_path).status_code == 403

        # Completion availability is projected only to authorized internal roles and
        # follows the persisted policy requirements already attached to this placement.
        env.admin.execute("INSERT INTO progress_entry(placement_id,student_id,hours) VALUES (%s,%s,100)",
                          (active, users["s1"]))
        confirmation = clients["pc_sys"].post(
            f"/placements/{active}/confirm-completion", headers={"Origin": ORIGIN},
        )
        assert confirmation.status_code == 204, confirmation.text
        completed = clients["ec1"].get(f"/placements/{active}/dossier").json()
        assert completed["placement"]["state"] == "COMPLETED"
        assert completed["capabilities"]["confirm_completion"] is False
        assert completed["capabilities"]["close_placement"] is True
        assert completed["hours"] is None
        assert completed["completion_requirements"] is not None
        assert all(item["satisfied"] for item in completed["completion_requirements"])

        hours_after_completion = clients["s1"].get(f"/placements/{active}/hours")
        assert hours_after_completion.status_code == 200
        assert sum(float(entry["hours"]) for entry in hours_after_completion.json()) == 104.5
        student_completed = clients["s1"].get(f"/placements/{active}/dossier").json()
        assert student_completed["placement"]["state"] == "COMPLETED"
        assert float(student_completed["hours_total"]) == 104.5
        assert student_completed["hours"] is not None

        closure = clients["ec1"].post(
            f"/placements/{active}/close", headers={"Origin": ORIGIN},
        )
        assert closure.status_code == 204, closure.text
        closed = clients["s1"].get(f"/placements/{active}/dossier").json()
        assert closed["placement"]["state"] == "CLOSED"
        assert float(closed["hours_total"]) == 104.5
        assert closed["hours"] is not None
        assert all(set(event) == {"occurred_at", "action"} for event in closed["activity"])
        closed_hours_write = clients["s1"].post(
            f"/placements/{active}/hours", json={"hours": 1}, headers={"Origin": ORIGIN},
        )
        assert closed_hours_write.status_code == 409
        assert closed_hours_write.json()["error"] == "PLACEMENT_NOT_ACTIVE"
        hours_after_rejected_write = clients["s1"].get(f"/placements/{active}/hours")
        assert hours_after_rejected_write.status_code == 200
        assert sum(float(entry["hours"]) for entry in hours_after_rejected_write.json()) == 104.5
    finally:
        for client in clients.values():
            client.close()
