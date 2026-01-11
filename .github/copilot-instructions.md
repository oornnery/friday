# Friday AI Assistant - Copilot Instructions

## Project Overview

Friday is a Terminal TUI LLM assistant built with **Textual** (TUI framework) and **Agno** (agentic backend). The architecture separates UI components from agent logic.

## Architecture

```
app/
├── cli.py          # Typer CLI entrypoint (uv run friday tui)
├── tui.py          # FridayApp - main Textual application
├── style.tcss      # Textual CSS styling
├── components/     # Reusable TUI widgets (ChatViewer, ChatInput, modals)
└── agent/          # Agentic backend
    ├── agents.py   # Agent factory (get_agent), session management, async_chat
    ├── tools.py    # Custom tools (NotesTools, TasksTools)
    ├── memory.py   # MemoryManager configuration
    ├── knowledge.py# Knowledge base setup
    └── queue.py    # HITL async queue for external messages
```

## Key Patterns

### Agno Agent API
- Sessions persist in `data/friday.db` via `SqliteDb`
- Use `db.get_session(session_id, SessionType.AGENT)` to retrieve sessions
- Session messages are in `session.runs[].messages[]` - filter out `from_history=True` duplicates
- Agent streams via `async for chunk in agent.arun(msg, stream=True)`

### Textual TUI Patterns
- Components extend `Container`, `VerticalScroll`, or `Static`
- Use `reactive()` for state that triggers UI updates
- Throttle frequent updates (e.g., streaming) with time-based checks
- Messages between components use `self.post_message(MyMessage(...))`
- Background tasks: `self.run_worker(coroutine, name="...", group="...")`

### File Context Injection
Messages with `@filename` are processed by `process_message_with_files()` which injects file content as `<file_context>` XML blocks.

## Commands

```bash
# Run TUI (dev mode with hot reload)
uv run textual run app/tui.py --dev

# Run TUI (production)
uv run friday tui

# Quality checks (run before committing)
uv run ruff format .
uv run ruff check . --fix
uv run ty check app tests
uv run pytest

# All-in-one check
task check
```

## Environment Variables

```bash
OPENROUTER_API_KEY  # Primary (uses gpt-5-nano via OpenRouter)
PERPLEXITY_API_KEY  # For Research Agent (sonar-pro)
```

## Conventions

- **Tooling**: Always use `uv` for packages, `ruff` for lint/format, `ty` for types
- **Async**: Use `asyncio` - never block the event loop in TUI handlers
- **Agent tools**: Extend as classes with methods (see `NotesTools`, `TasksTools`)
- **Data files**: Store in `data/` directory (notes.json, tasks.json, friday.db)
- **Tests**: Prefer real implementations over mocks; mock only external APIs
