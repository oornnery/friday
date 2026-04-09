"""Interactive REPL — the main Friday chat interface."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pydantic_ai.exceptions import UserError
from rich.status import Status
from rich.table import Table

from friday.agent.context import WorkspaceContext
from friday.agent.core import create_agent
from friday.agent.deps import AgentDeps
from friday.agent.router import create_router_agent
from friday.agent.run_stats import format_turn_summary, record_turn_result
from friday.cli.completer import SLASH_COMMANDS, FridayCompleter
from friday.cli.models import fetch_models, list_models
from friday.cli.output import console, print_error, print_info, print_markdown, print_run_summary
from friday.cli.picker import pick
from friday.cli.theme import PT_STYLE, make_prompt_message
from friday.domain.models import AgentMode
from friday.infra.config import FridaySettings
from friday.infra.sessions import (
    JsonSessionStore,
    SessionData,
    SessionMeta,
    extract_last_user_message,
)


def _session_id() -> str:
    return f'{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}'


def _handle_slash(
    command: str, state: dict, settings: FridaySettings, store: JsonSessionStore
) -> bool:
    """Handle a slash command. Returns True if handled."""
    parts = command.strip().split(maxsplit=2)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ''
    arg2 = parts[2] if len(parts) > 2 else ''

    if cmd in ('/quit', '/exit'):
        raise EOFError

    if cmd == '/help':
        for name, desc in SLASH_COMMANDS.items():
            console.print(f'  [info]{name:<12}[/info] {desc}')
        return True

    if cmd == '/mode':
        return _handle_mode(arg, state)

    if cmd == '/model':
        return _handle_model(arg, state, settings)

    if cmd == '/models':
        list_models(settings, arg or None)
        return True

    if cmd == '/session':
        return _handle_session(arg, arg2, state, store)

    if cmd == '/clear':
        state['message_history'] = []
        state['session_meta'] = _new_session_meta(state)
        print_info('Conversation cleared (new session)')
        return True

    return False


# ── /mode ──────────────────────────────────────────────────────


def _handle_mode(arg: str, state: dict) -> bool:
    current = str(state.get('forced_mode', 'auto'))

    if not arg:
        # Interactive picker
        modes = ['auto', *(m.value for m in AgentMode)]
        selected = pick(items=modes, current=current, title='Select mode')
        if selected is None:
            return True
        arg = selected

    if arg.lower() == 'auto':
        state.pop('forced_mode', None)
        print_info('Switched to auto mode (router decides)')
        state['rebuild_agent'] = True
    else:
        try:
            state['forced_mode'] = AgentMode(arg.lower())
            print_info(f'Switched to {state["forced_mode"]} mode')
            state['rebuild_agent'] = True
        except ValueError:
            print_error(f'Unknown mode: {arg}')
    return True


# ── /model ─────────────────────────────────────────────────────


def _handle_model(arg: str, state: dict, settings: FridaySettings) -> bool:
    if not arg:
        # Fetch models and show interactive picker
        current = state['model']
        print_info(f'Current: {current}')

        with Status('Fetching models...', console=console, spinner='dots'):
            models = fetch_models(settings)

        if not models:
            print_error('No models found. Set API keys in .env or start Ollama.')
            return True

        # Ensure current model is in the list
        if current not in models:
            models.insert(0, current)

        selected = pick(items=models, current=current, title='Select model')
        if selected is None:
            return True
        arg = selected

    state['model'] = arg
    state['rebuild_agent'] = True
    print_info(f'Switched to model: {arg}')
    return True


# ── /session ───────────────────────────────────────────────────


def _new_session_meta(state: dict) -> SessionMeta:
    return SessionMeta(
        id=_session_id(),
        created_at=datetime.now().isoformat(),
        model=state.get('model', ''),
        mode=str(state.get('forced_mode', 'auto')),
    )


def _handle_session(subcmd: str, arg: str, state: dict, store: JsonSessionStore) -> bool:
    """Handle /session subcommands."""
    if not subcmd or subcmd == 'list':
        sessions = store.list_sessions(limit=15)
        if not sessions:
            print_info('No saved sessions.')
            return True
        table = Table(title='Sessions', show_lines=False)
        table.add_column('ID', style='info')
        table.add_column('Created', style='muted')
        table.add_column('Model', style='muted')
        table.add_column('Turns')
        table.add_column('Last message', max_width=40)
        for s in sessions:
            current_meta: SessionMeta | None = state.get('session_meta')
            active = ' *' if current_meta and s.id == current_meta.id else ''
            table.add_row(
                f'{s.id}{active}',
                s.created_at[:19],
                s.model or '-',
                str(s.turn_count),
                s.last_user_message or '-',
            )
        console.print(table)
        return True

    if subcmd == 'resume':
        if not arg:
            # Interactive picker for sessions
            sessions = store.list_sessions(limit=15)
            if not sessions:
                print_info('No sessions to resume.')
                return True
            current_meta: SessionMeta | None = state.get('session_meta')
            current_id = current_meta.id if current_meta else ''
            items = [f'{s.id}  ({s.turn_count}t) {s.last_user_message or ""}' for s in sessions]
            ids = [s.id for s in sessions]
            # Use raw IDs for selection, display labels
            selected = pick(
                items=items,
                current=next(
                    (it for it, sid in zip(items, ids, strict=True) if sid == current_id), ''
                ),
                title='Resume session',
            )
            if selected is None:
                return True
            idx = items.index(selected)
            arg = ids[idx]

        try:
            data = store.load(arg)
            state['message_history'] = data.messages
            state['session_meta'] = data.meta
            state['rebuild_agent'] = True
            print_info(f'Resumed session {data.meta.id} ({data.meta.turn_count} turns)')
        except FileNotFoundError:
            print_error(f'Session not found: {arg}')
        return True

    if subcmd == 'new':
        state['message_history'] = []
        state['session_meta'] = _new_session_meta(state)
        print_info(f'New session: {state["session_meta"].id}')
        return True

    if subcmd == 'delete':
        if not arg:
            print_error('Usage: /session delete <id>')
            return True
        if store.delete(arg):
            print_info(f'Deleted session {arg}')
        else:
            print_error(f'Session not found: {arg}')
        return True

    print_error(f'Unknown: /session {subcmd}')
    print_info('Usage: /session list | resume [id] | new | delete <id>')
    return True


# ── Session persistence ────────────────────────────────────────


def _save_session(store: JsonSessionStore, state: dict) -> None:
    """Persist the current session to disk."""
    meta: SessionMeta = state['session_meta']
    messages = state.get('message_history', [])

    serialized = []
    for msg in messages:
        if hasattr(msg, 'model_dump'):
            serialized.append(msg.model_dump(mode='json'))
        elif isinstance(msg, dict):
            serialized.append(msg)

    meta.turn_count = len(
        [m for m in serialized if isinstance(m, dict) and m.get('kind') == 'request']
    )
    meta.last_user_message = extract_last_user_message(serialized)
    meta.model = state.get('model', '')
    meta.mode = str(state.get('forced_mode', 'auto'))

    store.save(SessionData(meta=meta, messages=serialized))


# ── Main REPL ──────────────────────────────────────────────────


def run_chat(
    mode: AgentMode,
    settings: FridaySettings,
    resume_session: SessionData | None = None,
) -> None:
    """Start the interactive REPL, optionally resuming a saved session."""
    history_path = settings.config_dir.expanduser() / 'repl_history'
    history_path.parent.mkdir(parents=True, exist_ok=True)

    context = WorkspaceContext.discover()

    prompt_session: PromptSession[str] = PromptSession(
        history=FileHistory(str(history_path)),
        completer=FridayCompleter(context.repo_root),
        style=PT_STYLE,
        complete_while_typing=True,
    )

    store = JsonSessionStore(settings.session_dir)
    deps = AgentDeps(
        workspace_root=context.repo_root,
        context=context,
        settings=settings,
    )

    if resume_session:
        state: dict = {
            'model': resume_session.meta.model or settings.default_model,
            'message_history': resume_session.messages,
            'rebuild_agent': True,
            'session_meta': resume_session.meta,
        }
        mode_str = resume_session.meta.mode
        if mode_str in AgentMode.__members__.values():
            state['forced_mode'] = AgentMode(mode_str)
    else:
        state = {
            'model': settings.default_model,
            'message_history': [],
            'rebuild_agent': True,
            'session_meta': _new_session_meta({'model': settings.default_model}),
        }

    if not resume_session and mode != AgentMode.CODE:
        state['forced_mode'] = mode

    def _sync_deps_settings() -> FridaySettings:
        current_settings = settings.model_copy(update={'default_model': state['model']})
        deps.settings = current_settings
        return current_settings

    def _build_agent():
        s = _sync_deps_settings()
        if 'forced_mode' in state:
            return create_agent(AgentMode(state['forced_mode']), s, context)
        return create_router_agent(s, context)

    try:
        agent = _build_agent()
    except UserError as exc:
        print_error(f'{exc}')
        print_info('Check your API keys in .env or use --model to pick another provider.')
        return

    state['rebuild_agent'] = False

    mode_label = str(state.get('forced_mode', 'auto'))

    model_name = state['model']
    session_id = state['session_meta'].id

    console.print()
    console.print('[accent]Friday[/accent] [muted]v0.1.0[/muted]')
    console.print(
        f'[muted]mode:[/muted] [info]{mode_label}[/info]  [muted]model:[/muted] {model_name}'
    )
    if resume_session:
        turns = resume_session.meta.turn_count
        console.print(f'[muted]session:[/muted] {session_id} [muted]({turns} turns)[/muted]')
    else:
        console.print(f'[muted]session:[/muted] {session_id}')
    console.print('[muted]/help for commands · /quit to exit[/muted]')
    console.print()

    while True:
        try:
            current_mode = str(state.get('forced_mode', 'auto'))
            prompt_msg = make_prompt_message(current_mode, state['model'])
            user_input = prompt_session.prompt(prompt_msg).strip()
        except (EOFError, KeyboardInterrupt):
            if state.get('message_history'):
                _save_session(store, state)
                print_info(f'\nSession saved: {state["session_meta"].id}')
            print_info('Bye!')
            break

        if not user_input:
            continue

        if user_input.startswith('/') and _handle_slash(user_input, state, settings, store):
            continue

        if state['rebuild_agent']:
            try:
                agent = _build_agent()
            except UserError as exc:
                print_error(f'{exc}')
                print_info('Use /model to pick another, or /models to list.')
                continue
            state['rebuild_agent'] = False

        try:
            deps.turn_stats.reset()
            with Status('Thinking...', console=console, spinner='dots'):
                result = asyncio.run(
                    agent.run(
                        user_input,
                        deps=deps,
                        message_history=state['message_history'] or None,
                    )
                )
            record_turn_result(deps.turn_stats, result, state['model'])
            print_markdown(result.output)
            print_run_summary(format_turn_summary(deps.turn_stats))
            state['message_history'] = result.all_messages()
            _save_session(store, state)
        except UserError as exc:
            print_error(f'{exc}')
            print_info('Use /model to pick another, or /models to list.')
        except KeyboardInterrupt:
            print_error('\nInterrupted. Type /quit to exit.')
        except Exception as exc:
            print_error(f'Error: {exc}')


def run_chat_with_session(session_id: str, settings: FridaySettings) -> None:
    """Resume a saved session and enter chat."""
    store = JsonSessionStore(settings.session_dir)
    try:
        data = store.load(session_id)
    except FileNotFoundError:
        print_error(f'Session not found: {session_id}')
        return

    if data.meta.model:
        settings = settings.model_copy(update={'default_model': data.meta.model})

    run_chat(AgentMode.CODE, settings, resume_session=data)
