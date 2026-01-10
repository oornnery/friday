"""Tool execution with policy and validation."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path

from friday.bus.schemas import ToolCall, ToolResult
from friday.core.policy import Decision, ToolPolicy
from friday.storage.db import connect
from friday.storage.repos import tool_logs as tool_logs_repo
from friday.tools.registry import ToolRegistry
from friday.utils.jsonschema import validate_jsonschema
from friday.utils.redact import redact_json


@dataclass(frozen=True)
class ConfirmationRequired(Exception):
    tool_name: str
    reason: str


class ToolGateway:
    def __init__(
        self, registry: ToolRegistry, policy: ToolPolicy, db_path: Path | None = None
    ) -> None:
        self._registry = registry
        self._policy = policy
        self._db_path = db_path

    async def execute(self, call: ToolCall) -> ToolResult:
        spec = self._registry.get(call.tool)
        decision = self._policy.evaluate(spec.name, spec.risk_level)
        if decision.decision is Decision.DENY:
            return ToolResult(
                call_id=call.call_id,
                ok=False,
                result=None,
                error=decision.reason,
                elapsed_ms=0,
            )
        if decision.decision is Decision.CONFIRM and call.requires_confirm:
            raise ConfirmationRequired(spec.name, decision.reason)

        validate_jsonschema(spec.args_schema, call.args)
        handler = self._registry.handler(spec.name)

        start = time.perf_counter()
        try:
            result = await asyncio.wait_for(
                handler(**call.args), timeout=spec.timeout_ms / 1000
            )
        except Exception as exc:  # pragma: no cover - error path
            tool_result = ToolResult(
                call_id=call.call_id,
                ok=False,
                result=None,
                error=str(exc),
                elapsed_ms=int((time.perf_counter() - start) * 1000),
            )
            await self._log_tool_call(call, tool_result)
            return tool_result

        tool_result = ToolResult(
            call_id=call.call_id,
            ok=True,
            result={"data": result} if result is not None else None,
            error=None,
            elapsed_ms=int((time.perf_counter() - start) * 1000),
        )
        await self._log_tool_call(call, tool_result)
        return tool_result

    async def _log_tool_call(self, call: ToolCall, result: ToolResult) -> None:
        db_path = self._db_path
        if db_path is None:
            return
        await asyncio.to_thread(self._log_tool_call_sync, db_path, call, result)

    def _log_tool_call_sync(
        self, db_path: Path, call: ToolCall, result: ToolResult
    ) -> None:
        with connect(db_path) as conn:
            tool_logs_repo.log_tool_call(
                conn,
                tool_logs_repo.ToolCallLog(
                    call_id=call.call_id,
                    session_id=call.session_id,
                    tool=call.tool,
                    args=redact_json(call.args),
                    result=redact_json(result.result) if result.result else None,
                    ok=result.ok,
                    elapsed_ms=result.elapsed_ms,
                    ts=int(time.time()),
                ),
            )
