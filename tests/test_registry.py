from __future__ import annotations

from friday.core.policy import RiskLevel
from friday.tools.registry import ToolRegistry, ToolSpec


async def _handler() -> str:
    return "ok"


def test_tool_registry_registers_handler() -> None:
    registry = ToolRegistry()
    spec = ToolSpec(
        name="demo.tool",
        description="demo",
        args_schema={},
        risk_level=RiskLevel.SAFE,
        timeout_ms=1000,
        caps=set(),
    )
    registry.register(spec, _handler)
    assert registry.get("demo.tool") == spec
    assert registry.handler("demo.tool") is _handler
