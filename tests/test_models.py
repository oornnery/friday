"""Tests for domain models."""

from __future__ import annotations

from friday.domain.models import AgentMode, WorkingMemory


class TestWorkingMemory:
    def test_remember_adds_item(self) -> None:
        mem = WorkingMemory()
        mem.remember(mem.files, 'a.py', 5)
        assert mem.files == ['a.py']

    def test_remember_deduplicates(self) -> None:
        mem = WorkingMemory()
        mem.remember(mem.files, 'a.py', 5)
        mem.remember(mem.files, 'b.py', 5)
        mem.remember(mem.files, 'a.py', 5)
        assert mem.files == ['b.py', 'a.py']

    def test_remember_respects_limit(self) -> None:
        mem = WorkingMemory()
        for i in range(10):
            mem.remember(mem.files, f'f{i}.py', 3)
        assert len(mem.files) == 3
        assert mem.files == ['f7.py', 'f8.py', 'f9.py']

    def test_remember_ignores_empty(self) -> None:
        mem = WorkingMemory()
        mem.remember(mem.files, '', 5)
        assert mem.files == []

    def test_render_contains_fields(self) -> None:
        mem = WorkingMemory(task='fix bug', mode=AgentMode.DEBUG)
        rendered = mem.render()
        assert 'fix bug' in rendered
        assert 'debug' in rendered
