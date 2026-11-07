from homeauto.base import DigitalSensor


class VibrationSensor(DigitalSensor):
    """Vibration / shock switch module (blue board with metal spring).

    Wiring: VCC -> 3.3V, GND -> GND, DO -> GPIO. These modules normally pull
    DO LOW on a shock. If yours behaves inverted (or it is actually a tilt
    switch/reed), pass `active_state=True`.

    The spring bounces, so one knock produces a burst of edges; the
    debounce window collapses them into one event.
    """

    kind = "vibration"
    active_state = False
    bounce_time = 0.05

    @property
    def vibration_detected(self) -> bool:
        return self.is_active
