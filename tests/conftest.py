"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    """A temporary workspace directory with a sample file."""
    sample = tmp_path / 'hello.py'
    sample.write_text('print("hello")\n', encoding='utf-8')
    return tmp_path


@pytest.fixture
def sample_file(tmp_workspace: Path) -> Path:
    return tmp_workspace / 'hello.py'
