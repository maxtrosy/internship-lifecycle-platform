"""Alembic environment. SQLAlchemy is used ONLY as the migration engine (no ORM, ADR-007)."""
from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine

config = context.config

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres@localhost:5432/postgres"
)
# SQLAlchemy's PostgreSQL default is psycopg2, while this project deliberately
# depends on psycopg 3. Accept the same standard PostgreSQL URL as the API and
# select the installed driver explicitly for Alembic.
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = "postgresql+psycopg://" + DATABASE_URL.removeprefix("postgresql://")


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=None,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
