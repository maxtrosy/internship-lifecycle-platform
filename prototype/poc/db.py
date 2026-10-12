import pathlib, tempfile, psycopg, pgserver
from psycopg.rows import dict_row

SCHEMA = pathlib.Path(__file__).with_name("schema.sql")


class Env:
    """Real PostgreSQL instance (pgserver) with the PoC schema loaded."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="dh05_poc_")
        self.srv = pgserver.get_server(self.dir)
        self.uri = self.srv.get_uri()
        with psycopg.connect(self.uri, autocommit=True) as c:
            c.execute(SCHEMA.read_text())
        self.admin = psycopg.connect(self.uri, autocommit=True, row_factory=dict_row)

    def conn(self, app_role=True):
        c = psycopg.connect(self.uri, autocommit=True, row_factory=dict_row)
        if app_role:
            c.execute("SET ROLE app_user")
        return c

    def close(self):
        self.admin.close()
        self.srv.cleanup()
