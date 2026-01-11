"""Typer CLI for Friday."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from friday.app.main import run_app
from friday.core.settings import load_settings
from friday.mcp.client import MCPClient
from friday.mcp.config import load_mcp_config
from friday.storage.db import connect, db_path, initialize_db
from friday.storage.repos import conversations
from friday.tools.local.notes import NotesService
from friday.tools.local.tasks import TasksService
from friday.tools.registry import ToolRegistry, register_local_tools

app = typer.Typer(help="Friday assistant CLI")
console = Console()


tasks_app = typer.Typer(help="Task operations")
notes_app = typer.Typer(help="Notes operations")
tools_app = typer.Typer(help="Tools operations")
config_app = typer.Typer(help="Configuration")
export_app = typer.Typer(help="Export data")
db_app = typer.Typer(help="Database operations")
mcp_app = typer.Typer(help="MCP operations")


@app.command()
def tui() -> None:
    """Run the Textual TUI."""
    run_app()


@tasks_app.command("list")
def tasks_list() -> None:
    notes_service, tasks_service = _services()
    _ = notes_service
    tasks = tasks_service.list_tasks()
    for task in tasks:
        console.print(
            f"{task['id']} | {task['title']} | next_run={task['next_run']} "
            f"| enabled={task['enabled']}"
        )


@tasks_app.command("create")
def tasks_create(title: str, schedule: str, payload_json: str | None = None) -> None:
    _notes_service, tasks_service = _services()
    payload = json.loads(payload_json) if payload_json else None
    task_id = tasks_service.create(title=title, schedule=schedule, payload=payload)
    console.print(f"created task {task_id}")


@tasks_app.command("run")
def tasks_run(task_id: str) -> None:
    _notes_service, tasks_service = _services()
    result = tasks_service.run(task_id)
    console.print(result)


@notes_app.command("list")
def notes_list() -> None:
    notes_service, _tasks_service = _services()
    notes = notes_service.search("")
    for note in notes:
        console.print(f"{note['id']} | {note['title']}")


@notes_app.command("add")
def notes_add(title: str, content: str) -> None:
    notes_service, _tasks_service = _services()
    note_id = notes_service.append(title, content)
    console.print(f"created note {note_id}")


@notes_app.command("search")
def notes_search(query: str) -> None:
    notes_service, _tasks_service = _services()
    notes = notes_service.search(query)
    for note in notes:
        console.print(f"{note['id']} | {note['title']}")


@tools_app.command("list")
def tools_list() -> None:
    settings = load_settings()
    registry = ToolRegistry()
    register_local_tools(registry, settings)
    for spec in registry.list_specs():
        console.print(f"{spec.name} ({spec.risk_level.value})")


@config_app.command("show")
def config_show() -> None:
    settings = load_settings()
    console.print(f"workspace_path={settings.workspace_path}")
    console.print(f"data_dir={settings.data_dir}")
    console.print(f"broker_url={settings.broker_url}")
    console.print(f"voice_mode={settings.voice_mode}")
    console.print(f"session_id={settings.session_id}")
    console.print(f"mcp_config_path={settings.mcp_config_path}")
    console.print(
        f"perplexity_api_key={'set' if settings.perplexity_api_key else 'missing'}"
    )
    console.print(
        f"openrouter_api_key={'set' if settings.openrouter_api_key else 'missing'}"
    )
    console.print(f"openrouter_base_url={settings.openrouter_base_url}")
    console.print(f"openrouter_model={settings.openrouter_model}")
    console.print(f"openrouter_timeout_s={settings.openrouter_timeout_s}")
    console.print(f"openrouter_vision_model={settings.openrouter_vision_model}")
    console.print(f"perplexity_base_url={settings.perplexity_base_url}")
    console.print(f"perplexity_model={settings.perplexity_model}")
    console.print(f"perplexity_timeout_s={settings.perplexity_timeout_s}")
    console.print(f"perplexity_max_results={settings.perplexity_max_results}")
    console.print(f"web_search_provider={settings.web_search_provider}")
    console.print(f"web_search_user_agent={settings.web_search_user_agent}")
    console.print(
        f"brave_search_api_key={'set' if settings.brave_search_api_key else 'missing'}"
    )
    console.print(f"brave_search_base_url={settings.brave_search_base_url}")
    console.print(f"brave_search_timeout_s={settings.brave_search_timeout_s}")
    console.print(f"brave_search_max_results={settings.brave_search_max_results}")
    console.print(f"ddg_max_results={settings.ddg_max_results}")
    console.print(f"voice_input_device={settings.voice_input_device}")
    console.print(f"voice_output_device={settings.voice_output_device}")
    console.print(f"voice_sample_rate={settings.voice_sample_rate}")
    console.print(f"voice_frame_ms={settings.voice_frame_ms}")
    console.print(f"voice_vad_sensitivity={settings.voice_vad_sensitivity}")
    console.print(f"voice_vad_min_speech_ms={settings.voice_vad_min_speech_ms}")
    console.print(f"voice_vad_silence_ms={settings.voice_vad_silence_ms}")
    console.print(f"voice_stt_model={settings.voice_stt_model}")
    console.print(f"voice_stt_device={settings.voice_stt_device}")
    console.print(f"voice_stt_compute_type={settings.voice_stt_compute_type}")
    console.print(f"voice_stt_language={settings.voice_stt_language}")
    console.print(f"voice_stt_beam_size={settings.voice_stt_beam_size}")
    console.print(
        f"voice_stt_partial_interval_s={settings.voice_stt_partial_interval_s}"
    )
    console.print(f"voice_tts_enabled={settings.voice_tts_enabled}")
    console.print(f"voice_tts_rate={settings.voice_tts_rate}")
    console.print(f"voice_tts_volume={settings.voice_tts_volume}")
    console.print(f"voice_tts_voice={settings.voice_tts_voice}")


@export_app.command("session")
def export_session(
    session_id: str | None = None,
    out_path: Path | None = None,
) -> None:
    settings = load_settings()
    initialize_db(settings)
    store_path = db_path(settings)
    session = session_id or settings.session_id
    with connect(store_path) as conn:
        rows = conversations.list_messages(conn, session)
    payload = {
        "session_id": session,
        "messages": [
            {
                "message_id": row.message_id,
                "role": row.role,
                "content": row.content,
                "ts": row.ts,
            }
            for row in rows
        ],
    }
    output = json.dumps(payload, indent=2)
    if out_path is None:
        console.print(output)
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    console.print(f"exported session to {out_path}")


@db_app.command("init")
def db_init() -> None:
    settings = load_settings()
    initialize_db(settings)
    console.print("database initialized")


@mcp_app.command("list")
def mcp_list() -> None:
    settings = load_settings()
    client = MCPClient(load_mcp_config(settings.mcp_config_path))

    async def _run() -> None:
        await client.connect()
        for tool in client.list_tools():
            console.print(f"{tool.name} ({tool.risk_level})")
        await client.close()

    import asyncio

    asyncio.run(_run())


app.add_typer(tasks_app, name="tasks")
app.add_typer(notes_app, name="notes")
app.add_typer(tools_app, name="tools")
app.add_typer(config_app, name="config")
app.add_typer(export_app, name="export")
app.add_typer(db_app, name="db")
app.add_typer(mcp_app, name="mcp")


def _services() -> tuple[NotesService, TasksService]:
    settings = load_settings()
    initialize_db(settings)
    store_path = db_path(settings)
    return NotesService(store_path), TasksService(store_path)
