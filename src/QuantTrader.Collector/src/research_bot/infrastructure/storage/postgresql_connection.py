from __future__ import annotations

import psycopg


class PostgreSqlConnectionFactory:
    def __init__(self, conninfo: str) -> None:
        self.conninfo = conninfo

    def connect(self):
        return psycopg.connect(self.conninfo)
