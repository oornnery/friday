"""Tests for domain permissions — safe_path and clip."""

from __future__ import annotations

from pathlib import Path

import pytest

from friday.domain.permissions import clip, safe_path


class TestSafePath:
    def test_relative_inside(self, tmp_workspace: Path) -> None:
        result = safe_path(tmp_workspace, 'hello.py')
        assert result == tmp_workspace / 'hello.py'

    def test_subdirectory(self, tmp_workspace: Path) -> None:
        sub = tmp_workspace / 'sub'
        sub.mkdir()
        (sub / 'file.txt').write_text('x')
        result = safe_path(tmp_workspace, 'sub/file.txt')
        assert result == sub / 'file.txt'

    def test_escape_raises(self, tmp_workspace: Path) -> None:
        with pytest.raises(PermissionError, match='escapes workspace'):
            safe_path(tmp_workspace, '../../../etc/passwd')

    def test_absolute_inside(self, tmp_workspace: Path) -> None:
        target = tmp_workspace / 'hello.py'
        result = safe_path(tmp_workspace, str(target))
        assert result == target

    def test_absolute_outside_raises(self, tmp_workspace: Path) -> None:
        with pytest.raises(PermissionError, match='escapes workspace'):
            safe_path(tmp_workspace, '/etc/passwd')


class TestClip:
    def test_short_text_unchanged(self) -> None:
        assert clip('hello', 100) == 'hello'

    def test_long_text_truncated(self) -> None:
        result = clip('a' * 200, 100)
        assert len(result) < 200
        assert 'truncated' in result
        assert '100 chars' in result
