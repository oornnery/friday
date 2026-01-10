"""Tasks repository."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class TaskRecord:
    id: str
    title: str
    schedule: str
    payload: dict | None
    enabled: bool
    last_run: int | None
    next_run: int | None


def create_task(
    conn: sqlite3.Connection,
    title: str,
    schedule: str,
    payload: dict | None = None,
    next_run: int | None = None,
) -> TaskRecord:
    task_id = f"task_{uuid.uuid4().hex}"
    payload_json = json.dumps(payload) if payload is not None else None
    conn.execute(
        "INSERT INTO tasks (id, title, schedule, payload_json, enabled, last_run, "
        "next_run) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, title, schedule, payload_json, 1, None, next_run),
    )
    conn.commit()
    return TaskRecord(
        id=task_id,
        title=title,
        schedule=schedule,
        payload=payload,
        enabled=True,
        last_run=None,
        next_run=next_run,
    )


def list_tasks(conn: sqlite3.Connection) -> list[TaskRecord]:
    rows = conn.execute(
        "SELECT id, title, schedule, payload_json, enabled, last_run, next_run "
        "FROM tasks"
    ).fetchall()
    return [_row_to_task(row) for row in rows]


def get_task(conn: sqlite3.Connection, task_id: str) -> TaskRecord | None:
    row = conn.execute(
        "SELECT id, title, schedule, payload_json, enabled, last_run, next_run "
        "FROM tasks WHERE id = ?",
        (task_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_task(row)


def due_tasks(conn: sqlite3.Connection, now_ts: int) -> list[TaskRecord]:
    rows = conn.execute(
        "SELECT id, title, schedule, payload_json, enabled, last_run, next_run "
        "FROM tasks WHERE enabled = 1 AND next_run IS NOT NULL AND next_run <= ?",
        (now_ts,),
    ).fetchall()
    return [_row_to_task(row) for row in rows]


def update_task_run(
    conn: sqlite3.Connection, task_id: str, last_run: int, next_run: int | None
) -> None:
    conn.execute(
        "UPDATE tasks SET last_run = ?, next_run = ? WHERE id = ?",
        (last_run, next_run, task_id),
    )
    conn.commit()


def disable_task(conn: sqlite3.Connection, task_id: str) -> None:
    conn.execute("UPDATE tasks SET enabled = 0 WHERE id = ?", (task_id,))
    conn.commit()


def _row_to_task(row: sqlite3.Row) -> TaskRecord:
    payload = json.loads(row[3]) if row[3] else None
    return TaskRecord(
        id=row[0],
        title=row[1],
        schedule=row[2],
        payload=payload,
        enabled=bool(row[4]),
        last_run=row[5],
        next_run=row[6],
    )
