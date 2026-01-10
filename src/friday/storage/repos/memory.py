"""Memory facts repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryFact:
    id: str
    key: str
    value: str
    confidence: float
    updated_at: int


def upsert_fact(conn: sqlite3.Connection, fact: MemoryFact) -> None:
    conn.execute(
        "INSERT INTO memory_facts (id, key, value, confidence, updated_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET key=excluded.key, value=excluded.value, "
        "confidence=excluded.confidence, updated_at=excluded.updated_at",
        (fact.id, fact.key, fact.value, fact.confidence, fact.updated_at),
    )
    conn.commit()


def list_facts(conn: sqlite3.Connection) -> list[MemoryFact]:
    rows = conn.execute(
        "SELECT id, key, value, confidence, updated_at FROM memory_facts"
    ).fetchall()
    return [
        MemoryFact(
            id=row[0],
            key=row[1],
            value=row[2],
            confidence=row[3],
            updated_at=row[4],
        )
        for row in rows
    ]
