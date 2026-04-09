"""Tool registry — typed metadata for Friday tools."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Risk = Literal['safe', 'risky']


@dataclass(frozen=True, slots=True)
class ToolMeta:
    """Metadata about a tool for approval gating and mode filtering."""

    name: str
    description: str
    risk: Risk
