"""Fan-out of JSON messages (events, state changes) to WebSocket clients."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import Any, Iterator

Message = dict[str, Any]


class EventHub:
    """Bridges gpiozero's threads to asyncio: `publish_threadsafe` may be called
    from any thread; each subscriber gets its own bounded queue."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._subs: set[asyncio.Queue[Message]] = set()

    def publish_threadsafe(self, msg: Message) -> None:
        self._loop.call_soon_threadsafe(self._publish, msg)

    def _publish(self, msg: Message) -> None:
        for q in self._subs:
            if q.full():  # slow client: drop oldest rather than block sensors
                q.get_nowait()
            q.put_nowait(msg)

    @contextmanager
    def subscribe(self) -> Iterator[asyncio.Queue[Message]]:
        q: asyncio.Queue[Message] = asyncio.Queue(maxsize=100)
        self._subs.add(q)
        try:
            yield q
        finally:
            self._subs.discard(q)
