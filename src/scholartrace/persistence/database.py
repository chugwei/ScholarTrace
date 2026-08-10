"""Database engine construction."""

import sqlite3
from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, event


def create_sqlite_engine(database_path: Path) -> Engine:
    """Create a SQLite engine with foreign-key enforcement enabled."""

    resolved_path = database_path.expanduser().resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite+pysqlite", database=str(resolved_path)),
        future=True,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        connection: sqlite3.Connection,
        _connection_record: object,
    ) -> None:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine
