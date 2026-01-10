"""Schedule parsing and next-run calculation."""

from __future__ import annotations

from datetime import UTC, datetime

from dateutil import rrule


def next_run_ts(schedule: str, after_ts: int) -> int | None:
    schedule = schedule.strip()
    if schedule.upper().startswith("RRULE:"):
        rule = rrule.rrulestr(schedule, dtstart=_utc_from_ts(after_ts))
        next_dt = rule.after(_utc_from_ts(after_ts), inc=False)
        return int(next_dt.timestamp()) if next_dt else None

    try:
        dt_value = datetime.fromisoformat(schedule)
    except ValueError as exc:
        raise ValueError(f"Invalid schedule format: {schedule}") from exc

    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=UTC)
    if dt_value <= _utc_from_ts(after_ts):
        return None
    return int(dt_value.timestamp())


def _utc_from_ts(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=UTC)
