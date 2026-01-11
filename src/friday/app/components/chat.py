from datetime import datetime
from typing import ClassVar

from textual import events, on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Collapsible,
    Input,
    Label,
    Markdown,
    OptionList,
    Static,
)
from textual.widgets._input import Selection
from textual.widgets.option_list import Option


class CopyButton(Static):
    """Clickable icon to copy content to clipboard."""

    DEFAULT_CSS = """
    CopyButton {
        width: 3;
        height: 1;
        content-align: center middle;
        color: $text-muted;
        background: transparent;
        dock: right;
    }
    CopyButton:hover {
        color: $text;
    }
    """

    ICON_COPY: ClassVar[str] = "🗐"
    ICON_CHECK: ClassVar[str] = "✓"

    def __init__(self, content: str) -> None:
        super().__init__(self.ICON_COPY)
        self._content = content
        self.tooltip = "Copy to clipboard"

    def on_click(self) -> None:
        import pyperclip

        pyperclip.copy(self._content)
        self.update(self.ICON_CHECK)
        self.tooltip = "Copied!"
        self.set_timer(1.0, self._reset_icon)
        self.post_message(self.Copied(self._content))

    def _reset_icon(self) -> None:
        self.update(self.ICON_COPY)
        self.tooltip = "Copy to clipboard"

    class Copied(Message):
        def __init__(self, content: str) -> None:
            super().__init__()
            self.content = content


class ChatMessage(Container):
    """Base class for all chat messages."""

    DEFAULT_CSS = """
    ChatMessage {
        margin: 1 0;
        padding: 1 2;
        border: blank;
        height: auto;
        width: 1fr;
        border-title-align: left;
        border-subtitle-align: right;
    }

    ChatMessage > .chat-row {
        height: auto;
    }

    ChatMessage > .chat-row > Markdown {
        width: 1fr;
    }
    """

    def __init__(
        self, role: str, content: str = "", date_time: datetime | None = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = date_time or datetime.now()
        self.border_title = role.title()

    def on_mount(self) -> None:
        self.border_subtitle = self.timestamp.strftime("%H:%M:%S")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="chat-row"):
            yield Markdown(self.content)
            yield CopyButton(self.content)


class ChatMessageUser(ChatMessage):
    """Message sent by the user."""

    DEFAULT_CSS = """
    ChatMessageUser {
        background: #1a1a1a;
        color: $text;
        margin: 1 8 1 1;
    }
    """

    def __init__(self, content: str, **kwargs) -> None:
        super().__init__(role="user", content=content, **kwargs)


class ChatMessageAssistant(ChatMessage):
    """Message sent by the assistant."""

    DEFAULT_CSS = """
    ChatMessageAssistant {
        background: #1a1a1a;
        color: $text;
        margin: 1 1 1 8;
    }

    .thinking-content {
        color: $text-muted;
        background: #111111;
        padding: 1;
        border-left: wide $success;
    }
    """

    def __init__(
        self,
        content: str,
        thinking: str | None = None,
        cost: float | None = None,
        tokens: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(role="assistant", content=content, **kwargs)
        self.thinking_text = thinking
        self.cost = cost
        self.tokens = tokens

    def on_mount(self) -> None:
        parts = []
        if self.cost is not None:
            parts.append(f"Cost: {self.cost:.4f}")
        if self.tokens is not None:
            parts.append(f"Tokens: {self.tokens}")
        parts.append(self.timestamp.strftime("%H:%M:%S"))
        self.border_subtitle = " | ".join(parts)

    def compose(self) -> ComposeResult:
        yield from super().compose()

        if self.thinking_text:
            yield Collapsible(
                Markdown(self.thinking_text),
                classes="thinking-content",
                title="Thinking Process",
            )


class ChatMessageTool(ChatMessage):
    """Message representing tool output."""

    DEFAULT_CSS = """
    ChatMessageTool {
        background: $panel;
        color: $warning-lighten-1;
        margin: 1 4 1 4;
    }
    """

    def __init__(self, tool_name: str, output: str, **kwargs) -> None:
        # Format content as markdown code block for the base class
        formatted_content = f"```\n{output}\n```"
        super().__init__(role="tool", content=formatted_content, **kwargs)
        self.border_title = f"Tool: {tool_name}"


class ChatMessageConfirm(ChatMessage):
    """Interactive confirmation message."""

    DEFAULT_CSS = """
    ChatMessageConfirm {
        background: $surface-lighten-1;
        color: $warning;
        margin: 1 4 1 4;
        border: wide $warning;
        height: auto;
        border-title-align: center;
    }

    ChatMessageConfirm Label {
        width: 100%;
        content-align: center middle;
        padding: 1;
    }

    ChatMessageConfirm .buttons {
        width: 100%;
        height: auto;
        align: center middle;
        margin-top: 1;
    }

    ChatMessageConfirm Button {
        margin: 0 1;
    }
    """

    class Confirmed(Message):
        def __init__(self, result: bool) -> None:
            super().__init__()
            self.result = result

    def __init__(self, question: str, **kwargs) -> None:
        super().__init__(role="confirm", content=question, **kwargs)
        self.question = question
        self.border_title = "Confirmation Required"
        # Override alignment for confirm if needed, but base enforces left.
        # We can override in CSS above.

    def compose(self) -> ComposeResult:
        yield Label(self.question)
        with Horizontal(classes="buttons"):
            yield Button("Yes", variant="success", id="btn-yes")
            yield Button("No", variant="error", id="btn-no")

    @on(Button.Pressed, "#btn-yes")
    def on_yes(self) -> None:
        self.disabled = True
        self.post_message(self.Confirmed(True))

    @on(Button.Pressed, "#btn-no")
    def on_no(self) -> None:
        self.disabled = True
        self.post_message(self.Confirmed(False))


class ChatViewer(VerticalScroll):
    """Container for chat messages."""

    DEFAULT_CSS = """
    ChatViewer {
        height: 1fr;
        background: $surface;
        border: blank;
        scrollbar-gutter: stable;
    }
    """

    def add_message(self, message: ChatMessage) -> None:
        self.mount(message)
        # Ensure we scroll to the bottom when a new message arrives
        self.call_after_refresh(self.scroll_end, animate=True)

    def clear(self) -> None:
        self.remove_children()


class ChatStatus(Static):
    """Status bar showing current state or hints."""

    status = reactive("")
    is_busy = reactive(False)

    DEFAULT_CSS = """
    ChatStatus {
        height: 1;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0 1;
        text-align: right;
    }
    .busy {
        color: $warning;
    }
    """

    def render(self) -> str:
        icon = "⟳ " if self.is_busy else "● "
        return f"{icon}{self.status}"

    def watch_is_busy(self, busy: bool) -> None:
        self.set_class(busy, "busy")


class ChatInput(Vertical):
    """
    Input with autocomplete
    Layout: Vertical stack of (InputContainer) and (OptionList).
    InputContainer Input field.
    """

    DEFAULT_CSS = """
    ChatInput {
        height: auto;
        min-height: 3;
        background: #111111;
    }

    /*
        Stack input and autocomplete text
        Using dock: top allows them to overlap if we ensure container has height.
    */
    ChatInput .input-container {
        height: auto;
        min-height: 1;
        width: 100%;
        /* layout: vertical; Default is fine, docking removes from flow */
    }

    #chat-input {
        background: transparent;
        border: blank;
        width: 100%;
        height: auto;
    }

    ChatInput OptionList {
        height: auto;
        max-height: 14;
        border: blank;
        background: $surface;
        display: none;
    }
    """

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    # Public API
    value = reactive("")

    def __init__(self) -> None:
        super().__init__()
        self._history: list[str] = []
        self._history_pos: int | None = None
        self._active_token: tuple[int, int] | None = None

        self.tool_suggestions: list[tuple[str, str]] = []
        self.file_suggestions: list[str] = []
        self.max_suggestions = 8

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Type a message...", id="chat-input")
        yield OptionList(id="suggestions")

    def on_mount(self) -> None:
        self.input_widget.focus()
        self.input_widget.select_on_focus = False

    @property
    def input_widget(self) -> Input:
        return self.query_one("#chat-input", Input)

    @property
    def options_widget(self) -> OptionList:
        return self.query_one("#suggestions", OptionList)

    def clear(self) -> None:
        self.input_widget.value = ""
        self.value = ""

    # --- Event Handlers ---

    @on(Input.Changed)
    def _on_input_changed(self, event: Input.Changed) -> None:
        self.value = event.value
        self._history_pos = None  # Reset history on typing

        # Check for tokens
        token_info = self._get_current_token(
            self.value, self.input_widget.cursor_position
        )
        self._active_token = None

        if token_info:
            token, start, end = token_info
            if token.startswith("/"):
                self._active_token = (start, end)
                self._show_tools(token[1:])
                return
            elif token.startswith("@"):
                self._active_token = (start, end)
                self._show_files(token[1:])
                return

        self._hide_suggestions()

    @on(Input.Submitted)
    def _on_submit(self, event: Input.Submitted) -> None:
        event.stop()
        text = event.value.strip()
        if text:
            self._history.append(text)
            self.post_message(self.Submitted(text))

    @on(OptionList.OptionSelected)
    def _on_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if self._active_token:
            self._apply_suggestion(event.option)

    @on(OptionList.OptionHighlighted)
    def _on_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        event.stop()
        if event.option:
            self._apply_suggestion(event.option)

    # --- Key Handling ---

    def on_key(self, event: events.Key) -> None:
        options = self.options_widget

        if options.display:
            # Navigation mode
            if event.key == "escape":
                event.stop()
                self._hide_suggestions()
            elif event.key == "enter":
                event.stop()
                self._select_highlighted()
            elif event.key in ("up", "down", "pageup", "pagedown", "home", "end"):
                event.stop()
                self._navigate_options(event.key, options)
        else:
            # History mode
            if event.key in ("up", "down") and self._navigate_history(event.key):
                event.stop()

    # --- Logic ---

    def _get_current_token(self, text: str, cursor: int) -> tuple[str, int, int] | None:
        if not text:
            return None
        cursor = min(cursor, len(text))
        start = cursor
        while start > 0 and not text[start - 1].isspace():
            start -= 1
        end = cursor
        while end < len(text) and not text[end].isspace():
            end += 1
        return (text[start:end], start, end)

    def _show_tools(self, query: str) -> None:
        query = query.lower()
        matches = [
            Option(f"{name} — {desc}", id=name)
            for name, desc in self.tool_suggestions
            if query in name.lower() or query in desc.lower()
        ]
        self._display_choices(matches)

    def _show_files(self, query: str) -> None:
        query = query.lower()
        matches = [
            Option(f"@{path}", id=f"@{path}")
            for path in self.file_suggestions
            if query in path.lower()
        ]
        self._display_choices(matches)

    def _display_choices(self, options: list[Option]) -> None:
        w = self.options_widget
        w.clear_options()
        if not options:
            self._hide_suggestions()
            return
        w.add_options(options[: self.max_suggestions])
        w.display = True
        w.highlighted = 0

    def _hide_suggestions(self) -> None:
        self.options_widget.display = False

    def _apply_suggestion(self, option: Option) -> None:
        if not self._active_token:
            return

        insert = str(option.id)
        start, end = self._active_token

        # Reconstruct
        new_val = f"{self.value[:start]}{insert} {self.value[end:]}"
        self.input_widget.value = new_val

        # Move cursor
        new_cursor = start + len(insert) + 1
        self.input_widget.selection = Selection.cursor(new_cursor)

        self._hide_suggestions()
        self.input_widget.focus()

    def _select_highlighted(self) -> None:
        opts = self.options_widget
        if opts.highlighted is not None:
            self._apply_suggestion(opts.get_option_at_index(opts.highlighted))

    def _navigate_options(self, key: str, list_widget: OptionList) -> None:
        if key == "down":
            list_widget.action_cursor_down()
        elif key == "up":
            list_widget.action_cursor_up()
        elif key == "pageup":
            list_widget.action_page_up()
        elif key == "pagedown":
            list_widget.action_page_down()
        elif key == "home":
            list_widget.action_first()
        elif key == "end":
            list_widget.action_last()

    def _navigate_history(self, key: str) -> bool:
        if self.value and self._history_pos is None:
            return False
        if not self._history:
            return False

        if key == "up":
            if self._history_pos is None:
                self._history_pos = len(self._history) - 1
            elif self._history_pos > 0:
                self._history_pos -= 1
        elif key == "down":
            if self._history_pos is None:
                return False
            if self._history_pos < len(self._history) - 1:
                self._history_pos += 1
            else:
                self._history_pos = None
                self.input_widget.value = ""
                return True

        if self._history_pos is not None:
            self.input_widget.value = self._history[self._history_pos]
            self.input_widget.action_end()  # Move cursor to end
            return True
        return False
