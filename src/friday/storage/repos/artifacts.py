"""Artifacts repository."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class Artifact:
    id: str
    type: str
    path: str
    meta: dict | None
    ts: int


def add_artifact(conn: sqlite3.Connection, artifact: Artifact) -> None:
    conn.execute(
        "INSERT INTO artifacts (id, type, path, meta_json, ts) VALUES (?, ?, ?, ?, ?)",
        (
            artifact.id,
            artifact.type,
            artifact.path,
            json.dumps(artifact.meta) if artifact.meta is not None else None,
            artifact.ts,
        ),
    )
    conn.commit()
