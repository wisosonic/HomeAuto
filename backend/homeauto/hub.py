"""Fan-out of sensor events to WebSocket clients."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import Iterator

from homeauto.base import SensorEvent


class EventHub:
    """Bridges gpiozero's threads to asyncio: `publish_threadsafe` may be called
    from any thread; each subscriber gets its own bounded queue."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._subs: set[asyncio.Queue[SensorEvent]] = set()

    def publish_threadsafe(self, ev: SensorEvent) -> None:
        self._loop.call_soon_threadsafe(self._publish, ev)

    def _publish(self, ev: SensorEvent) -> None:
        for q in self._subs:
            if q.full():  # slow client: drop oldest rather than block sensors
                q.get_nowait()
            q.put_nowait(ev)

    @contextmanager
    def subscribe(self) -> Iterator[asyncio.Queue[SensorEvent]]:
        q: asyncio.Queue[SensorEvent] = asyncio.Queue(maxsize=100)
        self._subs.add(q)
        try:
            yield q
        finally:
            self._subs.discard(q)
