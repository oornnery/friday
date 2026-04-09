"""Session persistence — JSON file store."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from friday.domain.permissions import clip


def _utcnow() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class SessionMeta:
    """Lightweight session metadata for listing and resuming."""

    id: str
    created_at: str
    model: str = ''
    mode: str = 'auto'
    turn_count: int = 0
    last_user_message: str = ''


@dataclass(slots=True)
class SessionData:
    """Full session data — metadata + pydantic-ai message history."""

    meta: SessionMeta
    messages: list[dict[str, Any]] = field(default_factory=list)


class JsonSessionStore:
    """Stores sessions as JSON files in a directory."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, session_id: str) -> Path:
        return self.root / f'{session_id}.json'

    def save(self, data: SessionData) -> None:
        payload = {
            'meta': asdict(data.meta),
            'messages': data.messages,
        }
        self._path(data.meta.id).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding='utf-8',
        )

    def load(self, session_id: str) -> SessionData:
        path = self._path(session_id)
        if not path.exists():
            msg = f'Session not found: {session_id}'
            raise FileNotFoundError(msg)
        raw = json.loads(path.read_text(encoding='utf-8'))
        meta = SessionMeta(**raw['meta'])
        return SessionData(meta=meta, messages=raw.get('messages', []))

    def latest_id(self) -> str | None:
        files = sorted(self.root.glob('*.json'), key=lambda p: p.stat().st_mtime)
        return files[-1].stem if files else None

    def list_sessions(self, limit: int = 20) -> list[SessionMeta]:
        """List recent sessions, newest first."""
        files = sorted(
            self.root.glob('*.json'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        sessions: list[SessionMeta] = []
        for f in files[:limit]:
            try:
                raw = json.loads(f.read_text(encoding='utf-8'))
                sessions.append(SessionMeta(**raw['meta']))
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions

    def delete(self, session_id: str) -> bool:
        path = self._path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False


def extract_last_user_message(messages: list[dict[str, Any]]) -> str:
    """Extract the last user message text from pydantic-ai message history."""
    for msg in reversed(messages):
        if msg.get('kind') == 'request':
            for part in reversed(msg.get('parts', [])):
                if part.get('part_kind') == 'user-prompt':
                    return clip(part.get('content', ''), 80)
    return ''
