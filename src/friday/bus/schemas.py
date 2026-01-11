"""Event message schemas."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from friday.utils.time import now_ts

Source = Literal["tui", "cli", "voice"]


@dataclass(frozen=True)
class InputText:
    session_id: str
    message_id: str
    ts: int
    text: str
    source: Source


@dataclass(frozen=True)
class InputTextPartial:
    session_id: str
    message_id: str
    ts: int
    text: str
    source: Source


@dataclass(frozen=True)
class InputAudioFrames:
    session_id: str
    ts: int
    audio: bytes
    sample_rate: int


@dataclass(frozen=True)
class ToolCall:
    session_id: str
    call_id: str
    tool: str
    args: dict[str, Any]
    requires_confirm: bool


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    ok: bool
    result: dict[str, Any] | None
    error: str | None
    elapsed_ms: int


@dataclass(frozen=True)
class OutputText:
    session_id: str
    message_id: str
    ts: int
    text: str
    thinking: str | None = None


def new_message_id() -> str:
    return f"msg_{uuid.uuid4().hex}"


def new_call_id() -> str:
    return f"call_{uuid.uuid4().hex}"


def build_input_text(session_id: str, text: str, source: Source) -> InputText:
    return InputText(
        session_id=session_id,
        message_id=new_message_id(),
        ts=now_ts(),
        text=text,
        source=source,
    )
