"""Build the disposable, container-only Evaluation 3 fixture."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from alembic import command
from alembic.config import Config
from psycopg import sql
from psycopg.rows import dict_row


def require_disposable_target(database_url: str) -> None:
    parsed = urlsplit(database_url)
    if (
        parsed.scheme not in {"postgresql", "postgres"}
        or parsed.hostname != "db"
        or parsed.port != 5432
        or parsed.path != "/dh05_eval3"
        or parsed.username != "postgres"
    ):
        raise RuntimeError("Refusing to seed: target is not the isolated Compose demo database.")


def runtime_url(database_url: str, password: str) -> str:
    parsed = urlsplit(database_url)
    netloc = f"app_runtime:{password}@{parsed.hostname}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def main() -> None:
    if os.environ.get("APP_ENV") != "development":
        raise RuntimeError("This fixture can only run with APP_ENV=development.")
    database_url = os.environ.get("DATABASE_URL", "")
    runtime_password = os.environ.get("DEMO_RUNTIME_PASSWORD", "")
    if not runtime_password:
        raise RuntimeError("The disposable runtime role password is missing.")
    require_disposable_target(database_url)

    backend_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(backend_root / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    from app.seed import seed
    from app.synthetic_dataset import populate_synthetic_dataset

    with psycopg.connect(database_url, autocommit=True, row_factory=dict_row) as conn:
        seed(conn.cursor())
        populate_synthetic_dataset(
            conn.cursor(),
            include_demo_eligibility_policy=True,
            demo_eligibility_policy_reason=(
                "Evaluation 3 container fixture only; replace with institutionally approved policy."
            ),
            allow_test_password=True,
            allow_demo_lifecycle_records=True,
        )
        conn.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier("app_runtime"), sql.Literal(runtime_password)
            )
        )
        conn.execute("GRANT app_user TO app_runtime")
        revision = conn.execute("SELECT version_num FROM alembic_version").fetchone()["version_num"]
        counts = {
            table: conn.execute(sql.SQL("SELECT count(*) AS n FROM {}").format(
                sql.Identifier(table)
            )).fetchone()["n"]
            for table in ("user_account", "host_org", "opportunity", "application", "placement")
        }

    app_url = runtime_url(database_url, runtime_password)
    with psycopg.connect(app_url, row_factory=dict_row) as conn:
        with conn.transaction():
            conn.execute("SET ROLE app_user")
            identity = conn.execute(
                "SELECT session_user, current_user"
            ).fetchone()
            if identity != {"session_user": "app_runtime", "current_user": "app_user"}:
                raise RuntimeError("The local runtime role could not assume app_user.")
            conn.execute("SELECT count(*) FROM placement").fetchone()

    if revision != "0014":
        raise RuntimeError("The container fixture did not reach Alembic revision 0014.")
    print(f"MIGRATION_HEAD={revision}")
    print("RUNTIME_ROLE=app_runtime; SET_ROLE=app_user PASS")
    print("FIXTURE_COUNTS=" + ", ".join(f"{table}={count}" for table, count in counts.items()))
    print("DATA=synthetic and disposable; policy assumptions are not institutional rules")


if __name__ == "__main__":
    main()
