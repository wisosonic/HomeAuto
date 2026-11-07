import pytest
from fastapi.testclient import TestClient

from homeauto.api import create_app
from homeauto.pinmap import DEFAULT_PINS


@pytest.fixture
def client():
    with TestClient(create_app(mock=True, db_path=":memory:")) as c:
        yield c


def test_list_sensors_all_idle(client):
    data = client.get("/api/sensors").json()
    assert {s["name"] for s in data} == set(DEFAULT_PINS)
    assert not any(s["active"] for s in data)  # incl. active-low ones


def test_unknown_sensor_404(client):
    assert client.get("/api/sensors/nope").status_code == 404
    assert client.post("/api/sensors/nope/simulate", json={"active": True}).status_code == 404


def test_simulate_updates_state_and_history(client):
    for name in ("pir", "rain"):  # active-high and active-low
        snap = client.post(f"/api/sensors/{name}/simulate", json={"active": True}).json()
        assert snap["active"] and snap["detection_count"] == 1
        client.post(f"/api/sensors/{name}/simulate", json={"active": False})
    ev = client.get("/api/events", params={"sensor": "rain"}).json()
    assert [e["active"] for e in ev] == [False, True]  # newest first


def test_websocket_snapshot_then_event(client):
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "snapshot"
        client.post("/api/sensors/flame/simulate", json={"active": True})
        msg = ws.receive_json()
        assert msg["type"] == "event" and msg["sensor"] == "flame" and msg["active"] is True


def test_simulate_forbidden_without_mock(monkeypatch):
    # real mode needs hardware; just check the guard using a mock-created app flipped off
    with TestClient(create_app(mock=True, db_path=":memory:")) as c:
        c.app.state.mock = False
        assert c.post("/api/sensors/pir/simulate", json={"active": True}).status_code == 403


def test_info_reports_mock(client):
    assert client.get("/api/info").json() == {"mock": True}


def test_wiring_matches_pinmap(client):
    w = client.get("/api/wiring").json()
    assert [m["key"] for m in w["modules"]] == list(DEFAULT_PINS)
    pir = w["modules"][0]
    assert (pir["gpio"], pir["physical_pin"], pir["vcc"], pir["active"]) == (17, 11, "5V", "HIGH")
    assert pir["columns"] == {"vcc": 2, "signal": 3, "gnd": 4}
    assert w["modules"][1]["columns"]["vcc"] == 7
    assert {p["name"]: p["physical_pin"] for p in w["power"]} == {"3V3": 1, "5V": 2, "GND": 6}
    assert all(m["physical_pin"] for m in w["modules"])


def test_clear_events_all_and_per_sensor(client):
    for name in ("pir", "flame"):
        client.post(f"/api/sensors/{name}/simulate", json={"active": True})
    assert len(client.get("/api/events").json()) == 2
    assert client.delete("/api/events", params={"sensor": "pir"}).json() == {"deleted": 1}
    assert [e["sensor"] for e in client.get("/api/events").json()] == ["flame"]
    assert client.delete("/api/events").json() == {"deleted": 1}
    assert client.get("/api/events").json() == []


def test_clear_events_broadcasts(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()  # snapshot
        client.delete("/api/events")
        assert ws.receive_json() == {"type": "events_cleared", "sensor": None}


def test_disable_blocks_events_and_simulate(client):
    snap = client.put("/api/sensors/pir/enabled", json={"enabled": False}).json()
    assert snap["enabled"] is False and snap["active"] is False
    assert client.post("/api/sensors/pir/simulate", json={"active": True}).status_code == 409
    assert client.get("/api/events").json() == []
    # other sensors are unaffected
    assert client.post("/api/sensors/flame/simulate", json={"active": True}).json()["active"]
    # re-enable: works again
    assert client.put("/api/sensors/pir/enabled", json={"enabled": True}).json()["enabled"] is True
    assert client.post("/api/sensors/pir/simulate", json={"active": True}).json()["active"]


def test_disable_broadcasts_state(client):
    with client.websocket_connect("/ws") as ws:
        ws.receive_json()
        client.put("/api/sensors/rain/enabled", json={"enabled": False})
        msg = ws.receive_json()
        assert msg["type"] == "sensor_state" and msg["sensor"]["name"] == "rain"
        assert msg["sensor"]["enabled"] is False


def test_disabled_setting_survives_restart(tmp_path):
    db = str(tmp_path / "h.db")
    with TestClient(create_app(mock=True, db_path=db)) as c:
        c.put("/api/sensors/sound/enabled", json={"enabled": False})
    with TestClient(create_app(mock=True, db_path=db)) as c:
        by_name = {s["name"]: s for s in c.get("/api/sensors").json()}
        assert by_name["sound"]["enabled"] is False
        assert by_name["pir"]["enabled"] is True
