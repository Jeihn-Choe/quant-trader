from __future__ import annotations

from pathlib import Path

import duckdb


class DuckDbConnectionFactory:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return duckdb.connect(str(self.database_path))
