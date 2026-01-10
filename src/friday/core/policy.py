"""Policy and permissions for tool execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiskLevel(str, Enum):
    SAFE = "safe"
    CONFIRM = "confirm"
    DANGEROUS = "dangerous"


class Decision(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyDecision:
    decision: Decision
    reason: str


class ToolPolicy:
    def __init__(
        self,
        confirm_tools: set[str] | None = None,
        deny_tools: set[str] | None = None,
    ) -> None:
        self._confirm_tools = confirm_tools or set()
        self._deny_tools = deny_tools or set()

    def evaluate(self, tool_name: str, risk_level: RiskLevel) -> PolicyDecision:
        if tool_name in self._deny_tools:
            return PolicyDecision(Decision.DENY, "Tool is blocked by policy")
        if tool_name in self._confirm_tools:
            return PolicyDecision(Decision.CONFIRM, "Tool requires confirmation")
        if risk_level is RiskLevel.SAFE:
            return PolicyDecision(Decision.ALLOW, "Safe tool")
        if risk_level is RiskLevel.CONFIRM:
            return PolicyDecision(Decision.CONFIRM, "Tool requires confirmation")
        return PolicyDecision(Decision.DENY, "Tool is dangerous by default")
