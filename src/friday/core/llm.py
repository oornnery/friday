"""LLM client integrations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class LLMToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    content: str | None
    tool_calls: list[LLMToolCall]
    raw_tool_calls: list[dict[str, Any]]


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0.2,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        url = f"{self._base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=self._timeout_s) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        return _parse_openrouter_response(data)


def _parse_openrouter_response(payload: dict[str, Any]) -> LLMResponse:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return LLMResponse(content=None, tool_calls=[], raw_tool_calls=[])
    message = choices[0].get("message", {})
    content = message.get("content") if isinstance(message, dict) else None
    content = content.strip() if isinstance(content, str) else None

    raw_tool_calls = []
    tool_calls: list[LLMToolCall] = []
    if isinstance(message, dict):
        raw_tool_calls = message.get("tool_calls") or []

    if isinstance(raw_tool_calls, list):
        for call in raw_tool_calls:
            if not isinstance(call, dict):
                continue
            call_id = str(call.get("id", ""))
            function = call.get("function") or {}
            if not isinstance(function, dict):
                continue
            name = str(function.get("name", ""))
            arguments_raw = function.get("arguments")
            if not name or not isinstance(arguments_raw, str):
                continue
            try:
                arguments = json.loads(arguments_raw)
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append(LLMToolCall(id=call_id, name=name, arguments=arguments))

    return LLMResponse(
        content=content,
        tool_calls=tool_calls,
        raw_tool_calls=raw_tool_calls if isinstance(raw_tool_calls, list) else [],
    )
