"""MCP client integration."""

from __future__ import annotations

import contextlib
import logging
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamable_http_client
from mcp.shared._httpx_utils import create_mcp_http_client

from friday.mcp.config import MCPConfig, MCPServerConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MCPTool:
    name: str
    server_name: str
    server_tool_name: str
    description: str | None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    risk_level: str


class MCPClient:
    def __init__(self, config: MCPConfig) -> None:
        self._config = config
        self._exit_stack: contextlib.AsyncExitStack | None = None
        self._sessions: dict[str, ClientSession] = {}
        self._tools: dict[str, MCPTool] = {}

    async def connect(self) -> None:
        if self._exit_stack is not None:
            return
        self._exit_stack = contextlib.AsyncExitStack()
        await self._exit_stack.__aenter__()

        for server in self._config.servers:
            try:
                session = await self._connect_server(server)
            except Exception:
                logger.exception("Failed to connect to MCP server %s", server.name)
                continue
            self._sessions[server.name] = session
            await self._register_tools(server, session)

    async def close(self) -> None:
        if self._exit_stack is None:
            return
        await self._exit_stack.aclose()
        self._exit_stack = None
        self._sessions.clear()
        self._tools.clear()

    def list_tools(self) -> list[MCPTool]:
        return list(self._tools.values())

    async def call_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown MCP tool: {name}")
        session = self._sessions.get(tool.server_name)
        if session is None:
            raise RuntimeError("MCP session not connected")

        result = await session.call_tool(tool.server_tool_name, arguments=args)
        if result.isError:
            return {"ok": False, "content": _content_to_text(result.content)}
        if result.structuredContent is not None:
            return result.structuredContent
        return {"ok": True, "content": _content_to_text(result.content)}

    async def _connect_server(self, server: MCPServerConfig) -> ClientSession:
        if self._exit_stack is None:
            raise RuntimeError("MCP client is not initialized")

        if server.transport == "stdio":
            if not server.command:
                raise ValueError("MCP stdio server requires command")
            params = StdioServerParameters(
                command=server.command,
                args=server.args,
                env=server.env,
                cwd=server.cwd,
            )
            read, write = await self._exit_stack.enter_async_context(
                mcp_stdin_client(params)
            )
        elif server.transport == "sse":
            if not server.url:
                raise ValueError("MCP sse server requires url")
            read, write = await self._exit_stack.enter_async_context(
                sse_client(
                    url=server.url,
                    headers=server.headers,
                )
            )
        elif server.transport == "http":
            if not server.url:
                raise ValueError("MCP http server requires url")
            httpx_client = create_mcp_http_client(headers=server.headers)
            await self._exit_stack.enter_async_context(httpx_client)
            read, write, _ = await self._exit_stack.enter_async_context(
                streamable_http_client(
                    url=server.url,
                    http_client=httpx_client,
                    terminate_on_close=True,
                )
            )
        else:
            raise ValueError(f"Unsupported MCP transport: {server.transport}")

        session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        return session

    async def _register_tools(
        self, server: MCPServerConfig, session: ClientSession
    ) -> None:
        tools_result = await session.list_tools()
        for tool in tools_result.tools:
            if not _is_allowed(server, tool.name):
                continue
            tool_name = f"mcp.{server.name}.{tool.name}"
            risk_level = server.risk_overrides.get(tool.name, "safe")
            self._tools[tool_name] = MCPTool(
                name=tool_name,
                server_name=server.name,
                server_tool_name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
                output_schema=tool.outputSchema,
                risk_level=risk_level,
            )


@contextlib.asynccontextmanager
async def mcp_stdin_client(params: StdioServerParameters):
    async with mcp_stdio_client(params) as (read, write):
        yield read, write


def _is_allowed(server: MCPServerConfig, tool_name: str) -> bool:
    if server.allow_tools:
        return tool_name in server.allow_tools
    return server.trusted


def _content_to_text(content: list[Any]) -> str:
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict):
            if block.get("type") == "text" and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
            continue
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
        else:
            parts.append(str(block))
    return "\n".join(part.strip() for part in parts if part)


def _get_mcp_stdio_client():
    try:
        from mcp import stdio_client
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("mcp stdio client unavailable") from exc
    return stdio_client


mcp_stdio_client = _get_mcp_stdio_client()
