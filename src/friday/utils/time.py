"""Time helpers."""

from __future__ import annotations

import datetime as dt
import time


def now_ts() -> int:
    return int(time.time())


def utc_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()
