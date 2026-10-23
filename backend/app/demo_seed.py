"""Seed synthetic users for the isolated Compose demo database only."""
from __future__ import annotations

from psycopg.conninfo import conninfo_to_dict

from app import db
from app.config import get_settings
from app.seed import seed


def main() -> None:
    settings = get_settings()
    target = conninfo_to_dict(settings.database_url)
    if settings.app_env != "demo":
        raise RuntimeError("Demo seed refused: APP_ENV must be exactly 'demo'.")
    if target.get("dbname") != "dh05_demo" or target.get("host") != "db":
        raise RuntimeError("Demo seed refused: expected the isolated db service and dh05_demo database.")

    with db.admin() as cur:
        existing = cur.execute("SELECT count(*) AS n FROM user_account").fetchone()["n"]
        if existing:
            raise RuntimeError(
                f"Demo seed refused: dh05_demo already contains {existing} accounts; "
                "use the demo runbook's explicit reset procedure for a clean dataset."
            )
        users = seed(cur)
    print(
        "Demo target verified: host=db database=dh05_demo; "
        f"created {len(users) - 1} synthetic accounts and program policies."
    )


if __name__ == "__main__":
    main()
