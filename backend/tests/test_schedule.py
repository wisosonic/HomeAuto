import time

from test_api import session

HOUR = 3600


def rule(c, start, end, sensors=("pir", "rain"), name="Night watch"):
    return c.post("/api/schedules", json={"name": name, "sensors": list(sensors), "start": start, "end": end})


def enabled(c):
    return {s["name"]: s["enabled"] for s in c.get("/api/sensors").json()}


def test_sensors_enabled_during_window_then_back_to_initial_state():
    with session() as c:
        c.put("/api/sensors/pir/enabled", json={"enabled": False})  # initial: pir off, rain on, flame off
        c.put("/api/sensors/flame/enabled", json={"enabled": False})
        now = time.time()
        r = rule(c, now + 600, now + 2 * HOUR, sensors=("pir", "rain"))
        assert r.status_code == 201 and r.json()["status"] == "upcoming"
        assert enabled(c)["pir"] is False  # not started yet

        c.app.state.reconcile(now + HOUR)  # inside the window
        assert enabled(c)["pir"] is True and enabled(c)["flame"] is False  # only the selected sensor

        c.app.state.reconcile(now + 3 * HOUR)  # after the end
        e = enabled(c)
        assert (e["pir"], e["rain"], e["flame"]) == (False, True, False)  # exactly the initial states


def test_rule_that_is_already_open_applies_immediately_and_delete_releases_it():
    with session() as c:
        c.put("/api/sensors/pir/enabled", json={"enabled": False})
        now = time.time()
        rid = rule(c, now - 60, now + HOUR, sensors=("pir",)).json()["id"]
        assert enabled(c)["pir"] is True
        assert c.get("/api/schedules").json()[0]["status"] == "active"
        assert c.delete(f"/api/schedules/{rid}").status_code == 200
        assert enabled(c)["pir"] is False


def test_cannot_disable_a_sensor_held_by_a_rule_but_can_after_it_ends():
    with session() as c:
        c.put("/api/sensors/pir/enabled", json={"enabled": False})
        now = time.time()
        rule(c, now - 60, now + HOUR, sensors=("pir",))
        resp = c.put("/api/sensors/pir/enabled", json={"enabled": False})
        assert resp.status_code == 409 and "Night watch" in resp.json()["detail"]
        assert c.put("/api/sensors/rain/enabled", json={"enabled": False}).status_code == 200  # not held


def test_overlapping_rules_hold_until_the_last_one_ends():
    with session() as c:
        c.put("/api/sensors/pir/enabled", json={"enabled": False})
        now = time.time()
        rule(c, now - 60, now + HOUR, sensors=("pir",), name="a")
        rule(c, now - 60, now + 3 * HOUR, sensors=("pir",), name="b")
        c.app.state.reconcile(now + 2 * HOUR)
        assert enabled(c)["pir"] is True  # rule a ended, b still open
        c.app.state.reconcile(now + 4 * HOUR)
        assert enabled(c)["pir"] is False


def test_validation():
    with session() as c:
        now = time.time()
        assert rule(c, now + HOUR, now).status_code == 422  # end before start
        assert rule(c, now - 2 * HOUR, now - HOUR).status_code == 422  # already over
        assert rule(c, now, now + HOUR, sensors=()).status_code == 422  # no sensors
        assert rule(c, now, now + HOUR, sensors=("nope",)).status_code == 422
        assert rule(c, now, now + HOUR, name="  ").status_code == 422
        assert c.put("/api/schedules/99", json={"name": "x", "sensors": ["pir"], "start": now, "end": now + 5}).status_code == 404


def test_update_rule_and_viewer_cannot_manage():
    with session() as c:
        now = time.time()
        rid = rule(c, now + HOUR, now + 2 * HOUR, sensors=("pir",)).json()["id"]
        body = {"name": "Renamed", "sensors": ["flame"], "start": now + HOUR, "end": now + 3 * HOUR}
        r = c.put(f"/api/schedules/{rid}", json=body).json()
        assert r["name"] == "Renamed" and r["sensors"] == ["flame"]

        c.post("/api/users", json={"username": "vera", "password": "viewer-pass-1", "role": "viewer"})
        tok = c.post("/api/auth/login", json={"username": "vera", "password": "viewer-pass-1"}).json()["token"]
        h = {"Authorization": f"Bearer {tok}"}
        assert c.get("/api/schedules", headers=h).status_code == 200
        assert c.post("/api/schedules", headers=h, json=body).status_code == 403
        assert c.delete(f"/api/schedules/{rid}", headers=h).status_code == 403
