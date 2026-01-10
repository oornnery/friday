"""Tool registry and specifications."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from friday.core.policy import RiskLevel
from friday.core.settings import Settings
from friday.mcp.client import MCPClient
from friday.storage.db import db_path
from friday.tools.local import fs_ops, notes, screenshot, tasks, web_search

ToolHandler = Callable[..., Awaitable[object]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    args_schema: dict[str, object]
    risk_level: RiskLevel
    timeout_ms: int
    caps: set[str] = field(default_factory=set)


class ToolRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, spec: ToolSpec, handler: ToolHandler) -> None:
        if spec.name in self._specs:
            raise ValueError(f"Tool already registered: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler

    def get(self, name: str) -> ToolSpec:
        if name not in self._specs:
            raise KeyError(f"Tool not registered: {name}")
        return self._specs[name]

    def handler(self, name: str) -> ToolHandler:
        if name not in self._handlers:
            raise KeyError(f"Handler not registered: {name}")
        return self._handlers[name]

    def list_specs(self) -> list[ToolSpec]:
        return list(self._specs.values())


def register_mcp_tools(registry: ToolRegistry, client: MCPClient) -> None:
    for tool in client.list_tools():
        risk_level = _parse_risk(tool.risk_level)
        tool_name = tool.name

        async def _handler(tool_name=tool_name, **kwargs):
            return await client.call_tool(tool_name, kwargs)

        registry.register(
            ToolSpec(
                name=tool.name,
                description=tool.description or "MCP tool",
                args_schema=tool.input_schema,
                risk_level=risk_level,
                timeout_ms=15_000,
                caps={"mcp"},
            ),
            _handler,
        )


def _parse_risk(value: str) -> RiskLevel:
    normalized = value.strip().lower()
    if normalized == "safe":
        return RiskLevel.SAFE
    if normalized == "confirm":
        return RiskLevel.CONFIRM
    if normalized == "dangerous":
        return RiskLevel.DANGEROUS
    return RiskLevel.SAFE


def register_local_tools(registry: ToolRegistry, settings: Settings) -> None:
    provider = web_search.build_provider(settings)
    store_path = db_path(settings)
    notes_service = notes.NotesService(store_path)
    tasks_service = tasks.TasksService(store_path)
    screenshot_service = screenshot.ScreenshotService(
        db_path=store_path,
        artifacts_dir=settings.data_dir / "artifacts",
        openrouter_api_key=settings.openrouter_api_key,
        openrouter_base_url=settings.openrouter_base_url,
        openrouter_vision_model=settings.openrouter_vision_model,
        openrouter_timeout_s=settings.openrouter_timeout_s,
    )

    async def fs_read(path: str) -> str:
        return await asyncio.to_thread(fs_ops.read_text, settings.workspace_path, path)

    async def fs_write(path: str, content: str) -> dict[str, str]:
        await asyncio.to_thread(
            fs_ops.write_text, settings.workspace_path, path, content
        )
        return {"ok": "true"}

    async def web_search_query(query: str) -> list[dict[str, str]]:
        return await provider.search(query)

    async def notes_append(title: str, content: str) -> str:
        return await asyncio.to_thread(notes_service.append, title, content)

    async def notes_search(query: str) -> list[dict[str, str]]:
        return await asyncio.to_thread(notes_service.search, query)

    async def tasks_create(
        title: str, schedule: str, payload: dict | None = None
    ) -> str:
        return await asyncio.to_thread(tasks_service.create, title, schedule, payload)

    async def tasks_run(task_id: str) -> dict[str, str]:
        return await asyncio.to_thread(tasks_service.run, task_id)

    async def tasks_search(query: str) -> list[dict[str, str]]:
        return await asyncio.to_thread(tasks_service.search, query)

    async def screenshot_capture() -> str:
        return await asyncio.to_thread(screenshot_service.capture)

    async def screenshot_describe(file_path: str) -> str:
        return await screenshot_service.describe(file_path)

    registry.register(
        ToolSpec(
            name="web.search",
            description="Search the web for a query",
            args_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=10_000,
            caps={"net"},
        ),
        web_search_query,
    )
    registry.register(
        ToolSpec(
            name="fs.read",
            description="Read a text file from the workspace",
            args_schema={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=2_000,
            caps={"fs_read"},
        ),
        fs_read,
    )
    registry.register(
        ToolSpec(
            name="fs.write",
            description="Write a text file to the workspace",
            args_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            risk_level=RiskLevel.CONFIRM,
            timeout_ms=2_000,
            caps={"fs_write"},
        ),
        fs_write,
    )
    registry.register(
        ToolSpec(
            name="notes.append",
            description="Append a note",
            args_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=2_000,
            caps={"notes"},
        ),
        notes_append,
    )
    registry.register(
        ToolSpec(
            name="notes.search",
            description="Search notes",
            args_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=2_000,
            caps={"notes"},
        ),
        notes_search,
    )
    registry.register(
        ToolSpec(
            name="tasks.create",
            description="Create a task",
            args_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "schedule": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["title", "schedule"],
            },
            risk_level=RiskLevel.CONFIRM,
            timeout_ms=2_000,
            caps={"tasks"},
        ),
        tasks_create,
    )
    registry.register(
        ToolSpec(
            name="tasks.search",
            description="Search tasks",
            args_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=2_000,
            caps={"tasks"},
        ),
        tasks_search,
    )
    registry.register(
        ToolSpec(
            name="tasks.run",
            description="Run a task by id",
            args_schema={
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=10_000,
            caps={"tasks"},
        ),
        tasks_run,
    )
    registry.register(
        ToolSpec(
            name="screenshot.capture",
            description="Capture a screenshot",
            args_schema={"type": "object", "properties": {}, "required": []},
            risk_level=RiskLevel.CONFIRM,
            timeout_ms=5_000,
            caps={"screenshot"},
        ),
        screenshot_capture,
    )
    registry.register(
        ToolSpec(
            name="screenshot.describe",
            description="Describe a screenshot",
            args_schema={
                "type": "object",
                "properties": {"file_path": {"type": "string"}},
                "required": ["file_path"],
            },
            risk_level=RiskLevel.SAFE,
            timeout_ms=5_000,
            caps={"screenshot"},
        ),
        screenshot_describe,
    )
