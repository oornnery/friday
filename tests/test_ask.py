"""Tests for the single-shot ask command."""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from pydantic_ai.usage import RunUsage

from friday.cli import ask as ask_module
from friday.infra.config import FridaySettings


class DummyResult:
    def __init__(self) -> None:
        self.output = 'hello from friday'
        self.response = SimpleNamespace(
            model_name='claude-sonnet-4-20250514',
            provider_name='anthropic',
            provider_details=None,
        )

    def usage(self) -> RunUsage:
        return RunUsage(input_tokens=12, output_tokens=5)


class DummyAgent:
    async def run(self, question: str, deps) -> DummyResult:
        return DummyResult()


def test_run_ask_prints_summary_after_answer(monkeypatch, tmp_path: Path) -> None:
    rendered: list[str] = []
    summaries: list[str] = []

    monkeypatch.setattr(
        ask_module.WorkspaceContext,
        'discover',
        staticmethod(lambda: SimpleNamespace(repo_root=tmp_path)),
    )
    monkeypatch.setattr(ask_module.sys, 'stdin', SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(ask_module, 'create_router_agent', lambda settings, context: DummyAgent())
    monkeypatch.setattr(ask_module, 'Status', lambda *args, **kwargs: nullcontext())
    monkeypatch.setattr(ask_module, 'print_markdown', rendered.append)
    monkeypatch.setattr(ask_module, 'print_run_summary', summaries.append)

    settings = FridaySettings(
        default_model='anthropic:claude-sonnet-4-20250514',
        session_dir=tmp_path / 'sessions',
        config_dir=tmp_path / 'config',
    )
    settings.resolve_paths()

    ask_module.run_ask('hi', None, settings)

    assert rendered == ['hello from friday']
    assert summaries == [
        'model: anthropic:claude-sonnet-4-20250514  tokens: 17 total, 12 in, 5 out  cost: n/d'
    ]
