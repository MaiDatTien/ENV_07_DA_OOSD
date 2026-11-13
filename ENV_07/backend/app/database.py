from contextlib import contextmanager
from decimal import Decimal

import pyodbc

from .config import settings


def _clean(v):
    return float(v) if isinstance(v, Decimal) else v


class Database:
    def __init__(self, conn_str: str):
        self.conn_str = conn_str

    @contextmanager
    def transaction(self):
        conn = pyodbc.connect(self.conn_str, autocommit=False)
        try:
            yield conn.cursor()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def rows(cur) -> list[dict]:
        if cur.description is None:
            return []
        cols = [c[0] for c in cur.description]
        return [{k: _clean(v) for k, v in zip(cols, r)} for r in cur.fetchall()]

    def query(self, sql: str, *params) -> list[dict]:
        with self.transaction() as cur:
            cur.execute(sql, *params)
            return self.rows(cur)

    def query_one(self, sql: str, *params):
        r = self.query(sql, *params)
        return r[0] if r else None

    def execute(self, sql: str, *params) -> int:
        with self.transaction() as cur:
            cur.execute(sql, *params)
            return cur.rowcount

    def ping(self) -> bool:
        try:
            self.query("SELECT 1 AS ok")
            return True
        except Exception:
            return False


db = Database(settings.connection_string)
