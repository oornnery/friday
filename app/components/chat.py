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

    is_loading = reactive(False)

    def __init__(
        self,
        content: str = "",
        thinking_text: str = "",
        cost: float | None = None,
        tokens: int | None = None,
        from_history: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(role="assistant", content=content, **kwargs)
        self.thinking_text = thinking_text
        self.cost = cost
        self.tokens = tokens
        self.from_history = from_history
        self._thinking_last_update = 0.0
        self._tool_logs_last_update = 0.0
        self.tool_logs: list[dict[str, str]] = []  # List of {name, args, result}
        # Cached widget refs for performance
        self._loader: LoadingIndicator | None = None
        self._content_md: Markdown | None = None
        self._thinking_md: Markdown | None = None
        self._thinking_col: Collapsible | None = None
        self._tool_logs_md: Markdown | None = None
        self._tool_logs_col: Collapsible | None = None
        # Start loading only for new messages (not from history)
        self.is_loading = not from_history and not content

    def on_mount(self) -> None:
        parts = []
        if self.cost is not None:
            parts.append(f"Cost: {self.cost:.4f}")
        if self.tokens is not None:
            parts.append(f"Tokens: {self.tokens}")
        parts.append(self.timestamp.strftime("%H:%M:%S"))
        self.border_subtitle = " | ".join(parts)

        # Cache widget refs for performance (avoid repeated queries)
        try:
            self._loader = self.query_one("#loading-indicator", LoadingIndicator)
            self._content_md = self.query_one("#content-md", Markdown)
            self._loader.display = self.is_loading
            self._content_md.display = not self.is_loading
        except Exception:
            pass

        if not self.from_history:
            try:
                self._thinking_md = self.query_one("#thinking-md", Markdown)
                self._thinking_col = self.query_one("#thinking-collapsible", Collapsible)
                # Hide thinking by default - only show when content is received
                if self._thinking_col:
                    self._thinking_col.display = False
            except Exception:
                pass
            try:
                self._tool_logs_md = self.query_one("#tool-logs-md", Markdown)
                self._tool_logs_col = self.query_one("#tool-logs-collapsible", Collapsible)
                # Hide tool logs by default
                if self._tool_logs_col:
                    self._tool_logs_col.display = False
            except Exception:
                pass

    def compose(self) -> ComposeResult:
        # Content area - shows loading or markdown (first)
        with Vertical(id="content-area"):
            yield LoadingIndicator(id="loading-indicator")
            yield Markdown(self.content, id="content-md")
        yield IconCopy(self.content)

        # Thinking/Reasoning - only for new messages (after content)
        # Hidden by default, shown only when actual thinking content is received
        if not self.from_history:
            with (
                Collapsible(
                    title="Thinking Process",
                    collapsed=False,
                    id="thinking-collapsible",
                ),
                VerticalScroll(classes="thinking-scroll"),
            ):
                yield Markdown(self.thinking_text, id="thinking-md")

            # Tool Logs - hidden by default, only shown when tools are used
            with (
                Collapsible(title="Tool Logs", collapsed=True, id="tool-logs-collapsible"),
                VerticalScroll(classes="tool-logs-scroll"),
            ):
                yield Markdown("", id="tool-logs-md")

    def watch_is_loading(self, loading: bool) -> None:
        """Toggle visibility between loading indicator and content."""
        if self._loader and self._content_md:
            self._loader.display = loading
            self._content_md.display = not loading

    def update_content(self, new_content: str, force: bool = False) -> None:
        """Update content and switch from loading to content view."""
        self.content = new_content
        now = time.time()
        should_update = force or (now - self._last_update > self._update_threshold)
        if should_update and self._content_md:
            self._content_md.update(new_content)
            self._last_update = now

    def update_thinking(self, text: str) -> None:
        """Update the thinking text with throttling."""
        self.thinking_text += text
        now = time.time()
        should_update = now - self._thinking_last_update > self._update_threshold

        # Show thinking collapsible when first content is received
        if self._thinking_col and not self._thinking_col.display:
            self._thinking_col.display = True

        if should_update and self._thinking_md:
            self._thinking_md.update(self.thinking_text)
            self._thinking_last_update = now

    def stop_thinking(self) -> None:
        """Collapse thinking process and ensure final text is set."""
        if self._thinking_md:
            self._thinking_md.update(self.thinking_text)
        if self._thinking_col:
            # Hide entirely if no thinking content, otherwise just collapse
            if not self.thinking_text.strip():
                self._thinking_col.display = False
            else:
                self._thinking_col.collapsed = True

    def add_tool_log(self, name: str, args: str, result: str) -> None:
        """Add a tool execution log."""
        self.tool_logs.append({"name": name, "args": args, "result": result})
        # Format all logs as markdown
        logs_md = ""
        for log in self.tool_logs:
            logs_md += f"### {log['name']}\n"
            if log["args"]:
                logs_md += f"**Args:** `{log['args']}`\n\n"
            logs_md += f"```\n{log['result']}\n```\n\n"

        # Update UI - show and expand tool logs
        if self._tool_logs_col:
            self._tool_logs_col.display = True  # Show when tool is used
            self._tool_logs_col.collapsed = False  # Expand when tool is used
        if self._tool_logs_md:
            self._tool_logs_md.update(logs_md)

    def stop_loading(self) -> None:
        """Stop the loading state and show content."""
        self.is_loading = False


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
    """Input with autocomplete and large paste detection."""

    PASTE_THRESHOLD = 500  # chars threshold for "pasted content" display

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    value = reactive("")

    def __init__(self) -> None:
        super().__init__()
        self._history: list[str] = []
        # Cached widget references (set on mount)
        self._input: Input | None = None
        self._opts: OptionList | None = None
        self._history_pos: int | None = None
        self._active_token: tuple[int, int] | None = None
        self._pasted_content: str | None = None  # Store actual pasted content

        self.tool_suggestions: list[tuple[str, str]] = []
        self.file_suggestions: list[str] = []
        self.max_suggestions = 8

    def compose(self) -> ComposeResult:
        yield Input(id="chat-input", placeholder="Type a message...")
        yield OptionList(id="suggestions")

    def on_mount(self) -> None:
        # Cache widget refs for performance (avoid repeated queries)
        self._input = self.query_one("#chat-input", Input)
        self._opts = self.query_one("#suggestions", OptionList)
        self._input.focus()

    @property
    def input_widget(self) -> Input:
        # Use cached ref if available
        if self._input is not None:
            return self._input
        return self.query_one("#chat-input", Input)

    @property
    def options_widget(self) -> OptionList:
        # Use cached ref if available
        if self._opts is not None:
            return self._opts
        return self.query_one("#suggestions", OptionList)

    def clear(self) -> None:
        self.input_widget.value = ""
        self.value = ""
        self._pasted_content = None

    def _get_actual_value(self) -> str:
        """Get the actual value to submit (pasted content or input value)."""
        if self._pasted_content is not None:
            return self._pasted_content
        return self.input_widget.value

    @on(Input.Changed)
    def _on_input_changed(self, event: Input.Changed) -> None:
        text = event.value

        # If user edits after paste placeholder, clear the stored paste
        if self._pasted_content and not text.startswith("[Pasted Content"):
            self._pasted_content = None

        self.value = self._pasted_content if self._pasted_content else text
        self._history_pos = None

        # Early exit if no special chars that trigger autocomplete
        if "/" not in text and "@" not in text:
            self._hide_suggestions()
            return

        # Autocomplete logic
        cursor_pos = self.input_widget.cursor_position
        token_info = self._get_current_token(text, cursor_pos)
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

    def on_paste(self, event: events.Paste) -> None:
        """Handle paste events - detect large pastes."""
        text = event.text
        if len(text) > self.PASTE_THRESHOLD:
            # Store actual content, show placeholder
            self._pasted_content = text
            placeholder = f"[Pasted Content {len(text)} chars]"
            self.input_widget.value = placeholder
            self.value = text
            event.prevent_default()
            event.stop()

    @on(Input.Submitted)
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle submit from Input (Enter key)."""
        event.stop()
        # If suggestions are open, select highlighted instead
        if self.options_widget.display:
            self._select_highlighted()
            return
        # Otherwise submit the message
        text = self._get_actual_value().strip()
        if text:
            self._history.append(text)
            self.post_message(self.Submitted(text))

    def on_key(self, event: events.Key) -> None:
        options = self.options_widget

        # Handle suggestions navigation
        if options.display:
            if event.key == "escape":
                event.stop()
                self._hide_suggestions()
                return
            elif event.key in ("up", "down", "pageup", "pagedown"):
                event.stop()
                self._navigate_options(event.key, options)
                return

        # History navigation with Ctrl+Up/Down
        if event.key == "ctrl+up":
            event.stop()
            self._navigate_history("up")
        elif event.key == "ctrl+down":
            event.stop()
            self._navigate_history("down")

    @on(OptionList.OptionSelected)
    def _on_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if self._active_token:
            self._apply_suggestion(event.option)

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
        query_lower = query.lower()
        # Limit matches early to avoid creating too many Option objects
        matches: list[Option] = []
        for name, desc in self.tool_suggestions:
            if query_lower in name.lower() or query_lower in desc.lower():
                matches.append(Option(f"/{name} — {desc}", id=f"/{name}"))
                if len(matches) >= self.max_suggestions:
                    break
        self._display_choices(matches)

    def _show_files(self, query: str) -> None:
        query_lower = query.lower()
        # Limit matches early to avoid creating too many Option objects
        matches: list[Option] = []
        for path in self.file_suggestions:
            if query_lower in path.lower():
                matches.append(Option(f"@{path}", id=f"@{path}"))
                if len(matches) >= self.max_suggestions:
                    break
        self._display_choices(matches)

    def _display_choices(self, options: list[Option]) -> None:
        if not options:
            self._hide_suggestions()
            return
        w = self.options_widget
        w.clear_options()
        w.add_options(options)  # Already limited upstream
        w.display = True
        w.highlighted = 0

    def _hide_suggestions(self) -> None:
        self.options_widget.display = False

    def _apply_suggestion(self, option: Option) -> None:
        if not self._active_token:
            return
        insert = str(option.id)
        start, end = self._active_token

        # Update input value
        text = self.input_widget.value
        new_text = f"{text[:start]}{insert} {text[end:]}"
        self.input_widget.value = new_text
        # Move cursor after inserted text
        self.input_widget.cursor_position = start + len(insert) + 1

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
            return True
        return False
