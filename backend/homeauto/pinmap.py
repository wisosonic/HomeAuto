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
