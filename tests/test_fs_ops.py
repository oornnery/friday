from __future__ import annotations

import pytest

from friday.tools.local import fs_ops


def test_fs_ops_read_write(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    fs_ops.write_text(workspace, "notes/test.txt", "hello")
    assert fs_ops.read_text(workspace, "notes/test.txt") == "hello"


def test_fs_ops_escape(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    with pytest.raises(ValueError):
        fs_ops.read_text(workspace, "../secret.txt")
