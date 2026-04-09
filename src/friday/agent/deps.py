"""Agent dependencies — shared by core, router, and tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from friday.agent.context import WorkspaceContext
from friday.agent.run_stats import TurnStats
from friday.infra.config import FridaySettings


@dataclass(slots=True)
class AgentDeps:
    """Dependencies injected into every tool call via RunContext."""

    workspace_root: Path
    context: WorkspaceContext
    settings: FridaySettings
    turn_stats: TurnStats = field(default_factory=TurnStats)
