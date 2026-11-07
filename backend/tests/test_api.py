from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from homeauto.api import create_app
from homeauto.pinmap import DEFAULT_PINS

ADMIN_PW = "test-password-1"


@contextmanager
def session(db=":memory:"):
    """A TestClient logged in as the bootstrap admin."""
    with TestClient(create_app(mock=True, db_path=db, admin_password=ADMIN_PW)) as c:
        token = c.post("/api/auth/login", json={"username": "admin", "password": ADMIN_PW}).json()["token"]
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@contextmanager
def ws_connect(c):
    """Open /ws and send the auth message the server requires first."""
    with c.websocket_connect("/ws") as ws:
        ws.send_json({"type": "auth", "token": c.headers["Authorization"].split()[1]})
        yield ws


@pytest.fixture
def client():
    with session() as c:
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
    with ws_connect(client) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        client.post("/api/sensors/flame/simulate", json={"active": True})
        msg = ws.receive_json()
        assert msg["type"] == "event" and msg["sensor"] == "flame" and msg["active"] is True


def test_simulate_forbidden_without_mock(monkeypatch):
    # real mode needs hardware; just check the guard using a mock-created app flipped off
    with session() as c:
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
    with ws_connect(client) as ws:
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
    with ws_connect(client) as ws:
        ws.receive_json()
        client.put("/api/sensors/rain/enabled", json={"enabled": False})
        msg = ws.receive_json()
        assert msg["type"] == "sensor_state" and msg["sensor"]["name"] == "rain"
        assert msg["sensor"]["enabled"] is False


def test_disabled_setting_survives_restart(tmp_path):
    db = str(tmp_path / "h.db")
    with session(db) as c:
        c.put("/api/sensors/sound/enabled", json={"enabled": False})
    with session(db) as c:
        by_name = {s["name"]: s for s in c.get("/api/sensors").json()}
        assert by_name["sound"]["enabled"] is False
        assert by_name["pir"]["enabled"] is True


def test_clear_events_resets_detection_counts(client):
    for name in ("pir", "flame"):
        client.post(f"/api/sensors/{name}/simulate", json={"active": True})
    assert client.get("/api/sensors/pir").json()["detection_count"] == 1
    # clearing one sensor only resets that sensor
    client.delete("/api/events", params={"sensor": "pir"})
    pir, flame = client.get("/api/sensors/pir").json(), client.get("/api/sensors/flame").json()
    assert pir["detection_count"] == 0 and pir["last_event"] is None
    assert flame["detection_count"] == 1 and flame["last_event"] is not None
    # clearing everything resets all
    client.delete("/api/events")
    assert all(s["detection_count"] == 0 and s["last_event"] is None for s in client.get("/api/sensors").json())


def test_counts_restored_from_history_on_restart_and_reset_by_clear(tmp_path):
    db = str(tmp_path / "h.db")
    with session(db) as c:
        for _ in range(2):
            c.post("/api/sensors/pir/simulate", json={"active": True})
            c.post("/api/sensors/pir/simulate", json={"active": False})
    with session(db) as c:
        pir = c.get("/api/sensors/pir").json()
        assert pir["detection_count"] == 2 and pir["last_event"]["active"] is False
        c.delete("/api/events")
    with session(db) as c:
        assert c.get("/api/sensors/pir").json()["detection_count"] == 0
