"""Database plumbing.

Three helpers:
- ``command(actor_id)``: ONE transaction running as ``app_user``; enforces that an
  accepted mutation writes its audit event (BR-07). Denied commands raise before mutating
  and therefore roll back with no audit row.
- ``read()``: read-only transaction running as ``app_user`` (no audit enforcement).
- ``admin()``: superuser connection for seeding/migrations (no role switch).
"""
from __future__ import annotations

import contextvars
import uuid
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from .config import get_settings
from .errors import BusinessError

_current_command: contextvars.ContextVar["CommandContext | None"] = contextvars.ContextVar(
    "current_command", default=None
)
_shared_command_connection: contextvars.ContextVar[tuple[psycopg.Connection, str | None] | None] = contextvars.ContextVar(
    "shared_command_connection", default=None
)

_DML_KEYWORDS = {"insert", "update", "delete"}
_CONFIGURED_ROLE = object()


def _is_dml(sql: str) -> bool:
    first = sql.lstrip().split(None, 1)[0].lower() if sql.strip() else ""
    return first in _DML_KEYWORDS


class CommandContext:
    """Cursor facade that tracks DML and audit so BR-07 can be enforced on commit."""

    def __init__(self, conn: psycopg.Connection, cur: psycopg.Cursor, actor_id: int | None,
                 correlation_id: str):
        self.conn = conn
        self.cur = cur
        self.actor_id = actor_id
        self.correlation_id = correlation_id
        self.dirty = False
        self.audited = False

    def execute(self, sql: str, params: Any = None) -> psycopg.Cursor:
        if _is_dml(sql):
            self.dirty = True
        return self.cur.execute(sql, params) if params is not None else self.cur.execute(sql)

    def fetchone(self):
        return self.cur.fetchone()

    def fetchall(self):
        return self.cur.fetchall()

    @property
    def rowcount(self) -> int:
        return self.cur.rowcount


def current_command() -> "CommandContext | None":
    return _current_command.get()


def _connect() -> psycopg.Connection:
    return psycopg.connect(get_settings().database_url, row_factory=dict_row)


@contextmanager
def command(actor_id: int | None) -> Iterator[CommandContext]:
    """One mutation transaction under the application DB role.

    ``actor_id`` is None only for system-internal commands; business commands pass a real id.
    """
    shared = _shared_command_connection.get()
    if shared is not None:
        shared_conn, required_role = shared
        # Used by explicitly scoped batch operations that must remain atomic. The
        # caller opens the outer transaction and has already selected app_role.
        # Each command gets a savepoint so a failed domain operation cannot leave
        # partial work in the enclosing batch.
        with shared_conn.transaction():
            cur = shared_conn.cursor()
            active_role = cur.execute("SELECT current_user AS role").fetchone()["role"]
            if required_role is not None and active_role != required_role:
                raise RuntimeError("Shared command connection must already run as the application role.")
            cur.execute("SELECT set_config('dh05.actor_id', %s, true)",
                        (str(actor_id) if actor_id is not None else "",))
            ctx = CommandContext(shared_conn, cur, actor_id, str(uuid.uuid4()))
            token = _current_command.set(ctx)
            try:
                yield ctx
            except BaseException:
                raise
            else:
                if ctx.dirty and not ctx.audited:
                    raise BusinessError("AUDIT_MISSING", "accepted mutation without audit event")
            finally:
                _current_command.reset(token)
        return

    with _connect() as conn:
        with conn.transaction():
            cur = conn.cursor()
            cur.execute(f"SET ROLE {get_settings().app_role}")
            cur.execute("SELECT set_config('dh05.actor_id', %s, true)", (str(actor_id) if actor_id is not None else "",))
            ctx = CommandContext(conn, cur, actor_id, str(uuid.uuid4()))
            token = _current_command.set(ctx)
            try:
                yield ctx
            except BaseException:
                raise
            else:
                if ctx.dirty and not ctx.audited:
                    raise BusinessError("AUDIT_MISSING", "accepted mutation without audit event")
            finally:
                _current_command.reset(token)


@contextmanager
def shared_command_connection(conn: psycopg.Connection, *,
                              required_role: str | None | object = _CONFIGURED_ROLE) -> Iterator[None]:
    """Route nested ``command()`` calls through an existing atomic batch transaction.

    The owner must open the outer transaction before entering this scope. When
    ``required_role`` is set, the connection must already be running as that role.
    ``None`` is reserved for trusted one-off loaders using a separately verified
    writer connection; HTTP requests continue using independent command transactions.
    """
    if _shared_command_connection.get() is not None:
        raise RuntimeError("A shared command connection is already active in this context.")
    if not conn.info.transaction_status:
        raise RuntimeError("Shared command connection requires an open outer transaction.")
    active_role = get_settings().app_role if required_role is _CONFIGURED_ROLE else required_role
    token = _shared_command_connection.set((conn, active_role))
    try:
        yield
    finally:
        _shared_command_connection.reset(token)


@contextmanager
def read() -> Iterator[psycopg.Cursor]:
    """One read-only transaction under the application DB role."""
    with _connect() as conn:
        with conn.transaction():
            cur = conn.cursor()
            cur.execute(f"SET ROLE {get_settings().app_role}")
            yield cur


@contextmanager
def admin() -> Iterator[psycopg.Cursor]:
    """Superuser connection for seeding and migrations."""
    with _connect() as conn:
        with conn.transaction():
            yield conn.cursor()
