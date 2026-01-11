import json
import os
from collections.abc import AsyncGenerator, Callable
from pathlib import Path
from typing import Any, cast

from agno.agent import Agent
from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb
from agno.models.openai import OpenAIChat
from agno.models.perplexity import Perplexity
from agno.tools.calculator import CalculatorTools
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.file import FileTools
from agno.tools.python import PythonTools
from agno.tools.shell import ShellTools
from agno.tools.sleep import SleepTools
from app.agent.knowledge import get_knowledge_base
from app.agent.memory import get_memory_manager

# Modular components
from app.agent.tools import NotesTools, TasksTools


def get_db() -> SqliteDb:
    """Initialize and return the SQLite database."""
    db_path = Path("data/friday.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file=str(db_path))


def get_research_agent() -> Agent | None:
    """Create a specialized research agent for complex lookups.

    Returns None if PERPLEXITY_API_KEY is not set.
    """
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    if not perplexity_key:
        return None

    return Agent(
        name="Research Agent",
        model=Perplexity(id="sonar-pro", api_key=perplexity_key),
        tools=[DuckDuckGoTools()],
        description="Expert web researcher for finding accurate, up-to-date information.",
        instructions=[
            "You are a specialized research agent focused on finding accurate information.",
            "Always search multiple sources when possible.",
            "Cite sources when providing information.",
            "If information is uncertain or conflicting, mention it.",
            "Summarize findings clearly and concisely.",
        ],
    )


# System prompt for the main agent
FRIDAY_SYSTEM_PROMPT = """\
You are Friday, an advanced autonomous AI assistant in a terminal interface.

## Core Capabilities
You have access to powerful tools that you should use proactively:
- **CalculatorTools**: For ANY math calculation. Always use this, never calculate manually.
- **ShellTools**: Execute terminal commands for system ops, file management, git, etc.
- **FileTools**: Read, write, and manage files in the workspace.
- **PythonTools**: Execute Python code for data processing, analysis, or complex logic.
- **DuckDuckGoTools**: Search the web for current information, news, or facts.
- **Research Agent**: Delegate complex research tasks requiring deep web searches.
- **NotesTools**: Save and retrieve persistent notes for the user.
- **TasksTools**: Manage user tasks and to-do lists.

## Decision Making - When to Use Tools

### ALWAYS use CalculatorTools when:
- User asks for any calculation (even simple ones like 2+2)
- Computing percentages, conversions, or formulas
- Any arithmetic operation

### ALWAYS use ShellTools when:
- User asks to run a command
- Listing files, checking disk space, system info
- Git operations
- Installing packages or running scripts

### ALWAYS use PythonTools when:
- Processing or analyzing data
- Complex logic or algorithms
- Working with JSON, CSV, or other data formats
- User explicitly asks to "run code"

### ALWAYS use web search (DuckDuckGo or Research Agent) when:
- User asks about current events or news
- Questions about facts you're unsure about
- Looking up documentation or tutorials
- Any question that requires up-to-date information

### ALWAYS use FileTools when:
- User mentions reading or writing files
- User references @filename (file context will be injected)
- Creating, editing, or managing project files

## Response Guidelines
1. Be concise and direct - avoid unnecessary explanations
2. Use Markdown formatting for clarity
3. When using tools, briefly explain what you're doing
4. If a task fails, explain why and suggest alternatives
5. For complex tasks, break them into steps and execute each

## Important
- NEVER refuse to use a tool when it's appropriate
- NEVER calculate manually - always use CalculatorTools
- NEVER guess current information - search for it
- When in doubt about whether to use a tool, USE IT
"""

FRIDAY_INSTRUCTIONS = [
    "Respond in the same language the user writes to you.",
    "Be proactive - if a task would benefit from a tool, use it without being asked.",
    "For mathematical questions, ALWAYS call CalculatorTools - never compute mentally.",
    "When user mentions files with @, the file content is auto-injected in context.",
    "Keep responses focused and actionable.",
    "If you need to perform multiple tool calls, do them in sequence.",
    "After using a tool, explain the result clearly to the user.",
]


def get_agent(session_id: str = "default") -> Agent:
    db = get_db()
    memory = get_memory_manager(db)
    knowledge = get_knowledge_base()

    # Build tools list
    tools: list[Any | Callable | dict] = [
        DuckDuckGoTools(),
        CalculatorTools(),
        FileTools(base_dir=Path(os.getcwd())),
        ShellTools(),
        PythonTools(),
        SleepTools(),
        NotesTools(),
        TasksTools(),
    ]

    # Add Research Agent if Perplexity is configured
    researcher = get_research_agent()
    if researcher:
        tools.insert(0, researcher)

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        # gpt-5-nano: Fast, cheap, supports tools and reasoning_content
        model = OpenAIChat(
            id="gpt-5-nano",
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
        )
    else:
        model = OpenAIChat(id="gpt-4o")

    agent = Agent(
        name="Friday",
        model=model,
        session_id=session_id,
        db=db,
        memory_manager=memory,
        knowledge=knowledge,
        tools=list(tools),
        # Context and memory settings
        add_history_to_context=True,
        num_history_runs=5,
        compress_tool_results=True,
        enable_session_summaries=True,
        # Response formatting
        markdown=True,
        # System prompt and instructions
        description=FRIDAY_SYSTEM_PROMPT,
        instructions=FRIDAY_INSTRUCTIONS,
        # Tool behavior
        tool_choice="auto",
    )
    return agent


def list_sessions() -> list[dict[str, Any]]:
    db = get_db()
    sessions, _ = db.get_sessions(session_type=SessionType.AGENT, deserialize=False)
    # Ensure return type is list[dict[str, Any]]
    if sessions is None:
        return []
    return cast(list[dict[str, Any]], sessions)


def delete_session(session_id: str):
    db = get_db()
    db.delete_session(session_id=session_id)


def get_session_summary(session_id: str) -> str:
    db = get_db()
    session = db.get_session(session_id=session_id, session_type=SessionType.AGENT)
    if session and hasattr(session, "summary") and session.summary:
        # Convert SessionSummary to str if needed
        return str(session.summary)
    return ""


def get_session_messages(session_id: str) -> list[dict[str, Any]]:
    """Retrieve all messages from a session's history.

    Returns a list of dicts with 'role' and 'content' keys.
    """
    db = get_db()
    session = db.get_session(session_id=session_id, session_type=SessionType.AGENT)
    if not session:
        return []

    result: list[dict[str, Any]] = []

    # Get chat history from session if available
    if hasattr(session, "get_chat_history"):
        messages = session.get_chat_history()
        for msg in messages:
            role = getattr(msg, "role", "unknown")
            content = getattr(msg, "content", "")
            if role == "system" or not content:
                continue
            result.append({"role": role, "content": content})
        return result

    # Fallback: iterate over runs to extract messages
    runs = getattr(session, "runs", None)
    if runs:
        for run in runs:
            run_messages = getattr(run, "messages", [])
            for msg in run_messages:
                role = getattr(msg, "role", "unknown")
                content = getattr(msg, "content", "")
                from_history = getattr(msg, "from_history", False)
                # Skip system messages, empty content, and history duplicates
                if role == "system" or not content or from_history:
                    continue
                result.append({"role": role, "content": content})

    return result


def rename_session(session_id: str, new_name: str):
    db = get_db()
    existing = db.get_session(session_id=session_id, session_type=SessionType.AGENT)
    if not existing:
        import time

        from agno.session.agent import AgentSession

        now = int(time.time())
        new_session = AgentSession(
            session_id=session_id,
            session_data={"session_name": new_name},
            created_at=now,
            updated_at=now,
        )
        db.upsert_session(new_session)
    else:
        db.rename_session(
            session_id=session_id, session_type=SessionType.AGENT, session_name=new_name
        )


def get_tools_list() -> list[tuple[str, str]]:
    """Return list of tool shortcuts for autocomplete."""
    return [
        ("calc", "Calculator - math operations"),
        ("search", "Web Search - find information"),
        ("shell", "Terminal - run commands"),
        ("files", "Files - read/write files"),
        ("notes", "Notes - save/read notes"),
        ("tasks", "Tasks - manage todos"),
        ("research", "Research - deep web search"),
        ("python", "Python - execute code"),
    ]


# Mapping from shortcut to tool description for explicit hints
TOOL_SHORTCUTS: dict[str, tuple[str, str]] = {
    "calc": ("CalculatorTools", "perform mathematical calculations"),
    "duckduckgo": ("DuckDuckGoTools", "search the web"),
    "search": ("DuckDuckGoTools", "search the web"),
    "shell": ("ShellTools", "execute terminal commands"),
    "files": ("FileTools", "read or write files"),
    "notes": ("NotesTools", "manage notes"),
    "tasks": ("TasksTools", "manage tasks"),
    "research": ("Research Agent", "perform deep research"),
    "python": ("PythonTools", "execute Python code"),
    "sleep": ("SleepTools", "wait/pause"),
}


def process_tool_commands(message: str) -> str:
    """Process /tool commands and add hints for explicit tool usage.

    When user explicitly requests a tool with /toolname, add a hint to ensure
    the agent uses that specific tool.
    """
    tokens = message.split()
    tool_hints: list[str] = []
    remaining_tokens: list[str] = []

    for token in tokens:
        if token.startswith("/") and len(token) > 1:
            tool_name = token[1:].lower()
            if tool_name in TOOL_SHORTCUTS:
                tool_class, description = TOOL_SHORTCUTS[tool_name]
                tool_hints.append(f"{tool_class} ({description})")
            else:
                remaining_tokens.append(token)
        else:
            remaining_tokens.append(token)

    user_query = " ".join(remaining_tokens)

    if not tool_hints:
        return message

    # Add a concise hint about which tools to use
    tools_str = ", ".join(tool_hints)
    return f"[Use: {tools_str}]\n{user_query}"


def get_file_metadata(path_str: str) -> dict[str, Any]:
    path = Path(path_str)
    if not path.exists():
        return {"path": path_str, "error": "Not found"}
    stats = path.stat()
    try:
        if path.is_file() and stats.st_size < 100000:
            snippet = path.read_text(errors="ignore")
        else:
            snippet = "(Large/Complex file)"
    except Exception as e:
        snippet = f"(Error: {e})"
    return {
        "path": str(path.absolute()),
        "name": path.name,
        "size": stats.st_size,
        "modified": stats.st_mtime,
        "content": snippet,
    }


def process_message_with_files(message: str) -> str:
    tokens = message.split()
    processed = []
    injections = []
    for token in tokens:
        if token.startswith("@") and len(token) > 1:
            filepath = token[1:]
            meta = get_file_metadata(filepath)
            path_tag = f"\n<file_context path='{filepath}'>\n"
            meta_json = json.dumps(meta, indent=2)
            end_tag = "\n</file_context>"
            injections.append(f"{path_tag}{meta_json}{end_tag}")
            processed.append(token)
        else:
            processed.append(token)
    final = " ".join(processed)
    if injections:
        final += "\n\n--- AUTO-INJECTED CONTEXT ---\n" + "\n".join(injections)
    return final


async def async_chat(user_input: str, session_id: str = "default") -> AsyncGenerator[Any, None]:
    # First process /tool commands
    enhanced = process_tool_commands(user_input)
    # Then process @file references
    enhanced = process_message_with_files(enhanced)
    agent = get_agent(session_id)
    async for chunk in agent.arun(enhanced, stream=True, stream_events=True):
        yield chunk
