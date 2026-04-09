# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack

- **Language**: Python 3.13
- **Package manager**: uv
- **Agent framework**: pydantic-ai
- **CLI**: typer + rich + prompt_toolkit
- **Linter/Formatter**: ruff
- **Test runner**: pytest
- **Task runner**: taskipy

## Commands

```bash
uv sync                          # Install deps
uv run task fmt                  # Format (ruff format)
uv run task lint                 # Lint (ruff check)
uv run task fix                  # Lint + autofix
uv run task test                 # Run tests
uv run task check                # fmt + lint + test (full validation)
uv run pytest -v tests/path.py::test_name  # Single test
```

## Architecture

```text
src/friday/
├── domain/          # Enums, value objects, permissions (pure, no IO)
├── agent/           # pydantic-ai agent, modes, context, prompts/
├── tools/           # Tool implementations (filesystem, shell)
├── infra/           # Config, sessions, MCP client (IO boundary)
├── cli/             # Typer app, commands, rich output
└── shell/           # ZSH plugin
```

- **Prompts** live in `agent/prompts/*.md` with YAML frontmatter (tools, max_steps)
- **Modes** (code, reader, write, debug) are loaded from those .md files
- **z.ai** is wired as an OpenAI-compatible provider via `zai:` prefix
- **Config** merges: env vars (`FRIDAY_*`) > `.env` > `~/.config/friday/config.toml`

## Conventions

See `.claude/rules/python.md` for full Python conventions. Key points:

- `pathlib` over `os.path`, f-strings only, type all public functions
- `logging` for app logs, `rich` for CLI output — never `print`
- IO at edges only — domain and services must be pure
- Prefer early returns over deep nesting
- `ruff check` must pass before any commit
