from __future__ import annotations

from homeauto.base import DigitalSensor
from homeauto.pinmap import DEFAULT_PINS

from .flame import FlameSensor
from .ir_obstacle import IRObstacleSensor
from .pir import PIRSensor
from .rain import RainSensor
from .sound import SoundSensor
from .vibration import VibrationSensor

#: name -> driver class. The same keys are used in the pin map.
SENSOR_TYPES: dict[str, type[DigitalSensor]] = {
    "pir": PIRSensor,
    "sound": SoundSensor,
    "flame": FlameSensor,
    "ir_obstacle": IRObstacleSensor,
    "rain": RainSensor,
    "vibration": VibrationSensor,
}


def create_sensors(pins: dict[str, int] | None = None) -> dict[str, DigitalSensor]:
    """Instantiate every sensor listed in `pins` (default: pinmap.DEFAULT_PINS)."""
    pins = DEFAULT_PINS if pins is None else pins
    return {name: SENSOR_TYPES[name](pin, name=name) for name, pin in pins.items()}


__all__ = [
    "SENSOR_TYPES",
    "create_sensors",
    "FlameSensor",
    "IRObstacleSensor",
    "PIRSensor",
    "RainSensor",
    "SoundSensor",
    "VibrationSensor",
]
