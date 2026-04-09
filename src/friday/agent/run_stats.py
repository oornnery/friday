"""Run statistics helpers — summarize model, token, and cost data per turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic_ai.usage import RunUsage

__all__ = ['TurnStats', 'format_turn_summary', 'record_turn_result']

_COST_KEYS = ('cost_usd', 'total_cost_usd', 'cost', 'total_cost', 'usd')


@dataclass(slots=True)
class TurnStats:
    """Aggregated stats for a single user-visible turn."""

    usage: RunUsage = field(default_factory=RunUsage)
    models: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    cost_known: bool = True
    run_count: int = 0

    def reset(self) -> None:
        """Clear all stats before a new top-level run starts."""
        self.usage = RunUsage()
        self.models.clear()
        self.cost_usd = 0.0
        self.cost_known = True
        self.run_count = 0


def record_turn_result(stats: TurnStats, result: Any, requested_model: str = '') -> None:
    """Accumulate usage, model, and cost data from a pydantic-ai run result."""
    stats.run_count += 1

    usage = getattr(result, 'usage', None)
    if callable(usage):
        stats.usage = stats.usage + usage()

    model = _extract_model_label(result, requested_model)
    if model and model not in stats.models:
        stats.models.append(model)

    cost = _extract_cost_usd(result)
    if cost is None:
        stats.cost_known = False
    else:
        stats.cost_usd += cost


def format_turn_summary(stats: TurnStats) -> str:
    """Build a compact single-line summary for the current turn."""
    model_label = 'models' if len(stats.models) > 1 else 'model'
    models = ', '.join(stats.models) or 'unknown'

    usage = stats.usage
    total_tokens = (
        usage.input_tokens
        + usage.output_tokens
        + usage.cache_write_tokens
        + usage.cache_read_tokens
        + usage.input_audio_tokens
        + usage.cache_audio_read_tokens
    )
    token_parts = [
        f'{total_tokens} total',
        f'{usage.input_tokens} in',
        f'{usage.output_tokens} out',
    ]
    if usage.cache_read_tokens or usage.cache_write_tokens:
        token_parts.append(f'cache {usage.cache_read_tokens} read/{usage.cache_write_tokens} write')

    cost = f'${stats.cost_usd:.6f}' if stats.run_count and stats.cost_known else 'n/d'
    return f'{model_label}: {models}  tokens: {", ".join(token_parts)}  cost: {cost}'


def _extract_model_label(result: Any, requested_model: str) -> str:
    response = _get_response(result)
    model_name = str(getattr(response, 'model_name', '') or '').strip()
    provider_name = str(getattr(response, 'provider_name', '') or '').strip()

    if requested_model:
        _, sep, requested_suffix = requested_model.partition(':')
        if not model_name:
            return requested_model
        if sep and requested_suffix == model_name:
            return requested_model

    if provider_name and model_name:
        return f'{provider_name}:{model_name}'
    return model_name or requested_model


def _extract_cost_usd(result: Any) -> float | None:
    response = _get_response(result)
    for candidate in (
        getattr(response, 'provider_details', None),
        getattr(result, 'metadata', None),
    ):
        cost = _find_cost(candidate)
        if cost is not None:
            return cost
    return None


def _find_cost(value: Any, depth: int = 0) -> float | None:
    if depth > 4:
        return None

    if isinstance(value, dict):
        for key in _COST_KEYS:
            if key in value:
                return _coerce_float(value[key])
        for nested in value.values():
            cost = _find_cost(nested, depth + 1)
            if cost is not None:
                return cost
        return None

    if isinstance(value, list | tuple):
        for nested in value:
            cost = _find_cost(nested, depth + 1)
            if cost is not None:
                return cost

    return None


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _get_response(result: Any) -> Any | None:
    try:
        return result.response
    except Exception:
        return None
