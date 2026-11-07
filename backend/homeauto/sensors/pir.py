from homeauto.base import DigitalSensor


class PIRSensor(DigitalSensor):
    """HC-SR501 PIR motion sensor.

    Wiring: VCC -> 5V (needs 5V supply; its output is 3.3V so GPIO-safe),
    GND -> GND, OUT -> GPIO. Output is HIGH on motion.

    Notes: it needs ~30-60 s to calibrate after power-up (spurious triggers
    are normal). Hold time and sensitivity are set with the two orange pots
    and the retrigger jumper on the board, not in software.
    """

    kind = "motion"
    active_state = True
    bounce_time = None  # the module already holds its output for seconds

    @property
    def motion_detected(self) -> bool:
        return self.is_active
