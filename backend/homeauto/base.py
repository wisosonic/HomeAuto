"""Base class shared by all digital (on/off) GPIO sensors.

The cheap Arduino-style modules (PIR, LM393 comparators, ...) expose a digital
output (DO) that is either HIGH or LOW. Whether HIGH or LOW means "detected"
depends on the module, which is what `active_state` captures.

Hardware edges are delivered by gpiozero on a background thread and turned
into `SensorEvent` objects, which is what the API layer consumes.

A sensor can be disabled at runtime: the GPIO pin is released and no events are
produced until it is enabled again.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any, Callable

from gpiozero import DigitalInputDevice

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SensorEvent:
    sensor: str  # instance name, e.g. "pir"
    kind: str  # e.g. "motion"
    active: bool  # True = detection started, False = detection ended
    timestamp: float  # unix time

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


Listener = Callable[[SensorEvent], None]


class DigitalSensor:
    """A digital input sensor with debounce, events and a JSON-friendly snapshot."""

    #: Event category, overridden by subclasses.
    kind: str = "generic"
    #: Pin level meaning "detected". True = HIGH, False = LOW.
    active_state: bool = True
    #: Debounce window in seconds.
    bounce_time: float | None = 0.05

    def __init__(
        self,
        pin: int,
        *,
        name: str | None = None,
        active_state: bool | None = None,
        bounce_time: float | None = None,
    ) -> None:
        self.pin = pin
        self.name = name or type(self).__name__.lower()
        self._lock = threading.Lock()
        self._listeners: list[Listener] = []
        self._count = 0
        self._last_event: SensorEvent | None = None
        self._active_state = self.active_state if active_state is None else active_state
        self._bounce = self.bounce_time if bounce_time is None else bounce_time
        self._device: DigitalInputDevice | None = None
        self._enabled = False
        self.enable()

    # -- enable / disable ------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        """Claim the GPIO pin and start producing events (idempotent)."""
        with self._lock:
            if self._enabled:
                return
            # pull_up=None: the module drives the line itself (no internal pull),
            # which requires an explicit active_state.
            dev = DigitalInputDevice(
                self.pin,
                pull_up=None,
                active_state=self._active_state,
                bounce_time=self._bounce,
            )
            dev.when_activated = lambda: self._emit(True)
            dev.when_deactivated = lambda: self._emit(False)
            self._device = dev
            self._enabled = True

    def disable(self) -> None:
        """Release the GPIO pin and stop producing events (idempotent)."""
        with self._lock:
            if not self._enabled:
                return
            self._enabled = False
            dev, self._device = self._device, None
        if dev is not None:
            dev.when_activated = None
            dev.when_deactivated = None
            dev.close()

    # -- state -----------------------------------------------------------
    @property
    def idle_level(self) -> bool:
        """Pin level (True = HIGH) when nothing is detected."""
        return not self._active_state

    @property
    def is_active(self) -> bool:
        """True while the sensor is currently detecting something."""
        dev = self._device
        return bool(dev.is_active) if dev is not None else False

    @property
    def detection_count(self) -> int:
        """Number of detections (rising activations) since start."""
        return self._count

    @property
    def last_event(self) -> SensorEvent | None:
        return self._last_event

    def reset_stats(self) -> None:
        """Forget the detection count and last event (used when history is cleared)."""
        with self._lock:
            self._count = 0
            self._last_event = None

    def restore_stats(self, count: int, last_event: SensorEvent | None) -> None:
        """Seed the count / last event from stored history (used at startup)."""
        with self._lock:
            self._count = count
            self._last_event = last_event

    def snapshot(self) -> dict[str, Any]:
        """Current state as plain data (for the API layer)."""
        last = self._last_event
        return {
            "name": self.name,
            "kind": self.kind,
            "pin": self.pin,
            "enabled": self._enabled,
            "active": self.is_active,
            "detection_count": self._count,
            "last_event": last.to_dict() if last else None,
        }

    # -- events ----------------------------------------------------------
    def add_listener(self, fn: Listener) -> Listener:
        """Register a callback invoked (on a gpiozero thread) for every event."""
        with self._lock:
            self._listeners.append(fn)
        return fn

    def remove_listener(self, fn: Listener) -> None:
        with self._lock:
            if fn in self._listeners:
                self._listeners.remove(fn)

    def _emit(self, active: bool) -> None:
        if not self._enabled:
            return
        event = SensorEvent(self.name, self.kind, active, time.time())
        with self._lock:
            if active:
                self._count += 1
            self._last_event = event
            listeners = list(self._listeners)
        for fn in listeners:
            try:
                fn(event)
            except Exception:  # a bad listener must not break the others
                log.exception("listener failed for %s", self.name)

    # -- lifecycle -------------------------------------------------------
    def close(self) -> None:
        self.disable()

    def __enter__(self) -> "DigitalSensor":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "off" if not self._enabled else f"active={self.is_active}"
        return f"<{type(self).__name__} {self.name!r} pin={self.pin} {state}>"
