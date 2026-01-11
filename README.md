# Friday 🤖 - Advanced AI Terminal TUI

Friday is an advanced autonomous AI assistant running in a sleek Terminal TUI (Textual User Interface), powered by `agno` and high-performance LLMs.

## 🚀 Key Features

- **Interactive TUI (Textual)**:
  - **Blazing Performance**: Optimized with `textual-speedups` and update throttling for smooth interactions even during high-speed streaming.
  - **Immediate Feedback**: Loading indicators and reasoning containers appear instantly.
  - **Smart Reasoning**: Dedicated "Thinking Process" section that automatically collapses once the final answer begins.
  - **Advanced Chat Management**: `Ctrl+N` for New Chats, `Ctrl+O` for History browsing (with search & delete), and `Ctrl+R` for Renaming sessions.
- **Agentic Backend (Agno)**:
  - **SQLite Persistence**: Automatic conversation storage and context management using `agno.db.sqlite.SqliteDb`.
  - **Multi-Model Intelligence**: Hybrid reasoning using `gpt-5-nano` and `sonar-pro` (via OpenRouter/Perplexity).
  - **Knowledge & RAG**: Efficient handling of large context through file injection (`@filename`) and persistent memory.
  - **HITL Integration**: Asynchronous human-in-the-loop queue for collaborative tasks.
- **Smart Tooling**:
  - `ShellTools`, `FileTools`, `CalculatorTools`, `DuckDuckGo`, and more.
  - Interactive confirmation steps for critical operations.

## ⌨️ Keybindings

| Key | Action |
| --- | --- |
| `Ctrl+N` | Start a **New Chat** session |
| `Ctrl+O` | Open Chat **History** & Switch Sessions |
| `Ctrl+R` | **Rename** Current Chat |
| `Tab` | Autocomplete Tool (`/`) or File (`@`) suggestions |
| `Esc` | Close history or dismiss suggestions |

## 🛠 Features Implemented & Optimized

- [x] **SQLite Persistence**: Full session management integrated.
- [x] **Context Optimization**: Context compression and smart history summarization on resume.
- [x] **Performance Mode**: Throttled UI updates and `textual-speedups` for zero-lag streaming.
- [x] **Modular Architecture**: Separated logic into `agents.py`, `tools.py`, `memory.py`, and `knowledge.py`.

## 🚦 Getting Started

1. **Environment Setup**:
   ```bash
   export OPENROUTER_API_KEY=your_key
   export PERPLEXITY_API_KEY=your_key
   ```
2. **Run TUI**:
   ```bash
   uv run friday
   ```

---
*Created with ❤️ by the Friday Team.*
