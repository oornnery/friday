"""PII redaction helpers."""

from __future__ import annotations

import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
TOKEN_RE = re.compile(r"(?i)(api_key|token|secret)=([A-Za-z0-9_-]+)")


def redact_text(text: str) -> str:
    text = EMAIL_RE.sub("[redacted-email]", text)
    return TOKEN_RE.sub(r"\1=[redacted]", text)


def redact_json(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [redact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_json(item) for key, item in value.items()}
    return value
