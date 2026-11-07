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
