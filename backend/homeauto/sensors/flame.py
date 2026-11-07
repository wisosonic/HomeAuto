from homeauto.base import DigitalSensor


class FlameSensor(DigitalSensor):
    """IR flame sensor module (black IR photodiode + LM393).

    Wiring: VCC -> 3.3V, GND -> GND, DO -> GPIO. DO goes LOW on flame.
    Detects IR in ~760-1100 nm, so sunlight and incandescent bulbs can
    also trigger it; tune with the pot. Not a safety device.
    """

    kind = "flame"
    active_state = False
    bounce_time = 0.1

    @property
    def flame_detected(self) -> bool:
        return self.is_active
