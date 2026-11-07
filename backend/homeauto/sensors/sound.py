from homeauto.base import DigitalSensor


class SoundSensor(DigitalSensor):
    """Microphone module with LM393 comparator (red board).

    Wiring: VCC -> 3.3V, GND -> GND, DO -> GPIO (AO unused: Pi has no ADC).
    DO goes LOW while sound exceeds the threshold set with the pot.
    """

    kind = "sound"
    active_state = False
    bounce_time = 0.02

    @property
    def sound_detected(self) -> bool:
        return self.is_active
