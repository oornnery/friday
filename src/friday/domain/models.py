"""Domain models — enums, value objects, and data structures."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AgentMode(StrEnum):
    CODE = 'code'
    READER = 'reader'
    WRITE = 'write'
    DEBUG = 'debug'


class ApprovalPolicy(StrEnum):
    ASK = 'ask'
    AUTO = 'auto'
    NEVER = 'never'


class Role(StrEnum):
    USER = 'user'
    ASSISTANT = 'assistant'
    TOOL = 'tool'
    SYSTEM = 'system'


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


def _session_id() -> str:
    return f'{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}'


@dataclass(slots=True)
class WorkingMemory:
    """Small, mutable, prompt-resident state — the agent's RAM."""

    task: str = ''
    files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    mode: AgentMode = AgentMode.CODE

    def remember(self, bucket: list[str], item: str, limit: int) -> None:
        if not item:
            return
        if item in bucket:
            bucket.remove(item)
        bucket.append(item)
        del bucket[:-limit]

    def render(self) -> str:
        files = ', '.join(self.files) or '-'
        notes_text = '\n'.join(f'  - {n}' for n in self.notes) or '  - none'
        return f'task: {self.task or "-"}\nmode: {self.mode}\nfiles: {files}\nnotes:\n{notes_text}'


@dataclass(slots=True)
class Message:
    role: Role
    content: str
    at: str = field(default_factory=_utcnow)
    tool: str = ''
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Session:
    """Full conversation transcript — the agent's hard drive."""

    id: str = field(default_factory=_session_id)
    created_at: str = field(default_factory=_utcnow)
    history: list[Message] = field(default_factory=list)
    memory: WorkingMemory = field(default_factory=WorkingMemory)
