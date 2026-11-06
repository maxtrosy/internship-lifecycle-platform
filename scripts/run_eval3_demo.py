"""Start a fully isolated, interactive Evaluation 3 demo.

The command creates a throwaway pgserver cluster under the OS temp directory,
migrates it to Alembic head, seeds only synthetic fixture records, and runs the
API and Vite locally. It never reads an inherited DATABASE_URL and never touches
Docker, Neon, the persistent development database, or demo data.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import pathlib
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser


DEMO_PASSWORD = "Demo-Only-2026!"


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


def stop(child: subprocess.Popen | None) -> None:
    if child is None or child.poll() is not None:
        return
    child.terminate()
    try:
        child.wait(timeout=8)
    except subprocess.TimeoutExpired:
        child.kill()
        child.wait(timeout=5)


def assert_login(api_base: str) -> None:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    request = urllib.request.Request(
        f"{api_base}/auth/login",
        data=json.dumps({"username": "s1", "password": DEMO_PASSWORD}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with opener.open(request, timeout=5) as response:
        if response.status not in (200, 204):
            raise RuntimeError("Synthetic student login did not succeed.")
    with opener.open(f"{api_base}/auth/me", timeout=5) as response:
        user = json.load(response)
    if user.get("username") != "s1":
        raise RuntimeError("Authenticated identity did not match the synthetic student.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--smoke", action="store_true",
        help="start the isolated stack, verify migrations/readiness/login, then clean it up",
    )
    parser.add_argument(
        "--open-browser", action="store_true",
        help="open the temporary local demo in the default browser",
    )
    args = parser.parse_args()
    if args.smoke and args.open_browser:
        parser.error("--open-browser cannot be combined with --smoke")

    repo = pathlib.Path(__file__).resolve().parents[1]
    backend, frontend = repo / "backend", repo / "frontend"
    node = shutil.which("node")
    vite = frontend / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite.is_file():
        raise RuntimeError("Install Node.js and frontend dependencies before starting the demo.")
    try:
        import pgserver
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Install backend dev dependencies, including pgserver.") from exc

    api_port, web_port = free_port(), free_port()
    while web_port == api_port:
        web_port = free_port()
    api_base = f"http://127.0.0.1:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    demo_root = pathlib.Path(tempfile.gettempdir()).resolve()
    with tempfile.TemporaryDirectory(prefix="dh05-eval3-demo-", dir=demo_root) as temp_dir:
        run_dir = pathlib.Path(temp_dir).resolve()
        if run_dir.parent != demo_root:
            raise RuntimeError("Refusing to create the temporary database outside the OS temp directory.")
        api_log_path, vite_log_path, migration_log_path = (
            run_dir / "api.log", run_dir / "vite.log", run_dir / "migrations.log"
        )
        database = api = web = None
        api_log = api_log_path.open("w", encoding="utf-8")
        vite_log = vite_log_path.open("w", encoding="utf-8")
        migration_log = migration_log_path.open("w", encoding="utf-8")
        try:
            database = pgserver.get_server(str(run_dir / "postgres"))
            database_url = database.get_uri()
            child_env = os.environ.copy()
            # A developer's local/remote DATABASE_URL must never be inherited.
            child_env.pop("DATABASE_URL", None)
            child_env.update({
                "DATABASE_URL": database_url,
                "JWT_SECRET": secrets.token_urlsafe(48),
                "JWT_TTL_MINUTES": "15",
                "APP_ENV": "development",
                "APP_ALLOWED_ORIGINS": web_url,
                "APP_DB_ROLE": "app_user",
                "PASSWORD_RESET_DELIVERY": "disabled",
                "DEMO_PASSWORD": DEMO_PASSWORD,
                "VITE_DEMO_LOGIN_PASSWORD": DEMO_PASSWORD,
                "VITE_DEMO_LOGIN_ENABLED": "true",
                # These authorities are configured for this disposable demo only.
                "OPPORTUNITY_REVIEWER_ROLES": "EXPERIENTIAL_COORDINATOR",
                "OPPORTUNITY_PUBLISHER_ROLES": "EXPERIENTIAL_COORDINATOR",
                "PLACEMENT_FACULTY_ASSIGNER_ROLES": "PROGRAM_COORDINATOR",
                "VITE_API_PROXY_TARGET": api_base,
            })
            # Domain services invoked by the fixture read Settings in this
            # process, so align it with the same isolated environment passed to
            # Alembic, Uvicorn, and Vite before importing any app modules.
            os.environ.update(child_env)
            migration_env = child_env.copy()
            if database_url.startswith("postgresql://"):
                migration_env["DATABASE_URL"] = (
                    "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
                )
            migration = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=backend, env=migration_env, stdout=migration_log,
                stderr=subprocess.STDOUT, check=False,
            )
            if migration.returncode:
                raise RuntimeError(
                    f"Alembic upgrade head failed (exit {migration.returncode}); see {migration_log_path}."
                )

            sys.path.insert(0, str(backend))
            from app.seed import seed
            from app.synthetic_dataset import populate_synthetic_dataset

            with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
                seed(conn.cursor())
                fixture = populate_synthetic_dataset(
                    conn.cursor(),
                    include_demo_eligibility_policy=True,
                    demo_eligibility_policy_reason=(
                        "DH-05 synthetic demo only; replace with institutionally approved policy."
                    ),
                    allow_test_password=True,
                    allow_demo_lifecycle_records=True,
                )
                revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()["version_num"]
                counts = {
                    table: conn.execute(f"SELECT count(*) AS n FROM {table}").fetchone()["n"]
                    for table in ("user_account", "host_org", "opportunity", "application", "placement")
                }
            if revision != "0014":
                raise RuntimeError("The temporary database did not reach migration revision 0014.")

            python_path = [str(backend)]
            if child_env.get("PYTHONPATH"):
                python_path.append(child_env["PYTHONPATH"])
            child_env["PYTHONPATH"] = os.pathsep.join(python_path)
            api = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                 "--port", str(api_port)],
                cwd=backend, env=child_env, stdout=api_log, stderr=subprocess.STDOUT,
            )
            web = subprocess.Popen(
                [node, str(vite), "--host", "127.0.0.1", "--port", str(web_port), "--strictPort"],
                cwd=frontend, env=child_env, stdout=vite_log, stderr=subprocess.STDOUT,
            )
            if not wait_for(f"{api_base}/health", (api, web)):
                raise RuntimeError(f"The isolated API did not start; see {api_log_path}.")
            if not wait_for(f"{api_base}/ready", (api, web)):
                raise RuntimeError(f"The isolated API is not ready; see {api_log_path}.")
            if not wait_for(web_url, (api, web)):
                raise RuntimeError(f"Vite did not start; see {vite_log_path}.")
            assert_login(api_base)

            print(f"MIGRATION_HEAD={revision}")
            print("HEALTH=/health PASS; READINESS=/ready PASS; SYNTHETIC_LOGIN PASS")
            print("FIXTURE_COUNTS=" + ", ".join(f"{key}={value}" for key, value in counts.items()))
            print("DEMO_POLICY=replaceable synthetic assumption only; not institutional policy")
            if args.smoke:
                return 0

            print(f"FRONTEND={web_url}")
            print(f"API_HEALTH={api_base}/health")
            print(f"API_READY={api_base}/ready")
            print("TEMPORARY_DATABASE=isolated pgserver; no Docker, local DB, demo DB, or Neon")
            print("DEMO_USERS=s1(student), hm_alfa(host member), pc_sys(program coordinator), ec1(experiential coordinator), ws_alfa(workplace supervisor), f1(faculty supervisor), legal1(legal reviewer)")
            print(f"DEMO_PASSWORD={DEMO_PASSWORD} (temporary synthetic fixture only)")
            print("Press Ctrl+C to stop the app and delete the temporary database.")
            if args.open_browser:
                webbrowser.open(web_url)
            while api.poll() is None and web.poll() is None:
                time.sleep(0.5)
            raise RuntimeError("A demo server process exited unexpectedly; check the temporary logs.")
        except KeyboardInterrupt:
            print("Stopping the isolated Evaluation 3 demo.")
            return 0
        finally:
            stop(web)
            stop(api)
            api_log.close()
            vite_log.close()
            migration_log.close()
            if database is not None:
                database.cleanup()
            print("TEMPORARY_DATABASE_CLEANED=true")


if __name__ == "__main__":
    raise SystemExit(main())
