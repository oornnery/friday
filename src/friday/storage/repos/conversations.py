"""Conversation repository."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

MessageRole = Literal["user", "assistant", "tool"]


@dataclass(frozen=True)
class ConversationMessage:
    session_id: str
    message_id: str
    role: MessageRole
    content: str
    ts: int


def add_message(conn: sqlite3.Connection, message: ConversationMessage) -> None:
    conn.execute(
        "INSERT INTO conversations (session_id, message_id, role, content, ts) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            message.session_id,
            message.message_id,
            message.role,
            message.content,
            message.ts,
        ),
    )
    conn.commit()


def list_messages(
    conn: sqlite3.Connection, session_id: str
) -> list[ConversationMessage]:
    rows = conn.execute(
        "SELECT session_id, message_id, role, content, ts "
        "FROM conversations WHERE session_id = ? ORDER BY ts",
        (session_id,),
    ).fetchall()
    return [
        ConversationMessage(
            session_id=row[0],
            message_id=row[1],
            role=row[2],
            content=row[3],
            ts=row[4],
        )
        for row in rows
    ]
