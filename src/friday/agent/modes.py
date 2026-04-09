"""Mode configurations — loaded from prompt .md files with YAML frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from friday.domain.models import AgentMode

_PROMPTS_DIR = Path(__file__).parent / 'prompts'

# Map mode to prompt filename
_PROMPT_FILES: dict[AgentMode, str] = {
    AgentMode.CODE: 'code.md',
    AgentMode.READER: 'reader.md',
    AgentMode.WRITE: 'writer.md',
    AgentMode.DEBUG: 'debug.md',
}

_FRONTMATTER_RE = re.compile(
    r'\A---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)',
    re.DOTALL,
)


def _parse_prompt_file(path: Path) -> tuple[dict[str, Any], str]:
    """Parse a prompt .md file into (frontmatter_dict, body_text)."""
    raw = path.read_text(encoding='utf-8')
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        return {}, raw.strip()
    meta = yaml.safe_load(match.group('meta')) or {}
    body = match.group('body').strip()
    return meta, body


@dataclass(frozen=True, slots=True)
class ModeConfig:
    """Configuration for an agent mode — from frontmatter."""

    system_prompt: str
    tool_names: tuple[str, ...]
    max_steps: int = 25
    model: str | None = None
    provider: str | None = None
    thinking: bool = False


def load_mode(mode: AgentMode) -> ModeConfig:
    """Load a ModeConfig from the corresponding prompt .md file."""
    filename = _PROMPT_FILES[mode]
    meta, body = _parse_prompt_file(_PROMPTS_DIR / filename)
    return ModeConfig(
        system_prompt=body,
        tool_names=tuple(meta.get('tools', [])),
        max_steps=int(meta.get('max_steps', 25)),
        model=meta.get('model') or None,
        provider=meta.get('provider') or None,
        thinking=bool(meta.get('thinking', False)),
    )


def load_prompt(mode: AgentMode) -> str:
    """Load just the system prompt body from a prompt .md file."""
    return load_mode(mode).system_prompt


# Eagerly load all modes at import time for quick access
MODE_CONFIGS: dict[AgentMode, ModeConfig] = {mode: load_mode(mode) for mode in AgentMode}
