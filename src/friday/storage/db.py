"""SQLite database helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from friday.core.settings import Settings


def db_path(settings: Settings) -> Path:
    return settings.data_dir / "friday.db"


def connect(db_path_value: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path_value)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db(settings: Settings) -> None:
    db_path_value = db_path(settings)
    db_path_value.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path_value)
    try:
        migrations_dir = Path(__file__).resolve().parent / "migrations"
        _apply_migrations(conn, migrations_dir)
    finally:
        conn.close()


def _apply_migrations(conn: sqlite3.Connection, migrations_dir: Path) -> None:
    if not migrations_dir.exists():
        return
    for migration in sorted(migrations_dir.glob("*.sql")):
        conn.executescript(migration.read_text(encoding="utf-8"))
    conn.commit()
