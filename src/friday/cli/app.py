"""Friday CLI — typer entry point."""

from __future__ import annotations

from typing import Annotated

import typer
from dotenv import load_dotenv

from friday.cli.ask import run_ask
from friday.cli.chat import run_chat
from friday.cli.models import list_models
from friday.cli.output import console, print_error, print_info
from friday.domain.models import AgentMode
from friday.infra.config import FridaySettings

# Load .env before anything reads env vars (providers check env directly)
load_dotenv()

app = typer.Typer(
    name='friday',
    help='Friday — LLM-powered shell agent',
    no_args_is_help=True,
    rich_markup_mode='rich',
)


def _get_settings() -> FridaySettings:
    settings = FridaySettings()
    settings.resolve_paths()
    return settings


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help='Question to ask Friday')],
    mode: Annotated[
        str | None,
        typer.Option('--mode', '-m', help='Force mode (code/reader/write/debug)'),
    ] = None,
    model: Annotated[str | None, typer.Option('--model', help='Model override')] = None,
) -> None:
    """Ask a single question. Uses the router agent by default."""
    settings = _get_settings()
    if model:
        settings = settings.model_copy(update={'default_model': model})
    agent_mode = AgentMode(mode) if mode else None
    run_ask(question, agent_mode, settings)


@app.command()
def chat(
    mode: Annotated[
        str | None,
        typer.Option('--mode', '-m', help='Force mode (code/reader/write/debug)'),
    ] = None,
    model: Annotated[str | None, typer.Option('--model', help='Model override')] = None,
) -> None:
    """Start an interactive chat session. Uses the router agent by default."""
    settings = _get_settings()
    if model:
        settings = settings.model_copy(update={'default_model': model})
    agent_mode = AgentMode(mode) if mode else AgentMode.CODE
    run_chat(agent_mode, settings)


@app.command()
def config(
    key: Annotated[str | None, typer.Argument(help='Config key to show')] = None,
) -> None:
    """Show current configuration."""
    settings = _get_settings()
    if key:
        value = getattr(settings, key, None)
        if value is None:
            console.print(f'[error]Unknown config key: {key}[/error]')
            raise typer.Exit(1)
        console.print(f'{key} = {value}')
    else:
        for field_name in FridaySettings.model_fields:
            value = getattr(settings, field_name)
            console.print(f'  {field_name} = {value}')


@app.command()
def session(
    action: Annotated[
        str,
        typer.Argument(help='Action: list, resume, delete'),
    ] = 'list',
    session_id: Annotated[
        str | None,
        typer.Argument(help='Session ID (for resume/delete)'),
    ] = None,
) -> None:
    """Manage chat sessions."""
    from rich.table import Table

    from friday.infra.sessions import JsonSessionStore

    settings = _get_settings()
    store = JsonSessionStore(settings.session_dir)

    if action == 'list':
        sessions = store.list_sessions(limit=20)
        if not sessions:
            console.print('[muted]No saved sessions.[/muted]')
            return
        table = Table(title='Sessions', show_lines=False)
        table.add_column('ID', style='cyan')
        table.add_column('Created', style='dim')
        table.add_column('Model', style='dim')
        table.add_column('Turns')
        table.add_column('Last message', max_width=50)
        for s in sessions:
            table.add_row(
                s.id,
                s.created_at[:19],
                s.model or '-',
                str(s.turn_count),
                s.last_user_message or '-',
            )
        console.print(table)

    elif action == 'delete':
        if not session_id:
            print_error('Usage: friday session delete <id>')
            raise typer.Exit(1)
        if store.delete(session_id):
            print_info(f'Deleted session {session_id}')
        else:
            print_error(f'Session not found: {session_id}')
            raise typer.Exit(1)

    elif action == 'resume':
        sid = session_id or store.latest_id()
        if not sid:
            print_error('No sessions to resume.')
            raise typer.Exit(1)
        settings = _get_settings()
        from friday.cli.chat import run_chat_with_session

        run_chat_with_session(sid, settings)

    else:
        print_error(f'Unknown action: {action}')
        print_info('Usage: friday session [list|resume|delete] [id]')
        raise typer.Exit(1)


@app.command()
def models(
    provider: Annotated[
        str | None,
        typer.Argument(help='Provider to list models from'),
    ] = None,
) -> None:
    """List available models. Queries provider APIs when keys are set.

    Examples:
        friday models            # all configured providers
        friday models openai     # only OpenAI models
        friday models | fzf      # fuzzy select
    """
    settings = _get_settings()
    list_models(settings, provider)


def main() -> None:
    app()
