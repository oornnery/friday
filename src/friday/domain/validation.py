"""Input validation for tool arguments — enforce sane limits."""

from __future__ import annotations

MAX_PATH_LENGTH = 500
MAX_PATTERN_LENGTH = 200
MAX_COMMAND_LENGTH = 2000
MAX_CONTENT_LENGTH = 100_000
MAX_LINE_RANGE = 10_000


def validate_path(path: str) -> str:
    """Reject paths that are too long."""
    if len(path) > MAX_PATH_LENGTH:
        msg = f'path too long ({len(path)} chars, max {MAX_PATH_LENGTH})'
        raise ValueError(msg)
    return path


def validate_pattern(pattern: str) -> str:
    """Reject search/glob patterns that are too long or contain traversal."""
    if len(pattern) > MAX_PATTERN_LENGTH:
        msg = f'pattern too long ({len(pattern)} chars, max {MAX_PATTERN_LENGTH})'
        raise ValueError(msg)
    if '..' in pattern:
        msg = 'pattern must not contain ..'
        raise ValueError(msg)
    return pattern


def validate_command(command: str) -> str:
    """Reject shell commands that are too long."""
    if len(command) > MAX_COMMAND_LENGTH:
        msg = f'command too long ({len(command)} chars, max {MAX_COMMAND_LENGTH})'
        raise ValueError(msg)
    return command


def validate_content(content: str) -> str:
    """Reject file content that is too large."""
    if len(content) > MAX_CONTENT_LENGTH:
        msg = f'content too large ({len(content)} chars, max {MAX_CONTENT_LENGTH})'
        raise ValueError(msg)
    return content


def validate_line_range(start: int, end: int) -> tuple[int, int]:
    """Clamp line range to safe bounds."""
    start = max(1, min(start, MAX_LINE_RANGE))
    end = max(start, min(end, MAX_LINE_RANGE))
    return start, end
