# Friday

Terminal assistant skeleton using Python, FastStream, Rich, Textual, Typer, and SQLite.

## Quickstart

- Install deps: `uv sync --extra dev`
- Install voice deps: `uv sync --extra dev --extra voice`
- Run TUI: `uv run friday tui`
- List tools: `uv run friday tools list`
- Initialize DB: `uv run friday db init`

## Configuration

Friday loads environment variables from `.env` (dev) or the OS environment.

- Required for providers:
  - `PERPLEXITY_API_KEY`
  - `OPENROUTER_API_KEY`
- Web search:
  - `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`)
  - `OPENROUTER_MODEL` (default `openrouter/auto`)
  - `OPENROUTER_TIMEOUT_S` (default `30`)
  - `OPENROUTER_VISION_MODEL` (default `openai/gpt-4o-mini`)
  - `PERPLEXITY_BASE_URL` (default `https://api.perplexity.ai`)
  - `PERPLEXITY_MODEL` (default `sonar`)
  - `PERPLEXITY_TIMEOUT_S` (default `15`)
  - `PERPLEXITY_MAX_RESULTS` (default `5`)
  - `FRIDAY_WEB_SEARCH_PROVIDER` (`auto`, `perplexity`, `brave`, `ddg`)
  - `FRIDAY_WEB_SEARCH_UA` (default `FridayBot/0.1 (+https://localhost)`)
  - `BRAVE_SEARCH_API_KEY`
  - `BRAVE_SEARCH_BASE_URL` (default `https://api.search.brave.com`)
  - `BRAVE_SEARCH_TIMEOUT_S` (default `10`)
  - `BRAVE_SEARCH_MAX_RESULTS` (default `5`)
  - `DDG_MAX_RESULTS` (default `5`)
- Voice:
  - `FRIDAY_VOICE_MODE` (`ptt`, `vad`, `both`)
  - `FRIDAY_VOICE_INPUT_DEVICE` (sounddevice input device name/id)
  - `FRIDAY_VOICE_OUTPUT_DEVICE` (sounddevice output device name/id)
  - `FRIDAY_VOICE_SAMPLE_RATE` (default `16000`)
  - `FRIDAY_VOICE_FRAME_MS` (default `30`)
  - `FRIDAY_VAD_SENSITIVITY` (default `2`)
  - `FRIDAY_VAD_MIN_SPEECH_MS` (default `180`)
  - `FRIDAY_VAD_SILENCE_MS` (default `600`)
  - `FRIDAY_STT_MODEL` (default `base`)
  - `FRIDAY_STT_DEVICE` (default `cpu`)
  - `FRIDAY_STT_COMPUTE_TYPE` (default `int8`)
  - `FRIDAY_STT_LANGUAGE` (optional, e.g. `pt`)
  - `FRIDAY_STT_BEAM_SIZE` (default `5`)
  - `FRIDAY_STT_PARTIAL_INTERVAL_S` (default `1.5`)
  - `FRIDAY_TTS_ENABLED` (default `true`)
  - `FRIDAY_TTS_RATE` (default `180`)
  - `FRIDAY_TTS_VOLUME` (default `0.9`)
  - `FRIDAY_TTS_VOICE` (optional voice id)
  - Install with `uv sync --extra voice` to enable local STT/TTS dependencies
- MCP:
  - `FRIDAY_MCP_CONFIG` (path to JSON config)
  - Example config:

```json
{
  "servers": [
    {
      "name": "local",
      "transport": "stdio",
      "command": "uvx",
      "args": ["mcp-server-example"],
      "trusted": true
    }
  ]
}
```
- Core:
  - `FRIDAY_WORKSPACE` (default `~/.friday/workspace`)
  - `FRIDAY_DATA_DIR` (default `~/.friday`)
  - `FRIDAY_BROKER_URL`
  - `FRIDAY_SESSION_ID`

Copy `.env.example` to `.env` and fill in values.

## Layout

- `src/friday/app`: Textual TUI and entrypoints
- `src/friday/core`: runtime, state, policy
- `src/friday/bus`: event topics and bus
- `src/friday/tools`: registry, gateway, local tools
- `src/friday/storage`: SQLite and repositories
- `src/friday/voice`: voice engine stubs
- `src/friday/mcp`: MCP stubs
