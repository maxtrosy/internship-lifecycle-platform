"""Run the Chromium lifecycle E2E against a disposable local pgserver database.

Requirements: backend dev dependencies (including pgserver), Node dependencies in
frontend/, and an installed Playwright Chromium browser. The script never reads an
existing DATABASE_URL; it replaces it with the URI of a fresh temporary database.
"""
from __future__ import annotations

import os
import pathlib
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import argparse
import urllib.error
import urllib.request


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for(url: str, children: tuple[subprocess.Popen, ...], timeout: float = 60) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(child.poll() is not None for child in children):
            return False
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    return False


def seed_assigned_faculty_practice(cur) -> None:
    """Add one role-relation fixture only to this runner's disposable database."""
    users = {
        row["username"]: row["id"]
        for row in cur.execute(
            "SELECT id, username FROM user_account WHERE username IN ('s3','ws_alfa','f1','pc_adm')"
        ).fetchall()
    }
    program_id = cur.execute(
        "SELECT id FROM academic_program WHERE code='ADM'"
    ).fetchone()["id"]
    organization_id = cur.execute(
        "SELECT id FROM host_org WHERE name='Org Alfa (synthetic)'"
    ).fetchone()["id"]
    opportunity_id = cur.execute(
        """INSERT INTO opportunity(host_org_id,program_id,title)
           VALUES (%s,%s,'E2E faculty assigned practice') RETURNING id""",
        (organization_id, program_id),
    ).fetchone()["id"]
    application_id = cur.execute(
        """INSERT INTO application(opportunity_id,student_id,state)
           VALUES (%s,%s,'SELECTED') RETURNING id""",
        (opportunity_id, users["s3"]),
    ).fetchone()["id"]
    placement_id = cur.execute(
        "INSERT INTO placement(application_id,state) VALUES (%s,'ACTIVE') RETURNING id",
        (application_id,),
    ).fetchone()["id"]
    version_id = cur.execute(
        """INSERT INTO placement_version(placement_id,version_no,workplace_supervisor_id,
           start_date,end_date,location,responsibilities,status,decided_by)
           VALUES (%s,1,%s,'2026-11-02','2027-02-26','Sede de pruebas aislada',
           'Relación docente sintética para E2E','APPROVED',%s) RETURNING id""",
        (placement_id, users["ws_alfa"], users["pc_adm"]),
    ).fetchone()["id"]
    cur.execute("UPDATE placement SET current_version_id=%s WHERE id=%s", (version_id, placement_id))
    cur.execute(
        "INSERT INTO supervisor_assignment(placement_id,user_id,kind) VALUES (%s,%s,'FACULTY')",
        (placement_id, users["f1"]),
    )


def stop(child: subprocess.Popen | None) -> None:
    if child is None or child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--populated", action="store_true",
        help="seed a connected synthetic ecosystem and run only its populated-data browser checks",
    )
    args = parser.parse_args()
    repo = pathlib.Path(__file__).resolve().parents[1]
    backend, frontend = repo / "backend", repo / "frontend"
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required to start Vite and Playwright.")
    vite = frontend / "node_modules" / "vite" / "bin" / "vite.js"
    playwright = frontend / "node_modules" / "@playwright" / "test" / "cli.js"
    if not vite.is_file() or not playwright.is_file():
        raise RuntimeError("Install the frontend dependencies before running this E2E harness.")

    try:
        import pgserver
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Install the backend dev dependencies, including pgserver.") from exc

    sys.path.insert(0, str(backend))
    api_port, web_port = free_port(), free_port()
    run_dir = pathlib.Path(tempfile.mkdtemp(prefix="dh05-isolated-e2e-"))
    captures = run_dir / "captures"
    captures.mkdir()
    api_log = (run_dir / "api.log").open("w", encoding="utf-8")
    web_log = (run_dir / "vite.log").open("w", encoding="utf-8")
    database = api = web = None
    result = 1
    populated_test_env: dict[str, str] = {}
    try:
        database = pgserver.get_server(str(run_dir / "postgres"))
        database_url = database.get_uri()
        os.environ.update({
            "DATABASE_URL": database_url,
            "JWT_SECRET": "isolated-e2e-only-secret-2026-not-for-deployment",
            "APP_ENV": "development",
            "APP_ALLOWED_ORIGINS": f"http://localhost:{web_port},http://127.0.0.1:{web_port}",
            "PASSWORD_RESET_DELIVERY": "disabled",
            "DEMO_PASSWORD": os.environ.get("E2E_DEMO_PASSWORD", "Demo-Only-2026!"),
            # Explicit test-only institutional configuration for OPEN-05.
            "OPPORTUNITY_REVIEWER_ROLES": "EXPERIENTIAL_COORDINATOR",
            "OPPORTUNITY_PUBLISHER_ROLES": "EXPERIENTIAL_COORDINATOR",
            "PLACEMENT_FACULTY_ASSIGNER_ROLES": "PROGRAM_COORDINATOR",
        })

        from migrations.schema_sql import CURRENT_SCHEMA
        from app.seed import seed

        with psycopg.connect(database_url, autocommit=True) as conn:
            conn.execute(CURRENT_SCHEMA)
        with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
            seed(conn.cursor())
            if args.populated:
                from app.synthetic_dataset import populate_synthetic_dataset

                generated = populate_synthetic_dataset(
                    conn.cursor(), include_test_policy=True, allow_test_password=True,
                )
                summary = {key: value for key, value in generated.items() if key != "placement_scenarios"}
                summary.pop("scenario_students", None)
                print(f"POPULATED_SYNTHETIC_FIXTURE={summary}", flush=True)
                scenario_ids = generated["placement_scenarios"]
                scenario_students = generated["scenario_students"]
                populated_test_env = {
                    "E2E_SCENARIO_CLOSED_ID": str(scenario_ids["cierre-completo"]),
                    "E2E_SCENARIO_CLOSED_USER": scenario_students["cierre-completo"],
                    "E2E_SCENARIO_ACTIVE_ID": str(scenario_ids["activa-con-avance"]),
                    "E2E_SCENARIO_ACTIVE_USER": scenario_students["activa-con-avance"],
                    "E2E_SCENARIO_INCIDENT_ID": str(scenario_ids["activa-con-incidente-y-cambio"]),
                    "E2E_SCENARIO_INCIDENT_USER": scenario_students["activa-con-incidente-y-cambio"],
                    "E2E_SCENARIO_MISSING_ID": str(scenario_ids["documentacion-pendiente"]),
                    "E2E_SCENARIO_MISSING_USER": scenario_students["documentacion-pendiente"],
                    "E2E_SCENARIO_REVIEW_ID": str(scenario_ids["documento-en-revision"]),
                    "E2E_SCENARIO_REVIEW_USER": scenario_students["documento-en-revision"],
                    "E2E_SCENARIO_CORRECTION_ID": str(scenario_ids["documento-devuelto"]),
                    "E2E_SCENARIO_CORRECTION_USER": scenario_students["documento-devuelto"],
                    "E2E_SCENARIO_PENDING_ID": str(scenario_ids["aprobacion-academica-pendiente-1"]),
                    "E2E_SCENARIO_PENDING_USER": scenario_students["aprobacion-academica-pendiente-1"],
                }
            else:
                seed_assigned_faculty_practice(conn.cursor())

        api_env = os.environ.copy()
        python_path = [str(backend)]
        if api_env.get("PYTHONPATH"):
            python_path.append(api_env["PYTHONPATH"])
        api_env["PYTHONPATH"] = os.pathsep.join(python_path)
        api = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
            cwd=backend, env=api_env, stdout=api_log, stderr=subprocess.STDOUT,
        )
        web_env = api_env.copy()
        web_env["VITE_API_PROXY_TARGET"] = f"http://127.0.0.1:{api_port}"
        web = subprocess.Popen(
            [node, str(vite), "--host", "127.0.0.1", "--port", str(web_port)],
            cwd=frontend, env=web_env, stdout=web_log, stderr=subprocess.STDOUT,
        )
        if not wait_for(f"http://127.0.0.1:{api_port}/health", (api, web)):
            raise RuntimeError("The isolated API did not become healthy; inspect api.log in the run directory.")
        if not wait_for(f"http://127.0.0.1:{web_port}/", (api, web)):
            raise RuntimeError("Vite did not become healthy; inspect vite.log in the run directory.")

        test_env = web_env.copy()
        test_env.update({
            "E2E_BASE_URL": f"http://localhost:{web_port}",
            "VISUAL_CAPTURE_DIR": str(captures),
            "E2E_DOSSIER_DESKTOP_SCREENSHOT": str(captures / "dossier-desktop.png"),
            "E2E_DOSSIER_MOBILE_SCREENSHOT": str(captures / "dossier-mobile.png"),
            "E2E_STUDENT_DASHBOARD_DESKTOP_SCREENSHOT": str(captures / "student-dashboard-desktop.png"),
            "E2E_STUDENT_DASHBOARD_MOBILE_SCREENSHOT": str(captures / "student-dashboard-mobile.png"),
            "E2E_SUPERVISOR_DASHBOARD_DESKTOP_SCREENSHOT": str(captures / "supervisor-dashboard-desktop.png"),
            "E2E_SUPERVISOR_DASHBOARD_MOBILE_SCREENSHOT": str(captures / "supervisor-dashboard-mobile.png"),
            "E2E_REPORTS_DESKTOP_SCREENSHOT": str(captures / "reports-desktop.png"),
            "E2E_REPORTS_MOBILE_SCREENSHOT": str(captures / "reports-mobile.png"),
            "E2E_POPULATED_SCREENSHOT": str(captures / "populated-student-dossier.png"),
            "E2E_POPULATED_DESKTOP_SCREENSHOT": str(captures / "populated-dossier-desktop.png"),
            "E2E_POPULATED_MOBILE_SCREENSHOT": str(captures / "populated-dossier-mobile.png"),
            "E2E_POPULATED_DARK_DESKTOP_SCREENSHOT": str(captures / "populated-dossier-dark-desktop.png"),
            "E2E_POPULATED_DARK_MOBILE_SCREENSHOT": str(captures / "populated-dossier-dark-mobile.png"),
        })
        test_env.update(populated_test_env)
        playwright_args = [node, str(playwright), "test"]
        if args.populated:
            playwright_args.extend(["--grep", "@populated"])
        completed = subprocess.run(
            playwright_args, cwd=frontend, env=test_env, check=False,
        )
        result = completed.returncode
    finally:
        stop(web)
        stop(api)
        api_log.close()
        web_log.close()
        if database is not None:
            database.cleanup()
        print(f"E2E_RUN_DIR={run_dir}", flush=True)
        print(f"SCREENSHOTS={captures}", flush=True)
        print("TEMPORARY_POSTGRES_CLEANED=true", flush=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
