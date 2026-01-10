"""Event bus implementations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from faststream import FastStream

Handler = Callable[[object], Awaitable[None]]


class EventBus(Protocol):
    def subscribe(self, topic: str, handler: Handler) -> None: ...

    async def publish(self, topic: str, message: object) -> None: ...


class InMemoryBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers[topic].append(handler)

    async def publish(self, topic: str, message: object) -> None:
        handlers = list(self._handlers.get(topic, []))
        for handler in handlers:
            await handler(message)


def build_faststream_app(broker_url: str | None) -> FastStream | None:
    if not broker_url:
        return None

    from faststream import FastStream

    try:
        from faststream.redis import RedisBroker
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "FastStream Redis broker is not installed. Add faststream[redis]."
        ) from exc

    broker = RedisBroker(broker_url)
    return FastStream(broker)
