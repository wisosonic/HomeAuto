from homeauto.base import DigitalSensor


class IRObstacleSensor(DigitalSensor):
    """IR obstacle avoidance module (FC-51 / HW-201).

    Also works for the 3-pin line-tracking module (detects reflective vs
    dark surface) by giving it a different `name`.

    Wiring: VCC -> 3.3V, GND -> GND, OUT -> GPIO. OUT goes LOW when an
    object reflects the IR beam. Range is set with the pot (~2-30 cm).
    """

    kind = "obstacle"
    active_state = False
    bounce_time = 0.03

    @property
    def obstacle_detected(self) -> bool:
        return self.is_active
