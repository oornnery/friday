import time
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
    LoadingIndicator,
    Markdown,
    OptionList,
    Static,
)
from textual.widgets._input import Selection
from textual.widgets.option_list import Option

# Lazy imports for performance
_pyperclip = None


def get_pyperclip():
    global _pyperclip
    if _pyperclip is None:
        import pyperclip as _pyperclip
    return _pyperclip


class IconCopy(Static):
    """Clickable icon to copy content to clipboard."""

    ICON_COPY: ClassVar[str] = "🗐"
    ICON_CHECK: ClassVar[str] = "✓"

    def __init__(self, content: str) -> None:
        super().__init__(self.ICON_COPY)
        self._content = content
        self.tooltip = "Copy to clipboard"

    def on_click(self) -> None:
        pc = get_pyperclip()
        if pc:
            pc.copy(self._content)
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
    """Base class for all chat messages with throttled updates."""

    def __init__(
        self, role: str, content: str = "", date_time: datetime | None = None, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.role = role
        self.content = content
        self.timestamp = date_time or datetime.now()
        self.border_title = role.title()
        self._last_update = 0.0
        self._update_threshold = 0.05  # 50ms throttle for smoother TUI

    def on_mount(self) -> None:
        self.border_subtitle = self.timestamp.strftime("%H:%M:%S")

    def update_content(self, new_content: str, force: bool = False) -> None:
        self.content = new_content
        now = time.time()
        if force or (now - self._last_update > self._update_threshold):
            try:
                self.query_one(Markdown).update(new_content)
                self._last_update = now
            except Exception:
                pass

    def compose(self) -> ComposeResult:
        yield Horizontal(Markdown(self.content), IconCopy(self.content), classes="chat-row")


class ChatMessageUser(ChatMessage):
    """Message sent by the user."""

    def __init__(self, content: str, **kwargs) -> None:
        super().__init__(role="user", content=content, **kwargs)


class ChatMessageAssistant(ChatMessage):
    """Message sent by the assistant with improved thinking/loading UI."""

    is_loading = reactive(True)

    def __init__(
        self,
        content: str,
        thinking_text: str = "",
        cost: float | None = None,
        tokens: int | None = None,
        **kwargs,
    ) -> None:
        super().__init__(role="assistant", content=content, **kwargs)
        self.thinking_text = thinking_text
        self.cost = cost
        self.tokens = tokens
        self.loading_indicator = LoadingIndicator()
        self._thinking_last_update = 0.0

    def on_mount(self) -> None:
        parts = []
        if self.cost is not None:
            parts.append(f"Cost: {self.cost:.4f}")
        if self.tokens is not None:
            parts.append(f"Tokens: {self.tokens}")
        parts.append(self.timestamp.strftime("%H:%M:%S"))
        self.border_subtitle = " | ".join(parts)

    def compose(self) -> ComposeResult:
        # 1. Main Content (Response) ALWAYS ABOVE
        yield from super().compose()

        # 2. Loading Indicator (persistent until stop_loading)
        yield self.loading_indicator

        # 3. Thinking/Reasoning (Available from start, scrollable)
        with (
            Collapsible(title="Thinking Process", collapsed=False, id="thinking-collapsible"),
            VerticalScroll(classes="thinking-scroll"),
        ):
            yield Markdown(self.thinking_text or "Thinking...", id="thinking-md")

    def update_thinking(self, text: str) -> None:
        """Update the thinking text with throttling."""
        self.thinking_text += text
        now = time.time()
        if now - self._thinking_last_update > self._update_threshold:
            try:
                md = self.query_one("#thinking-md", Markdown)
                md.update(self.thinking_text)
                self._thinking_last_update = now
            except Exception:
                pass

    def stop_thinking(self) -> None:
        """Collapse thinking process and ensure final text is set."""
        try:
            # Final update
            self.query_one("#thinking-md", Markdown).update(self.thinking_text)
            # Collapse
            col = self.query_one("#thinking-collapsible", Collapsible)
            col.collapsed = True
        except Exception:
            pass

    def stop_loading(self) -> None:
        """Stop the loading state and hide indicator."""
        self.is_loading = False
        try:
            if self.loading_indicator.is_mounted:
                # Instead of removing, we should probably just hide it if we want it "available"
                # but "available from the beginning" means yielded.
                # Removing is safer for performance if it's no longer needed.
                self.loading_indicator.display = False
        except Exception:
            pass


class ChatMessageTool(ChatMessage):
    """Message representing tool output."""

    def __init__(self, tool_name: str, output: str, log_tool: str | None = None, **kwargs) -> None:
        formatted_content = f"```\n{output}\n```"
        super().__init__(role="tool", content=formatted_content, **kwargs)
        self.border_title = f"Tool: {tool_name}"
        self.log_tool = log_tool

    def compose(self) -> ComposeResult:
        yield from super().compose()
        if self.log_tool:
            yield Collapsible(
                Markdown(self.log_tool),
                classes="tool-content",
                title="Tool Log",
            )


class ChatMessageConfirm(ChatMessage):
    """Interactive confirmation message."""

    class Confirmed(Message):
        def __init__(self, result: bool) -> None:
            super().__init__()
            self.result = result

    def __init__(self, question: str, **kwargs) -> None:
        super().__init__(role="confirm", content=question, **kwargs)
        self.question = question
        self.border_title = "Confirmation Required"

    def compose(self) -> ComposeResult:
        yield Label(self.question)
        with Horizontal(classes="buttons"):
            yield Button("Yes", variant="success", id="btn-yes", flat=True)
            yield Button("No", variant="error", id="btn-no", flat=True)

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

    def add_message(self, message: ChatMessage) -> None:
        self.mount(message)
        self.call_after_refresh(self.scroll_end, animate=True)

    def clear(self) -> None:
        self.remove_children()


class ChatStatus(Static):
    """Status bar showing current state or hints."""

    status = reactive("")
    icon = reactive("●")
    is_busy = reactive(False)

    def render(self) -> str:
        return f"{self.icon} {self.status}"

    def watch_is_busy(self, busy: bool) -> None:
        self.set_class(busy, "busy")


class ChatInput(Vertical):
    """Input with autocomplete."""

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

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

    @on(Input.Changed)
    def _on_input_changed(self, event: Input.Changed) -> None:
        self.value = event.value
        self._history_pos = None

        token_info = self._get_current_token(self.value, self.input_widget.cursor_position)
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

    def on_key(self, event: events.Key) -> None:
        options = self.options_widget
        if options.display:
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
            if event.key in ("up", "down") and self._navigate_history(event.key):
                event.stop()

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
        new_val = f"{self.value[:start]}{insert} {self.value[end:]}"
        self.input_widget.value = new_val
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
            self.input_widget.action_end()
            return True
        return False
