"""Tool call logs repository."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolCallLog:
    call_id: str
    session_id: str
    tool: str
    args: dict
    result: dict | None
    ok: bool
    elapsed_ms: int
    ts: int


def log_tool_call(conn: sqlite3.Connection, log: ToolCallLog) -> None:
    conn.execute(
        "INSERT INTO tool_calls (call_id, session_id, tool, args_json, result_json, "
        "ok, elapsed_ms, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            log.call_id,
            log.session_id,
            log.tool,
            json.dumps(log.args),
            json.dumps(log.result) if log.result is not None else None,
            1 if log.ok else 0,
            log.elapsed_ms,
            log.ts,
        ),
    )
    conn.commit()
