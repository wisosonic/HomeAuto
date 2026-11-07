"""Wiring description derived from pinmap.py, for the frontend's Wiring page.

Breadboard layout convention: module i (in pinmap order) plugs its 3 pins into row a,
columns 5i+2, 5i+3, 5i+4 (1-based) as VCC, signal, GND.
"""

from __future__ import annotations

from homeauto.pinmap import BCM_TO_PHYSICAL, DEFAULT_PINS, POWER_PINS
from homeauto.sensors import SENSOR_TYPES

# key -> (display name, VCC source, signal pin label printed on the module)
MODULE_INFO: dict[str, tuple[str, str, str]] = {
    "pir": ("PIR HC-SR501", "5V", "OUT"),
    "sound": ("Sound (LM393)", "3V3", "DO"),
    "flame": ("Flame", "3V3", "DO"),
    "ir_obstacle": ("IR obstacle FC-51", "3V3", "OUT"),
    "rain": ("Rain (MH-RD)", "3V3", "DO"),
    "vibration": ("Vibration", "3V3", "DO"),
}


def build_wiring(pins: dict[str, int] | None = None) -> dict:
    pins = DEFAULT_PINS if pins is None else pins
    modules = []
    for i, (key, gpio) in enumerate(pins.items()):
        label, vcc, signal = MODULE_INFO.get(key, (key, "3V3", "DO"))
        active_high = SENSOR_TYPES[key].active_state
        base = 5 * i
        modules.append(
            {
                "key": key,
                "label": label,
                "kind": SENSOR_TYPES[key].kind,
                "gpio": gpio,
                "physical_pin": BCM_TO_PHYSICAL.get(gpio),
                "vcc": vcc,
                "signal_label": signal,
                "active": "HIGH" if active_high else "LOW",
                "columns": {"vcc": base + 2, "signal": base + 3, "gnd": base + 4},
            }
        )
    return {
        "power": [{"name": n, "physical_pin": p} for n, p in POWER_PINS.items()],
        "modules": modules,
        "columns_total": 5 * len(modules),
    }
