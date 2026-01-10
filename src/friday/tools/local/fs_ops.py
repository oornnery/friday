"""Filesystem operations with workspace sandbox."""

from __future__ import annotations

from pathlib import Path


def resolve_path(workspace_path: Path, user_path: str) -> Path:
    workspace_root = workspace_path.expanduser().resolve()
    candidate = (workspace_root / user_path).expanduser().resolve()
    if candidate == workspace_root:
        return candidate
    if workspace_root not in candidate.parents:
        raise ValueError("Path escapes workspace")
    return candidate


def read_text(workspace_path: Path, user_path: str) -> str:
    path = resolve_path(workspace_path, user_path)
    return path.read_text(encoding="utf-8")


def write_text(workspace_path: Path, user_path: str, content: str) -> None:
    path = resolve_path(workspace_path, user_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
