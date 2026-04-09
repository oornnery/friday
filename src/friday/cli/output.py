"""Rich console output — markdown rendering and streaming display."""

from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown

from friday.cli.theme import RICH_THEME

console = Console(theme=RICH_THEME)


def print_markdown(text: str) -> None:
    """Render markdown text to the console."""
    console.print(Markdown(text))


def print_info(text: str) -> None:
    console.print(f'[info]{text}[/info]')


def print_error(text: str) -> None:
    console.print(f'[error]{text}[/error]')


def print_success(text: str) -> None:
    console.print(f'[success]{text}[/success]')


def print_run_summary(text: str) -> None:
    """Render a compact post-response summary."""
    console.print(f'[muted]{text}[/muted]')


def print_tool_call(name: str, args: str) -> None:
    """Show a tool call in muted style."""
    console.print(f'[muted]  > {name}({args})[/muted]')
