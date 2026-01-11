"""SQLite-backed state store."""

from __future__ import annotations

import uuid
from pathlib import Path

from friday.core.state import Message, MessageRole, StateStore
from friday.storage.db import connect
from friday.storage.repos import conversations
from friday.utils.time import now_ts


class SQLiteStateStore(StateStore):
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path

    def add_message(
        self, session_id: str, role: MessageRole, content: str, ts: int | None = None
    ) -> Message:
        message = Message(
            message_id=_message_id(),
            role=role,
            content=content,
            ts=ts or now_ts(),
        )
        with connect(self._db_path) as conn:
            conversations.add_message(
                conn,
                conversations.ConversationMessage(
                    session_id=session_id,
                    message_id=message.message_id,
                    role=message.role,
                    content=message.content,
                    ts=message.ts,
                ),
            )
        return message

    def list_messages(self, session_id: str) -> list[Message]:
        with connect(self._db_path) as conn:
            rows = conversations.list_messages(conn, session_id)
        return [
            Message(
                message_id=row.message_id,
                role=row.role,
                content=row.content,
                ts=row.ts,
            )
            for row in rows
        ]


def _message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"
