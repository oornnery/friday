"""Tests for CLI commands."""

from __future__ import annotations

from typer.testing import CliRunner

from friday.cli.app import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ['--help'])
    assert result.exit_code == 0
    assert 'Friday' in result.output


def test_config_shows_settings() -> None:
    result = runner.invoke(app, ['config'])
    assert result.exit_code == 0
    assert 'default_model' in result.output


def test_models_runs_without_error() -> None:
    """Models command succeeds even without API keys configured."""
    result = runner.invoke(app, ['models'])
    assert result.exit_code == 0
