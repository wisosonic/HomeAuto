from homeauto.base import DigitalSensor


class RainSensor(DigitalSensor):
    """Rain/water sensor plate + MH-RD comparator board.

    Wiring: VCC -> 3.3V, GND -> GND, DO -> GPIO (AO unused). DO goes LOW
    when the plate is wet enough to cross the pot threshold.
    Tip: power it only while sampling if you can; the plate corrodes
    under constant voltage.
    """

    kind = "rain"
    active_state = False
    bounce_time = 0.2  # droplets make the output flicker

    @property
    def is_raining(self) -> bool:
        return self.is_active
