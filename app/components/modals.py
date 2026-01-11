import datetime
from typing import Any, cast

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, ListItem, ListView


class InputModal(ModalScreen[str]):
    """A simple modal to get text input (e.g., chat name) following Confirm pattern."""

    BINDINGS = [("escape", "cancel", "Close")]

    def __init__(self, title: str, initial_value: str = ""):
        super().__init__()
        self.title_text = title
        self.initial_value = initial_value

    def action_cancel(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-container"):
            yield Label(self.title_text, classes="modal-title")
            yield Input(value=self.initial_value, id="modal-input")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", variant="error", id="cancel", flat=True)
                yield Button("Ok", variant="success", id="ok", flat=True)

    @on(Button.Pressed, "#cancel")
    def cancel(self):
        self.dismiss(None)

    @on(Button.Pressed, "#ok")
    def ok(self):
        val = self.query_one("#modal-input", Input).value
        self.dismiss(val)

    @on(Input.Submitted)
    def submit(self):
        self.ok()


class HistoryItem(ListItem):
    """An item in the history list."""

    def __init__(self, session: dict[str, Any]):
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        session_id = self.session.get("session_id", "N/A")
        session_data = self.session.get("session_data") or {}
        name = session_data.get("session_name") or f"Session {session_id[:8]}"
        created_at = self.session.get("created_at") or 0

        dt = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")

        yield Label(f"[bold]{name}[/bold] | {dt}")
        yield Label(f"[dim]{session_id}[/dim]", classes="id-label")


class HistoryScreen(ModalScreen[str]):
    """A screen to browse and manage old chats."""

    BINDINGS = [("escape", "close", "Close")]

    def __init__(self, sessions: list[dict[str, Any]]):
        super().__init__()
        # Sort sessions by created_at descending (most recent first)
        self.all_sessions = sorted(
            sessions, key=lambda s: s.get("created_at", 0), reverse=True
        )
        self.filtered_sessions = self.all_sessions

    def action_close(self) -> None:
        self.dismiss(None)

    def compose(self) -> ComposeResult:
        with Vertical(id="history-container"):
            yield Label("Chat History", classes="modal-title")
            yield Input(placeholder="Search by name, summary...", id="search-input")
            yield ListView(id="history-list")
            with Horizontal(classes="buttons", id="history-footer"):
                yield Button("Delete", variant="error", id="delete-btn", flat=True)
                yield Button("Open", variant="success", id="open-btn", flat=True)

    def on_mount(self) -> None:
        self.refresh_list()
        # Focus on search input first
        self.query_one("#search-input", Input).focus()

    def refresh_list(self) -> None:
        list_view = self.query_one("#history-list", ListView)
        list_view.clear()
        for session in self.filtered_sessions:
            list_view.append(HistoryItem(session))
        # Select first item if available
        if self.filtered_sessions:
            list_view.index = 0

    @on(Input.Changed, "#search-input")
    def filter_history(self, event: Input.Changed):
        query = event.value.lower()
        if not query:
            self.filtered_sessions = self.all_sessions
        else:
            self.filtered_sessions = [
                s
                for s in self.all_sessions
                if query in str(s.get("session_data", {})).lower()
                or query in str(s.get("summary", "")).lower()
                or query in s.get("session_id", "").lower()
            ]
        self.refresh_list()

    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected):
        if event.item:
            # Cast item to HistoryItem to access .session
            item = cast(HistoryItem, event.item)
            session_id = item.session.get("session_id")
            self.dismiss(cast(str, session_id))

    @on(Button.Pressed, "#open-btn")
    def open_selected(self):
        list_view = self.query_one("#history-list", ListView)
        if list_view.index is not None and list_view.children:
            item = cast(HistoryItem, list_view.children[list_view.index])
            session_id = item.session.get("session_id")
            self.dismiss(cast(str, session_id))

    @on(Button.Pressed, "#delete-btn")
    def delete_selected(self):
        list_view = self.query_one("#history-list", ListView)
        if list_view.index is not None and list_view.children:
            # Cast children element to HistoryItem
            item = cast(HistoryItem, list_view.children[list_view.index])
            session_id = item.session.get("session_id")
            self.post_message(self.DeleteRequested(cast(str, session_id)))

    class DeleteRequested(Message):
        def __init__(self, session_id: str):
            super().__init__()
            self.session_id = session_id
