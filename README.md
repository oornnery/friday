# Friday

LLM-powered shell agent — a ZSH extension for coding, debugging, and shell assistance.

Friday lives in your terminal. Ask questions, delegate coding tasks, debug errors, and generate docs — all from your shell. It uses a conversational **router agent** that automatically delegates to specialized sub-agents based on your intent.

## Quick Start

```bash
# Install
uv sync

# Set up your API keys
cp .env.example .env
# Edit .env with your keys

# Try it
friday ask "what does this project do?"
friday chat
```

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- At least one LLM provider API key (Anthropic, OpenAI, Mistral, Z.AI, or local Ollama)

## Installation

```bash
git clone <repo-url> friday
cd friday
uv sync
```

Add to your PATH:

```bash
# Option 1: uv tool
uv tool install -e .

# Option 2: direct
export PATH="$PWD/.venv/bin:$PATH"
```

### ZSH Plugin (optional)

Source the plugin in your `.zshrc`:

```bash
source /path/to/friday/src/friday/shell/friday.plugin.zsh
```

This gives you:

| Feature               | Description                                    |
| --------------------- | ---------------------------------------------- |
| `f "question"`        | Shorthand for `friday ask`                     |
| `Ctrl+F`              | Ask Friday about current buffer / last command |
| `Ctrl+G`              | Fuzzy search session history (requires fzf)    |
| `friday-select-model` | Interactive model picker with fzf              |
| Tab completion        | Subcommands, modes, config keys                |

## Configuration

Friday reads config from three sources (in priority order):

1. Environment variables (`FRIDAY_*` prefix)
2. `.env` file in the project root
3. TOML config at `~/.config/friday/config.toml` or `friday.toml`

### API Keys (.env)

```bash
# At least one is required
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
ZAI_API_KEY=...
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
```

### TOML Config (~/.config/friday/config.toml)

```toml
default_model = "anthropic:claude-sonnet-4-20250514"
default_mode = "code"
approval_policy = "ask"   # ask | auto | never
max_steps = 25

# MCP server connections
[[mcp_servers]]
name = "filesystem"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"]
```

### Settings Reference

| Setting           | Default                               | Description                    |
| ----------------- | ------------------------------------- | ------------------------------ |
| `default_model`   | `anthropic:claude-sonnet-4-20250514`  | Default LLM model              |
| `fallback_model`  | *(empty)*                             | Fallback if default fails      |
| `default_mode`    | `code`                                | Default agent mode             |
| `approval_policy` | `ask`                                 | Confirmation for risky actions |
| `max_steps`       | `25`                                  | Max tool calls per run         |
| `session_dir`     | `~/.local/share/friday/sessions`      | Session storage path           |
| `config_dir`      | `~/.config/friday`                    | Config directory               |
| `zai_api_key`     | *(empty)*                             | Z.AI API key                   |
| `zai_base_url`    | `https://api.z.ai/api/coding/paas/v4` | Z.AI endpoint                  |

## CLI Commands

### `friday ask`

Single-shot question. Uses the router agent by default.

```bash
friday ask "explain the main function"
friday ask --mode debug "why is this test failing?"
friday ask --model ollama:llama3 "review this code"

# Pipe input
cat error.log | friday ask "what went wrong?"
git diff | friday ask "review these changes"
```

### `friday chat`

Interactive REPL with multi-turn conversation.

```bash
friday chat
friday chat --mode code
friday chat --model mistral:codestral-latest
```

REPL commands:

| Command         | Description                                    |
| --------------- | ---------------------------------------------- |
| `/help`         | Show available commands                        |
| `/mode <mode>`  | Switch mode (code, reader, write, debug, auto) |
| `/model <name>` | Switch model                                   |
| `/clear`        | Clear conversation history                     |
| `/quit`         | Exit                                           |

### `friday config`

Show current configuration.

```bash
friday config                    # Show all settings
friday config default_model      # Show specific key
```

### `friday models`

List available models from configured providers. Queries APIs dynamically.

```bash
friday models                    # All providers
friday models openai             # Only OpenAI
friday models mistral            # Only Mistral
friday models | fzf              # Fuzzy select
```

## Architecture

### Router Agent

The default agent is a **conversational router**. It talks directly to the user and delegates complex tasks to specialized sub-agents:

```text
User ──> Router ──> answer directly (conversation, simple questions)
                ├─> delegate_code   ──> Code Agent   ──> Router validates ──> User
                ├─> delegate_reader ──> Reader Agent  ──> Router validates ──> User
                ├─> delegate_writer ──> Writer Agent  ──> Router validates ──> User
                └─> delegate_debug  ──> Debug Agent   ──> Router validates ──> User
```

The router validates sub-agent output before returning it — checking relevance, completeness, and correctness.

### Agent Modes

| Mode       | Focus                       | Tools                                   |
| ---------- | --------------------------- | --------------------------------------- |
| **code**   | Write, edit, refactor, test | read, write, patch, list, search, shell |
| **reader** | Analyze and explain code    | read, list, search                      |
| **write**  | Generate docs and text      | read, write, list, search               |
| **debug**  | Diagnose errors and bugs    | read, list, search, shell               |

Each mode is defined in a markdown file under `src/friday/agent/prompts/` with YAML frontmatter:

```yaml
---
name: code
description: Coding and shell tasks.
model: null          # Override default model (null = use config)
provider: null       # Provider override
thinking: true       # Enable extended thinking
tools:
  - read_file
  - write_file
  - run_shell
max_steps: 25
---

# Code Mode

System prompt content here...
```

### Approval System

Risky tools (`write_file`, `patch_file`, `run_shell`) show a confirmation panel before executing:

```text
┌─ ⚠ Confirm action ──────────────────────┐
│ run_shell: Execute shell command         │
│                                          │
│ rm -rf node_modules && npm install       │
└──────────────────────────────────────────┘
Allow? [y/N]
```

Control with `approval_policy`:

- **ask** (default) — prompt for confirmation
- **auto** — execute without asking
- **never** — always deny risky actions

### Supported Providers

| Prefix       | Provider           | Auth                |
| ------------ | ------------------ | ------------------- |
| `anthropic:` | Anthropic (Claude) | `ANTHROPIC_API_KEY` |
| `openai:`    | OpenAI (GPT)       | `OPENAI_API_KEY`    |
| `mistral:`   | Mistral AI         | `MISTRAL_API_KEY`   |
| `zai:`       | Z.AI (GLM)         | `ZAI_API_KEY`       |
| `ollama:`    | Ollama (local)     | No key needed       |

Example model strings:

```text
anthropic:claude-sonnet-4-20250514
openai:gpt-4.1
mistral:codestral-latest
zai:glm-5.1
ollama:llama3
```

### MCP Integration

Friday supports [Model Context Protocol](https://modelcontextprotocol.io/) servers via pydantic-ai's built-in MCP client. Configure in `config.toml`:

```toml
[[mcp_servers]]
name = "github"
transport = "http"
url = "http://localhost:3000/mcp"

[[mcp_servers]]
name = "filesystem"
transport = "stdio"
command = "npx"
args = ["-y", "@modelcontextprotocol/server-filesystem", "/home/user"]
```

## Project Structure

```text
src/friday/
├── agent/               # Core AI agent logic
│   ├── core.py          # Agent factory, model resolution
│   ├── context.py       # Workspace context (git, env, shell state)
│   ├── modes.py         # Mode config loader (YAML frontmatter)
│   ├── router.py        # Conversational router with delegation
│   └── prompts/         # System prompts per mode (.md with frontmatter)
├── cli/                 # Typer CLI
│   ├── app.py           # Commands: ask, chat, config, models
│   ├── ask.py           # Single-shot handler
│   ├── chat.py          # Interactive REPL
│   ├── confirm.py       # Approval dialogs for risky actions
│   ├── models.py        # Dynamic model listing
│   └── output.py        # Rich console formatting
├── domain/              # Pure business logic
│   ├── models.py        # AgentMode, Session, WorkingMemory
│   └── permissions.py   # Path containment, output clipping
├── infra/               # IO boundary
│   ├── config.py        # FridaySettings (pydantic-settings)
│   ├── sessions.py      # JSON session store
│   └── mcp.py           # MCP server factory
├── tools/               # pydantic-ai tool implementations
│   ├── filesystem.py    # read, write, patch, list, search
│   ├── shell.py         # run_shell
│   └── registry.py      # Tool metadata
└── shell/
    └── friday.plugin.zsh  # ZSH integration
```

## Development

```bash
uv sync                  # Install dependencies
uv run task fmt          # Format (ruff)
uv run task lint         # Lint (ruff)
uv run task test         # Run tests (pytest)
uv run task check        # All of the above
```

Run a single test:

```bash
uv run pytest -v tests/test_permissions.py::TestSafePath::test_escape_raises
```

## License

MIT
