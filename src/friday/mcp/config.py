"""MCP configuration loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Transport = Literal["stdio", "sse", "http"]


@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    transport: Transport = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None
    cwd: str | None = None
    url: str | None = None
    headers: dict[str, str] | None = None
    trusted: bool = False
    allow_tools: list[str] = field(default_factory=list)
    risk_overrides: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MCPConfig:
    servers: list[MCPServerConfig]


def load_mcp_config(path: Path) -> MCPConfig:
    if not path.exists():
        return MCPConfig(servers=[])
    raw = json.loads(path.read_text(encoding="utf-8"))
    servers = []
    for server in raw.get("servers", []):
        transport = server.get("transport")
        command = server.get("command")
        url = server.get("url")
        if transport is None:
            if command:
                transport = "stdio"
            elif url:
                transport = "sse"
            else:
                transport = "stdio"
        servers.append(
            MCPServerConfig(
                name=server["name"],
                transport=transport,
                command=command,
                args=server.get("args", []),
                env=server.get("env"),
                cwd=server.get("cwd"),
                url=url,
                headers=server.get("headers"),
                trusted=server.get("trusted", False),
                allow_tools=server.get("allow_tools", []),
                risk_overrides=server.get("risk_overrides", {}),
            )
        )
    return MCPConfig(servers=servers)
