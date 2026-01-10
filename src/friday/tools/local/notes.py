"""Notes tool backed by SQLite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from friday.storage.db import connect
from friday.storage.repos import notes as notes_repo
from friday.utils.time import now_ts


@dataclass(frozen=True)
class NotesService:
    db_path: Path

    def append(self, title: str, content: str) -> str:
        with connect(self.db_path) as conn:
            note = notes_repo.add_note(conn, title, content, now_ts())
        return note.id

    def search(self, query: str) -> list[dict[str, str]]:
        with connect(self.db_path) as conn:
            notes = notes_repo.search_notes(conn, query)
        return [
            {"id": note.id, "title": note.title, "content": note.content}
            for note in notes
        ]
