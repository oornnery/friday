import asyncio
import os
import uuid
from contextlib import suppress
from typing import ClassVar

from textual import on
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input

# Performance: speedups
with suppress(ImportError):
    import textual_speedups  # noqa: F401

# Internal components
from app.agent.agents import (
    async_chat,
    delete_session,
    get_session_messages,
    get_session_summary,
    get_tools_list,
    list_sessions,
    rename_session,
)
from app.agent.queue import agent_queue
from app.components.chat import (
    ChatInput,
    ChatMessageAssistant,
    ChatMessageConfirm,
    ChatMessageUser,
    ChatStatus,
    ChatViewer,
)
from app.components.modals import HistoryScreen, InputModal


class FridayApp(App):
    """
    The main Friday Terminal application.
    Optimized for performance and clean UI transitions.
    """

    CSS_PATH = "style.tcss"
    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("ctrl+n", "new_chat", "New Chat"),
        ("ctrl+o", "open_history", "History"),
        ("ctrl+r", "rename_chat", "Rename Chat"),
    ]

    def __init__(self):
        super().__init__()
        # Generate initial session ID
        self.current_session_id = str(uuid.uuid4())

    def compose(self) -> ComposeResult:
        yield Header()
        yield ChatViewer()
        yield ChatStatus(id="status")
        yield ChatInput()
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the app on mount."""
        # 1. Load tools for autocomplete
        try:
            tools = get_tools_list()
        except Exception:
            tools = [("/search", "Web Search"), ("/calc", "Calculator")]

        ci = self.query_one(ChatInput)
        ci.tool_suggestions = tools

        # 2. Load files for autocomplete
        try:
            files = [f for f in os.listdir(".") if os.path.isfile(f)]
            ci.file_suggestions = files
        except Exception:
            ci.file_suggestions = ["readme.md"]

        self.query_one(ChatStatus).status = "Ready"

        # 3. Check for history summary (Resuming session)
        self.run_worker(
            self.resume_chat(self.current_session_id), name="ResumeChat", group="background"
        )

        # 4. Start HITL queue worker
        self.run_worker(self.queue_worker(), name="QueueWorker", group="background", exclusive=True)

    async def queue_worker(self):
        """Worker that listens to the external HITL message queue."""
        while True:
            try:
                msg = await agent_queue.get()
                self.call_next(self.handle_external_message, msg)
                agent_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error silently to avoid TUI spam
                await asyncio.sleep(1)

    async def handle_external_message(self, text: str):
        """Inject external message into chat and trigger agent."""
        v = self.query_one(ChatViewer)
        v.add_message(ChatMessageUser(f"[Async] {text}"))
        self.run_worker(self.process_input(text), name="AgentRun-Async", group="agent")

    async def action_new_chat(self) -> None:
        """Reset session and clear chat."""

        def check_name(name: str | None):
            if name:
                self.current_session_id = str(uuid.uuid4())
                rename_session(self.current_session_id, name)
                self.query_one(ChatViewer).clear()
                self.notify(f"Started: {name}")

        self.push_screen(InputModal("New Chat Name"), check_name)

    async def action_open_history(self) -> None:
        """Browse and switch between sessions."""
        sessions = list_sessions()

        def on_select(sid: str | None):
            if sid:
                self.current_session_id = sid
                self.query_one(ChatViewer).clear()
                self.notify(f"Chat: {sid[:8]}")
                self.run_worker(self.resume_chat(sid), name="ResumeChat", group="background")

        screen = HistoryScreen(sessions)

        @on(HistoryScreen.DeleteRequested)
        def handle_delete(ev: HistoryScreen.DeleteRequested):
            delete_session(ev.session_id)
            self.notify("Deleted")
            screen.all_sessions = list_sessions()
            try:
                inp = screen.query_one("#search-input", Input)
                screen.filter_history(Input.Changed(inp, inp.value))
            except Exception:
                pass

        self.push_screen(screen, on_select)

    async def action_rename_chat(self) -> None:
        """Rename current active session."""

        def do_rename(name: str | None):
            if name:
                rename_session(self.current_session_id, name)
                self.notify(f"Renamed: {name}")

        self.push_screen(InputModal("Rename Chat"), do_rename)

    async def resume_chat(self, sid: str):
        """Load previous messages when resuming a session."""
        viewer = self.query_one(ChatViewer)

        # Load messages from history
        messages = get_session_messages(sid)
        for msg_data in messages:
            role = msg_data.get("role", "")
            content = msg_data.get("content", "")
            if not content:
                continue
            if role == "user":
                viewer.add_message(ChatMessageUser(content))
            elif role == "assistant":
                # Mark as from_history to disable loading/thinking UI
                viewer.add_message(ChatMessageAssistant(content=content, from_history=True))

        # Optionally show summary if available and no messages loaded
        if not messages:
            summary = get_session_summary(sid)
            if summary:
                txt = f"Summary: {summary}"
                viewer.add_message(ChatMessageAssistant(content=txt, from_history=True))

    async def on_chat_input_submitted(self, event: ChatInput.Submitted):
        """Handle user input submission."""
        val = event.value.strip()
        if not val:
            return

        # Add user message to UI
        self.query_one(ChatViewer).add_message(ChatMessageUser(val))
        self.query_one(ChatInput).clear()

        # Process with agent
        self.run_worker(self.process_input(val), name="AgentRun", group="agent")

    async def process_input(self, text: str):
        """Stream agent response and handle thinking/loading states."""
        status = self.query_one(ChatStatus)
        status.status = "Thinking..."
        status.is_busy = True

        # Initial message
        msg = ChatMessageAssistant(content="")
        self.query_one(ChatViewer).add_message(msg)

        full = ""
        is_first = True

        try:
            sid = self.current_session_id
            async for chunk in async_chat(text, sid):
                # 1. Handle Reasoning/Thinking
                res = getattr(chunk, "reasoning_content", None)
                if not res and hasattr(chunk, "delta"):
                    res = getattr(chunk.delta, "reasoning_content", None)
                if res:
                    msg.update_thinking(res)

                # 2. Handle Final Content
                con = getattr(chunk, "content", None)
                if not con and hasattr(chunk, "delta"):
                    con = getattr(chunk.delta, "content", None)
                if con:
                    if is_first:
                        # Transitions
                        msg.stop_loading()
                        msg.stop_thinking()  # Collapse thinking on content start
                        status.status = "Writing..."
                        is_first = False

                    full += con
                    msg.update_content(full)

        except Exception as e:
            msg.update_content(f"Error: {e}", force=True)
        finally:
            status.status = "Ready"
            status.is_busy = False
            msg.stop_loading()

    @on(ChatMessageConfirm.Confirmed)
    async def on_confirm(self, event: ChatMessageConfirm.Confirmed):
        """Handle agent confirmation requests."""
        res = "Yes" if event.result else "No"
        v = self.query_one(ChatViewer)
        v.add_message(ChatMessageUser(f"User confirmed: {res}"))


def run_app():
    FridayApp().run()


if __name__ == "__main__":
    run_app()
