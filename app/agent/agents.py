import json
import os
from collections.abc import AsyncGenerator, Callable, Sequence
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


def get_research_agent() -> Agent:
    return Agent(
        name="Research Agent",
        model=Perplexity(id="sonar-pro"),
        tools=[DuckDuckGoTools()],
        description="Search specialist.",
        instructions="You are a research expert. Deeply search queries.",
    )


def get_agent(session_id: str = "default") -> Agent:
    db = get_db()
    memory = get_memory_manager(db)
    knowledge = get_knowledge_base()
    researcher = get_research_agent()

    # Cast tools to satisfy Agno's Agent constructor typing
    tools: Sequence[Any | Callable | dict] = [
        researcher,
        DuckDuckGoTools(),
        CalculatorTools(),
        FileTools(base_dir=Path(os.getcwd())),
        ShellTools(),
        PythonTools(),
        SleepTools(),
        NotesTools(),
        TasksTools(),
    ]

    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
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
        add_history_to_context=True,
        num_history_runs=3,
        compress_tool_results=True,
        markdown=True,
        enable_session_summaries=True,
        description="You are Friday, an advanced autonomous AI assistant.",
        instructions=[
            "Focus on precision and efficiency.",
            "Use the Research Agent for complex lookups.",
            "Use PythonTools for data processing and logic execution.",
            "Use ShellTools and FileTools for local operations, safely.",
            "Format responses in Markdown.",
            "When @filename is present, use the injected context.",
        ],
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
    return [
        ("calc", "Calculator"),
        ("duckduckgo", "Search"),
        ("shell", "Terminal"),
        ("files", "Files"),
        ("notes", "Notes"),
        ("tasks", "Tasks"),
        ("research", "Research"),
        ("python", "Python"),
        ("sleep", "Wait"),
    ]


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
    enhanced = process_message_with_files(user_input)
    agent = get_agent(session_id)
    async for chunk in agent.arun(enhanced, stream=True):
        yield chunk
