"""Textual-based TUI."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from rich import box
from rich.console import Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Input, OptionList, RichLog, Static
from textual.widgets._input import Selection
from textual.widgets.option_list import Option

from friday.bus import topics
from friday.bus.broker import EventBus
from friday.bus.schemas import (
    InputTextPartial,
    OutputText,
    ToolCall,
    build_input_text,
    new_call_id,
)
from friday.core.scheduler import TaskScheduler
from friday.core.settings import Settings
from friday.mcp.client import MCPClient
from friday.tools.gateway import ToolGateway
from friday.tools.registry import ToolRegistry, register_mcp_tools
from friday.voice.controller import VoiceController


class AssistantApp(App):
    CSS_PATH = "style.tcss"
    AUTO_FOCUS = "#input"
    MAX_SUGGESTIONS = 8
    FILE_SCAN_LIMIT = 200

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("f2", "ptt", "PTT"),
        ("f3", "toggle_vad", "Toggle VAD"),
        ("f8", "capture_screen", "Screenshot"),
        ("ctrl+r", "rerun", "Rerun"),
    ]

    def __init__(
        self,
        settings: Settings,
        bus: EventBus | None = None,
        scheduler: TaskScheduler | None = None,
        tool_registry: ToolRegistry | None = None,
        tool_gateway: ToolGateway | None = None,
        mcp_client: MCPClient | None = None,
        register_mcp: Callable[[ToolRegistry, MCPClient], None] | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings
        self._bus = bus
        self._scheduler = scheduler
        self._tool_registry = tool_registry
        self._tool_gateway = tool_gateway
        self._mcp_client = mcp_client
        self._register_mcp = register_mcp or register_mcp_tools
        self._voice = VoiceController(settings, bus) if bus else None

        self._tool_suggestions: list[tuple[str, str]] = []
        self._file_suggestions: list[str] = []
        self._file_scan_started = False
        self._active_token: tuple[int, int] | None = None
        self._suppress_submit = False  # prevent sending right after autocomplete insert
        self._history: list[str] = []
        self._history_pos: int | None = None
        self._confirm_active = False
        self._confirm_prompt = ""
        self._confirm_inflight = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="chat")
        yield Static(self._status_text(), id="status")
        yield Input(placeholder="Type a message...", id="input")
        yield Static("", id="confirm_prompt")
        yield OptionList(id="confirm")
        yield OptionList(id="suggestions")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_tool_suggestions()
        self._start_file_indexing()
        self._hide_suggestions()
        self._hide_confirm()
        self.query_one(Input).select_on_focus = False

        if self._bus is None:
            return

        self._bus.subscribe(topics.OUTPUT_TEXT, self._handle_output)
        self._bus.subscribe(topics.INPUT_TEXT_PARTIAL, self._handle_partial)

        if self._scheduler is not None:
            self.run_worker(self._scheduler.run(), exclusive=True)

        if self._mcp_client is not None and self._tool_registry is not None:
            self.run_worker(self._connect_mcp(), exclusive=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()

        if self._confirm_active:
            await self._submit_confirm(text)
            event.input.value = ""
            return

        if self._suppress_submit:
            self._suppress_submit = False
            event.stop()
            return

        if self._suggestions_visible():
            option_list = self.query_one("#suggestions", OptionList)
            if self._active_token is not None:
                option = option_list.highlighted_option or (
                    option_list.get_option_at_index(0) if option_list.option_count else None
                )
                if option is not None:
                    self._apply_option(option)
            self._suppress_submit = False
            event.stop()
            return

        if not text:
            return

        self._write_chat("user", text)
        self._history.append(text)
        self._history_pos = None
        event.input.value = ""
        self._hide_suggestions()

        if self._bus is None:
            return

        message = build_input_text(self._settings.session_id, text, "tui")
        self._set_status("Thinking…")
        await self._bus.publish(topics.INPUT_TEXT, message)

    def on_input_changed(self, event: Input.Changed) -> None:
        token, start, end = self._current_token(event.value, event.input.cursor_position)
        if event.value:
            self._history_pos = None

        if token and token.startswith("/"):
            options = self._tool_options(token[1:])
            self._active_token = (start, end)
            self._show_options(options)
            return

        if token and token.startswith("@"):
            options = self._file_options(token[1:])
            self._active_token = (start, end)
            self._show_options(options)
            return

        self._active_token = None
        self._hide_suggestions()

    def on_key(self, event: events.Key) -> None:
        if self._confirm_active:
            self._handle_confirm_keys(event)
            return

        option_list = self.query_one("#suggestions", OptionList)
        input_widget = self.query_one(Input)

        if event.key == "escape" and self._suggestions_visible():
            event.stop()
            self._active_token = None
            self._hide_suggestions()
            self.set_focus(input_widget)
            return

        if self._handle_history_nav(event, input_widget):
            return

        if self._suggestions_visible() and self.focused is input_widget:
            if event.key == "enter":
                event.stop()
                self._suppress_submit = True
                if self._active_token is not None:
                    option = option_list.highlighted_option or (
                        option_list.get_option_at_index(0) if option_list.option_count else None
                    )
                    if option is not None:
                        self._apply_option(option)
                return

            if event.key in {"down", "up", "pageup", "pagedown", "home", "end"}:
                event.stop()
                if not option_list.option_count:
                    return
                if option_list.highlighted is None:
                    option_list.highlighted = 0
                    return
                if event.key == "down":
                    option_list.action_cursor_down()
                elif event.key == "up":
                    option_list.action_cursor_up()
                elif event.key == "pageup":
                    option_list.action_page_up()
                elif event.key == "pagedown":
                    option_list.action_page_down()
                elif event.key == "home":
                    option_list.action_first()
                elif event.key == "end":
                    option_list.action_last()
                return

        if (
            event.key == "up"
            and self.focused is option_list
            and option_list.highlighted in (None, 0)
        ):
            event.stop()
            self.set_focus(input_widget)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "confirm" and self._confirm_active:
            event.stop()
            asyncio.create_task(self._submit_confirm(event.option.id or "no"))
            return

        if event.option_list.id != "suggestions":
            return

        if self._active_token is None:
            return

        event.stop()
        self._apply_option(event.option)

    async def _handle_output(self, message: object) -> None:
        if not isinstance(message, OutputText):
            return

        self._write_chat("assistant", message.text)
        self._set_status(self._status_text())

        # reset confirmation state if agent reports an error or completes
        if self._confirm_active:
            self._hide_confirm()

        if self._voice and self._settings.voice_tts_enabled:
            if self._voice.error():
                return
            try:
                await self._voice.speak(message.text)
            except Exception as exc:
                self._set_status(f"TTS error: {exc}")

    async def _handle_partial(self, message: object) -> None:
        if not isinstance(message, InputTextPartial):
            return
        self._set_status(f"partial: {message.text}")

    def action_ptt(self) -> None:
        if self._voice is None:
            self._set_status("Voice not configured")
            return
        self.run_worker(self._toggle_ptt(), exclusive=True)

    def action_toggle_vad(self) -> None:
        if self._voice is None:
            self._set_status("Voice not configured")
            return
        self.run_worker(self._toggle_vad(), exclusive=True)

    def action_capture_screen(self) -> None:
        if self._tool_gateway is None or self._bus is None:
            self._set_status("Tool gateway not configured")
            return
        self.run_worker(self._capture_screen(), exclusive=True)

    def action_rerun(self) -> None:
        self._set_status("Rerun requested (stub)")

    def _set_status(self, text: str) -> None:
        self.query_one("#status", Static).update(text)

    def _status_text(self) -> str:
        return f"session: {self._settings.session_id} | mode: {self._settings.voice_mode}"

    def _refresh_tool_suggestions(self) -> None:
        if self._tool_registry is None:
            self._tool_suggestions = []
            return
        specs = sorted(self._tool_registry.list_specs(), key=lambda spec: spec.name)
        self._tool_suggestions = [(f"/{spec.name}", spec.description) for spec in specs]

    def _start_file_indexing(self) -> None:
        if self._file_scan_started:
            return
        self._file_scan_started = True
        self.run_worker(self._load_file_suggestions(), exclusive=False)

    async def _load_file_suggestions(self) -> None:
        files = await asyncio.to_thread(
            self._scan_workspace_files, self._settings.workspace_path
        )
        self._file_suggestions = files

    def _scan_workspace_files(self, root: Path) -> list[str]:
        results: list[str] = []
        if not root.exists():
            return results

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [
                name
                for name in dirnames
                if not name.startswith(".") and name != "__pycache__"
            ]
            for filename in filenames:
                if filename.startswith("."):
                    continue
                rel_path = (Path(dirpath) / filename).relative_to(root).as_posix()
                results.append(rel_path)
                if len(results) >= self.FILE_SCAN_LIMIT:
                    return results
        return results

    async def _toggle_ptt(self) -> None:
        if self._voice is None:
            return
        try:
            await self._voice.toggle_ptt()
        except Exception as exc:
            self._set_status(f"PTT error: {exc}")
            return
        status = "PTT recording" if self._voice.ptt_recording() else "PTT stopped"
        self._set_status(status)

    async def _toggle_vad(self) -> None:
        if self._voice is None:
            return
        try:
            await self._voice.toggle_vad()
        except Exception as exc:
            self._set_status(f"VAD error: {exc}")
            return
        status = "VAD running" if self._voice.vad_running() else "VAD stopped"
        self._set_status(status)

    async def _capture_screen(self) -> None:
        if self._tool_gateway is None:
            return
        self._set_status("Capturing screenshot...")
        call = ToolCall(
            session_id=self._settings.session_id,
            call_id=new_call_id(),
            tool="screenshot.capture",
            args={},
            requires_confirm=False,
        )
        result = await self._tool_gateway.execute(call)
        if result.ok and result.result:
            path = result.result.get("data")
            if isinstance(path, str):
                self._write_chat("tool", f"Screenshot saved: {path}")
                self._set_status("Screenshot captured")
                return
        self._set_status("Screenshot failed")

    async def _connect_mcp(self) -> None:
        if self._mcp_client is None or self._tool_registry is None:
            return
        await self._mcp_client.connect()
        self._register_mcp(self._tool_registry, self._mcp_client)
        self._set_status("MCP tools registered")
        self._refresh_tool_suggestions()

    def _current_token(self, text: str, cursor: int) -> tuple[str, int, int]:
        if cursor < 0:
            cursor = 0
        cursor = min(cursor, len(text))
        start = cursor
        while start > 0 and not text[start - 1].isspace():
            start -= 1
        end = cursor
        while end < len(text) and not text[end].isspace():
            end += 1
        return text[start:end], start, end

    def _tool_options(self, query: str) -> list[Option]:
        q = query.lower()
        options: list[Option] = []
        for value, description in self._tool_suggestions:
            if q and q not in value.lower() and q not in description.lower():
                continue
            label = f"{value} — {description}"
            options.append(Option(label, id=value))
        return options[: self.MAX_SUGGESTIONS]

    def _file_options(self, query: str) -> list[Option]:
        q = query.lower()
        options: list[Option] = []
        for path in self._file_suggestions:
            if q and q not in path.lower():
                continue
            value = f"@{path}"
            options.append(Option(value, id=value))
        return options[: self.MAX_SUGGESTIONS]

    def _show_options(self, options: list[Option]) -> None:
        option_list = self.query_one("#suggestions", OptionList)
        option_list.clear_options()
        if not options:
            self._hide_suggestions()
            return
        for option in options:
            option_list.add_option(option)
        option_list.display = True
        option_list.highlighted = 0 if option_list.option_count else None
        option_list.refresh(layout=True)

    def _hide_suggestions(self) -> None:
        option_list = self.query_one("#suggestions", OptionList)
        option_list.display = False
        option_list.clear_options()

    def _suggestions_visible(self) -> bool:
        return self.query_one("#suggestions", OptionList).display

    def _apply_option(self, option: Option) -> None:
        input_widget = self.query_one(Input)
        text = input_widget.value
        start, end = self._active_token or (len(text), len(text))
        value = str(option.id or option.prompt)
        new_value = f"{text[:start]}{value} {text[end:]}"
        input_widget.value = new_value
        input_widget.selection = Selection.cursor(min(len(new_value), start + len(value) + 1))
        self._active_token = None
        self._hide_suggestions()
        self.set_focus(input_widget)

    def _handle_history_nav(self, event: events.Key, input_widget: Input) -> bool:
        if event.key not in {"up", "down"}:
            return False
        if input_widget.value or self._suggestions_visible():
            return False
        if not self._history:
            return False

        event.stop()
        if event.key == "up":
            if self._history_pos is None:
                self._history_pos = len(self._history) - 1
            elif self._history_pos > 0:
                self._history_pos -= 1
        elif event.key == "down":
            if self._history_pos is None:
                return True
            if self._history_pos < len(self._history) - 1:
                self._history_pos += 1
            else:
                self._history_pos = None
                input_widget.value = ""
                input_widget.selection = Selection.cursor(0)
                return True

        if self._history_pos is not None:
            text = self._history[self._history_pos]
            input_widget.value = text
            input_widget.selection = Selection.cursor(len(text))
        return True

    def _maybe_show_confirm(self, text: str) -> None:
        normalized = text.strip().lower()
        if (
            normalized.startswith("confirm tool call")
            or normalized.startswith("confirm with yes/no")
            or ("confirm tool call" in normalized and "yes/no" in normalized)
            or ("yes/no" in normalized and "tool" in normalized)
        ):
            self._show_confirm(text)
            return
        if normalized.startswith("cancelled tool call"):
            self._hide_confirm()
            self._set_status(self._status_text())

    def _show_confirm(self, prompt: str) -> None:
        self._confirm_active = True
        self._confirm_prompt = prompt
        confirm_list = self.query_one("#confirm", OptionList)
        confirm_text = self.query_one("#confirm_prompt", Static)
        confirm_list.display = True
        confirm_list.clear_options()
        confirm_list.add_option(Option("Yes", id="yes"))
        confirm_list.add_option(Option("No", id="no"))
        confirm_list.highlighted = 0
        confirm_list.refresh(layout=True)
        confirm_text.update(prompt)
        confirm_text.display = True
        input_widget = self.query_one(Input)
        input_widget.display = False
        self._hide_suggestions()
        self.set_focus(confirm_list)
        confirm_list.focus()
        self._set_status("Awaiting yes/no")

    def _hide_confirm(self) -> None:
        self._confirm_active = False
        self._confirm_prompt = ""
        confirm_list = self.query_one("#confirm", OptionList)
        confirm_text = self.query_one("#confirm_prompt", Static)
        confirm_list.display = False
        confirm_list.clear_options()
        confirm_text.update("")
        confirm_text.display = False
        input_widget = self.query_one(Input)
        input_widget.display = True
        self.set_focus(input_widget)

    def _handle_confirm_keys(self, event: events.Key) -> None:
        confirm_list = self.query_one("#confirm", OptionList)
        if event.key == "escape":
            event.stop()
            asyncio.create_task(self._submit_confirm("no"))
            return
        if event.key in {"down", "up"}:
            event.stop()
            if confirm_list.option_count == 0:
                return
            if confirm_list.highlighted is None:
                confirm_list.highlighted = 0
                return
            if event.key == "down":
                confirm_list.action_cursor_down()
            elif event.key == "up":
                confirm_list.action_cursor_up()
            return
        if event.key == "enter":
            event.stop()
            option = confirm_list.highlighted_option or confirm_list.get_option_at_index(0)
            asyncio.create_task(self._submit_confirm(option.id or "no"))

    async def _submit_confirm(self, answer: str) -> None:
        if self._confirm_inflight:
            return
        self._confirm_inflight = True
        try:
            if self._bus is not None:
                text = "yes" if answer.lower().startswith("y") else "no"
                self._write_chat("user", text)
                message = build_input_text(self._settings.session_id, text, "tui")
                self._set_status("Thinking…")
                await self._bus.publish(topics.INPUT_TEXT, message)
        finally:
            self._hide_confirm()
            self._confirm_inflight = False

    def _write_chat(self, role: str, text: str) -> None:
        log = self.query_one(RichLog)
        fg, bg = self._role_colors(role)
        header = Text(role, style=fg)
        body = Markdown(text, code_theme="monokai")
        content = Group(header, body)
        panel = Panel(
            content,
            box=box.MINIMAL,
            border_style=bg,
            padding=(0, 1),
            style="on " + bg,
            expand=True,
        )
        log.write(panel)
        if role == "assistant":
            self._maybe_show_confirm(text)

    def _role_colors(self, role: str) -> tuple[str, str]:
        if role == "user":
            return "cyan", "#0b1220"
        if role == "assistant":
            return "magenta", "#0b1220"
        if role == "tool":
            return "green", "#0b1220"
        return "white", "#0b1220"


def run_tui(
    settings: Settings,
    bus: EventBus | None = None,
    scheduler: TaskScheduler | None = None,
    tool_registry: ToolRegistry | None = None,
    tool_gateway: ToolGateway | None = None,
    mcp_client: MCPClient | None = None,
    register_mcp: Callable[[ToolRegistry, MCPClient], None] | None = None,
) -> None:
    app = AssistantApp(
        settings=settings,
        bus=bus,
        scheduler=scheduler,
        tool_registry=tool_registry,
        tool_gateway=tool_gateway,
        mcp_client=mcp_client,
        register_mcp=register_mcp,
    )
    app.run()
