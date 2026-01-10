"""Compose the TUI, runtime, and bus."""

from __future__ import annotations

from friday.app.tui import run_tui
from friday.bus.broker import InMemoryBus
from friday.core.agent_runtime import AgentRuntime, wire_runtime
from friday.core.llm import OpenRouterClient
from friday.core.policy import ToolPolicy
from friday.core.scheduler import TaskScheduler
from friday.core.settings import load_settings
from friday.mcp.client import MCPClient
from friday.mcp.config import load_mcp_config
from friday.storage.db import db_path, initialize_db
from friday.storage.state_store import SQLiteStateStore
from friday.tools.gateway import ToolGateway
from friday.tools.registry import ToolRegistry, register_local_tools, register_mcp_tools


def run_app() -> None:
    settings = load_settings()
    settings.workspace_path.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    initialize_db(settings)
    store_path = db_path(settings)

    bus = InMemoryBus()
    registry = ToolRegistry()
    register_local_tools(registry, settings)
    policy = ToolPolicy()
    gateway = ToolGateway(registry, policy, db_path=store_path)
    state_store = SQLiteStateStore(store_path)
    mcp_client = MCPClient(load_mcp_config(settings.mcp_config_path))
    llm_client = None
    if settings.openrouter_api_key:
        llm_client = OpenRouterClient(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.openrouter_model,
            timeout_s=settings.openrouter_timeout_s,
        )

    runtime = AgentRuntime(state_store, gateway, registry, llm_client=llm_client)
    wire_runtime(bus, runtime)
    scheduler = TaskScheduler(
        db_path=store_path, bus=bus, session_id=settings.session_id
    )
    run_tui(
        settings,
        bus=bus,
        scheduler=scheduler,
        tool_registry=registry,
        tool_gateway=gateway,
        mcp_client=mcp_client,
        register_mcp=register_mcp_tools,
    )
