"""Path containment and context reduction utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

MAX_TOOL_OUTPUT = 4000
RECENT_WINDOW = 6
RECENT_LIMIT = 900
OLD_LIMIT = 180
MAX_HISTORY = 12_000


def safe_path(root: Path, raw: str) -> Path:
    """Resolve *raw* against *root*. Raise if it escapes."""
    raw_path = Path(raw)
    candidate = raw_path.resolve() if raw_path.is_absolute() else (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        msg = f'path escapes workspace: {raw}'
        raise PermissionError(msg) from exc
    return candidate


def clip(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    """Cap text length, marking truncation."""
    if len(text) <= limit:
        return text
    return f'{text[:limit]}\n...[truncated {len(text) - limit} chars]'


def render_history(history: list[dict[str, Any]]) -> str:
    """Recency-weighted, deduplicated transcript compaction."""
    if not history:
        return '- empty'

    seen_reads: set[str] = set()
    recent_start = max(0, len(history) - RECENT_WINDOW)
    lines: list[str] = []

    for i, item in enumerate(history):
        is_recent = i >= recent_start

        if not is_recent and item.get('tool') == 'read_file':
            path = str(item.get('args', {}).get('path', ''))
            if path in seen_reads:
                continue
            seen_reads.add(path)

        limit = RECENT_LIMIT if is_recent else OLD_LIMIT
        lines.append(f'[{item["role"]}] {clip(item["content"], limit)}')

    return clip('\n'.join(lines), MAX_HISTORY)
