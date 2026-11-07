"""Single place that defines which BCM GPIO pin each device is wired to.

Pins avoid I2C (2, 3), SPI (7-11) and UART (14, 15) so those buses stay free.
Change them here to match your wiring; nothing else needs to be touched.
"""

DEFAULT_PINS: dict[str, int] = {
    "pir": 17,
    "sound": 27,
    "flame": 22,
    "ir_obstacle": 23,
    "rain": 24,
    "vibration": 25,
}

# BCM GPIO number -> physical header pin (40-pin header, Pi 5 uses the same layout).
BCM_TO_PHYSICAL: dict[int, int] = {
    2: 3, 3: 5, 4: 7, 14: 8, 15: 10, 17: 11, 18: 12, 27: 13, 22: 15, 23: 16,
    24: 18, 10: 19, 9: 21, 25: 22, 11: 23, 8: 24, 7: 26, 0: 27, 1: 28, 5: 29,
    6: 31, 12: 32, 13: 33, 19: 35, 16: 36, 26: 37, 20: 38, 21: 40,
}

# Fixed power pins used by the wiring.
POWER_PINS = {"3V3": 1, "5V": 2, "GND": 6}
