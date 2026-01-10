"""Session state and memory interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from friday.utils.time import now_ts

MessageRole = Literal["user", "assistant", "tool"]


@dataclass(frozen=True)
class Message:
    message_id: str
    role: MessageRole
    content: str
    ts: int


@dataclass
class SessionState:
    session_id: str
    messages: list[Message] = field(default_factory=list)


class StateStore(Protocol):
    def add_message(
        self, session_id: str, role: MessageRole, content: str, ts: int | None = None
    ) -> Message: ...

    def list_messages(self, session_id: str) -> list[Message]: ...


class InMemoryStateStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def add_message(
        self, session_id: str, role: MessageRole, content: str, ts: int | None = None
    ) -> Message:
        message = Message(
            message_id=self._new_message_id(),
            role=role,
            content=content,
            ts=ts or now_ts(),
        )
        session = self._sessions.setdefault(session_id, SessionState(session_id))
        session.messages.append(message)
        return message

    def list_messages(self, session_id: str) -> list[Message]:
        session = self._sessions.get(session_id)
        if session is None:
            return []
        return list(session.messages)

    def _new_message_id(self) -> str:
        return f"msg_{now_ts()}_{len(self._sessions)}"
