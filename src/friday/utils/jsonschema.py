"""JSON Schema validation helpers."""

from __future__ import annotations

from typing import Any


def validate_jsonschema(schema: dict[str, Any], data: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("jsonschema is required for tool validation") from exc

    validate(instance=data, schema=schema)
