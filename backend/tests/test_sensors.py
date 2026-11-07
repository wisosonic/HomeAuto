"""Hardware-free tests using gpiozero's mock pin factory (runs on any OS)."""

import pytest
from gpiozero import Device
from gpiozero.pins.mock import MockFactory

from homeauto.pinmap import DEFAULT_PINS
from homeauto.sensors import SENSOR_TYPES, PIRSensor, RainSensor, create_sensors


@pytest.fixture(autouse=True)
def mock_pins():
    Device.pin_factory = MockFactory()
    yield
    Device.pin_factory.reset()
    Device.pin_factory = None


def _pin(n):
    return Device.pin_factory.pin(n)


def test_pir_is_active_high():
    with PIRSensor(17) as pir:
        assert not pir.is_active
        _pin(17).drive_high()
        assert pir.motion_detected
        _pin(17).drive_low()
        assert not pir.is_active


def test_rain_is_active_low():
    _pin(24).drive_high()  # module idles HIGH; mock pins start LOW
    with RainSensor(24) as rain:
        assert not rain.is_raining
        _pin(24).drive_low()
        assert rain.is_raining


def test_events_and_count():
    events = []
    with PIRSensor(17, name="hall") as pir:
        pir.add_listener(events.append)
        _pin(17).drive_high()
        _pin(17).drive_low()
        _pin(17).drive_high()
    assert [e.active for e in events] == [True, False, True]
    assert events[0].sensor == "hall" and events[0].kind == "motion"
    assert pir.detection_count == 2


def test_bad_listener_does_not_break_others():
    seen = []
    with PIRSensor(17) as pir:
        pir.add_listener(lambda e: 1 / 0)
        pir.add_listener(seen.append)
        _pin(17).drive_high()
    assert len(seen) == 1


def test_snapshot_is_json_friendly():
    import json

    with PIRSensor(17) as pir:
        _pin(17).drive_high()
        data = pir.snapshot()
    json.dumps(data)
    assert data["active"] is True and data["pin"] == 17 and data["last_event"]["active"]


def test_create_all_default_sensors():
    sensors = create_sensors()
    try:
        assert set(sensors) == set(SENSOR_TYPES) == set(DEFAULT_PINS)
    finally:
        for s in sensors.values():
            s.close()


def test_disable_releases_pin_and_ignores_edges_then_reenables():
    events = []
    pir = PIRSensor(17)
    pir.add_listener(events.append)
    pir.disable()
    assert not pir.enabled and not pir.is_active
    _pin(17).drive_high()  # edge while disabled: nobody is listening
    assert events == [] and pir.detection_count == 0
    PIRSensor(17).close()  # pin was released, so it can be claimed again
    pir.enable()
    assert pir.enabled and pir.motion_detected  # reads the live level on re-enable
    _pin(17).drive_low()
    _pin(17).drive_high()
    assert [e.active for e in events] == [False, True]
    pir.close()
