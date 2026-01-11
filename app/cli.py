"""Typer CLI for Friday."""

from __future__ import annotations

import typer
from rich.console import Console

from app.tui import run_app

app = typer.Typer(help="Friday assistant CLI")
console = Console()


@app.command()
def tui() -> None:
    """Run the Textual TUI."""
    run_app()


if __name__ == "__main__":
    app()
