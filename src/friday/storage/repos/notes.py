"""Notes repository."""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    content: str
    ts: int


def add_note(conn: sqlite3.Connection, title: str, content: str, ts: int) -> Note:
    note_id = f"note_{uuid.uuid4().hex}"
    conn.execute(
        "INSERT INTO notes (id, title, content, ts) VALUES (?, ?, ?, ?)",
        (note_id, title, content, ts),
    )
    conn.commit()
    return Note(id=note_id, title=title, content=content, ts=ts)


def search_notes(conn: sqlite3.Connection, query: str) -> list[Note]:
    like_query = f"%{query}%"
    rows = conn.execute(
        "SELECT id, title, content, ts FROM notes WHERE title LIKE ? OR content LIKE ?",
        (like_query, like_query),
    ).fetchall()
    return [Note(id=row[0], title=row[1], content=row[2], ts=row[3]) for row in rows]
