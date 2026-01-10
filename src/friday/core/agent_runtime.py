"""Agent runtime orchestration."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from friday.bus import topics
from friday.bus.broker import EventBus
from friday.bus.schemas import (
    InputText,
    OutputText,
    ToolCall,
    new_call_id,
    new_message_id,
)
from friday.core.llm import LLMResponse, OpenRouterClient
from friday.core.policy import RiskLevel
from friday.core.state import StateStore
from friday.tools.gateway import ConfirmationRequired, ToolGateway
from friday.tools.registry import ToolRegistry
from friday.utils.time import now_ts

logger = logging.getLogger(__name__)


@dataclass
class PendingToolCall:
    session_id: str
    tool_call: ToolCall
    llm_tool_call_id: str
    messages: list[dict[str, Any]]


class AgentRuntime:
    def __init__(
        self,
        state_store: StateStore,
        tool_gateway: ToolGateway,
        tool_registry: ToolRegistry,
        llm_client: OpenRouterClient | None = None,
        max_tool_steps: int = 3,
    ) -> None:
        self._state_store = state_store
        self._tool_gateway = tool_gateway
        self._tool_registry = tool_registry
        self._llm_client = llm_client
        self._max_tool_steps = max_tool_steps
        self._pending: PendingToolCall | None = None
        self._system_prompt = _load_prompt("system.md")
        self._tool_prompt = _load_prompt("tool_instructions.md")

    async def handle_input_text(self, message: InputText) -> OutputText:
        self._state_store.add_message(
            message.session_id, "user", message.text, message.ts
        )
        if self._pending is not None:
            return await self._handle_confirmation(message)

        if self._llm_client is None:
            reply_text = f"Received: {message.text}"
            output = OutputText(
                session_id=message.session_id,
                message_id=new_message_id(),
                ts=now_ts(),
                text=reply_text,
            )
            self._state_store.add_message(
                output.session_id, "assistant", output.text, output.ts
            )
            return output

        return await self._handle_llm(message.session_id)

    async def _handle_confirmation(self, message: InputText) -> OutputText:
        decision = message.text.strip().lower()
        if decision in {"y", "yes"}:
            pending = self._pending
            if pending is None:
                return _output_text(message.session_id, "No pending tool call.")
            self._pending = None
            confirmed_call = ToolCall(
                session_id=pending.tool_call.session_id,
                call_id=pending.tool_call.call_id,
                tool=pending.tool_call.tool,
                args=pending.tool_call.args,
                requires_confirm=False,
            )
            result = await self._tool_gateway.execute(confirmed_call)
            tool_content = json.dumps(
                result.result if result.result is not None else {"error": result.error}
            )
            self._state_store.add_message(
                message.session_id, "tool", tool_content, now_ts()
            )
            pending.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": pending.llm_tool_call_id,
                    "content": tool_content,
                }
            )
            if self._llm_client is None:
                return _output_text(message.session_id, tool_content)
            try:
                response = await self._llm_client.chat(
                    pending.messages, tools=_tool_specs_for_llm(self._tool_registry)
                )
            except Exception as exc:  # pragma: no cover - network/runtime path
                return _output_text(message.session_id, f"LLM error: {exc}")
            return self._finalize_llm_response(message.session_id, response)

        if decision in {"n", "no"}:
            self._pending = None
            return _output_text(message.session_id, "Cancelled tool call.")

        return _output_text(message.session_id, "Confirm with yes/no.")

    async def _handle_llm(self, session_id: str) -> OutputText:
        if self._llm_client is None:
            return _output_text(session_id, "LLM not configured.")
        messages = self._build_messages(session_id)
        tools = _tool_specs_for_llm(self._tool_registry)

        for _ in range(self._max_tool_steps):
            try:
                response = await self._llm_client.chat(messages, tools=tools)
            except Exception as exc:  # pragma: no cover - network/runtime path
                return _output_text(session_id, f"LLM error: {exc}")
            if not response.tool_calls:
                return self._finalize_llm_response(session_id, response)

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": response.raw_tool_calls,
                }
            )
            if response.content:
                self._state_store.add_message(session_id, "assistant", response.content)

            for call in response.tool_calls:
                tool_call = _build_tool_call(session_id, call, self._tool_registry)
                try:
                    result = await self._tool_gateway.execute(tool_call)
                except ConfirmationRequired as exc:
                    self._pending = PendingToolCall(
                        session_id=session_id,
                        tool_call=tool_call,
                        llm_tool_call_id=call.id,
                        messages=list(messages),
                    )
                    return _output_text(
                        session_id,
                        f"Confirm tool call {exc.tool_name}? (yes/no)",
                    )

                tool_content = json.dumps(
                    result.result
                    if result.result is not None
                    else {"error": result.error}
                )
                self._state_store.add_message(session_id, "tool", tool_content)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": tool_content,
                    }
                )

        return _output_text(session_id, "Tool loop exceeded max steps.")

    def _finalize_llm_response(
        self, session_id: str, response: LLMResponse
    ) -> OutputText:
        content = response.content or "No response."
        self._state_store.add_message(session_id, "assistant", content)
        return _output_text(session_id, content)

    def _build_messages(self, session_id: str) -> list[dict[str, Any]]:
        history = self._state_store.list_messages(session_id)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": f"{self._system_prompt}\n\n{self._tool_prompt}",
            }
        ]
        for item in history[-40:]:
            messages.append({"role": item.role, "content": item.content})
        return messages


def _load_prompt(name: str) -> str:
    base = Path(__file__).resolve().parent / "prompts" / name
    if base.exists():
        return base.read_text(encoding="utf-8").strip()
    return ""


def _output_text(session_id: str, text: str) -> OutputText:
    return OutputText(
        session_id=session_id,
        message_id=new_message_id(),
        ts=now_ts(),
        text=text,
    )


def _build_tool_call(session_id: str, call: Any, registry: ToolRegistry) -> ToolCall:
    spec = registry.get(call.name)
    requires_confirm = spec.risk_level is not RiskLevel.SAFE
    return ToolCall(
        session_id=session_id,
        call_id=new_call_id(),
        tool=call.name,
        args=call.arguments,
        requires_confirm=requires_confirm,
    )


def _tool_specs_for_llm(registry: ToolRegistry) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.args_schema,
            },
        }
        for spec in registry.list_specs()
    ]


def wire_runtime(bus: EventBus, runtime: AgentRuntime) -> None:
    async def on_input(message: object) -> None:
        if not isinstance(message, InputText):
            return
        try:
            output = await runtime.handle_input_text(message)
        except Exception as exc:  # pragma: no cover - safety net for runtime errors
            output = _output_text(message.session_id, f"Runtime error: {exc}")
        await bus.publish(topics.OUTPUT_TEXT, output)

    bus.subscribe(topics.INPUT_TEXT, on_input)
