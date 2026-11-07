"""FastAPI app.

REST:
  GET  /api/info                    {"mock": bool}
  GET  /api/wiring                  pin map + breadboard layout
  GET  /api/sensors                 all sensor snapshots
  GET  /api/sensors/{name}          one snapshot
  GET  /api/events?limit=&sensor=   recent history (newest first)
  DELETE /api/events?sensor=        clear history (all, or one sensor)
  PUT  /api/sensors/{name}/enabled  {"enabled": bool}: persisted, frees the GPIO pin
  POST /api/sensors/{name}/simulate mock mode only: {"active": true|false}
WebSocket:
  /ws   first message {"type":"snapshot","sensors":[...]}, then
        {"type":"event", ...}, {"type":"sensor_state","sensor":{...}},
        {"type":"events_cleared","sensor":null|name}.

Run on the Pi:      uvicorn homeauto.api:app --host 0.0.0.0
Run without a Pi:   HOMEAUTO_MOCK=1 uvicorn homeauto.api:app --reload
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from gpiozero import Device
from pydantic import BaseModel

from homeauto.hub import EventHub
from homeauto.pinmap import DEFAULT_PINS
from homeauto.sensors import SENSOR_TYPES, create_sensors
from homeauto.store import EventStore
from homeauto.wiring import build_wiring


class SimulateBody(BaseModel):
    active: bool


class EnabledBody(BaseModel):
    enabled: bool


def create_app(*, mock: bool | None = None, db_path: str | None = None) -> FastAPI:
    mock = os.environ.get("HOMEAUTO_MOCK") == "1" if mock is None else mock
    db_path = db_path or os.environ.get("HOMEAUTO_DB", "homeauto.db")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if mock:
            from gpiozero.pins.mock import MockFactory

            Device.pin_factory = MockFactory()
            # Mock pins start LOW; put active-low sensors at their idle (HIGH) level.
            for name, pin in DEFAULT_PINS.items():
                if not SENSOR_TYPES[name].active_state:
                    Device.pin_factory.pin(pin).drive_high()

        store = EventStore(db_path)
        hub = EventHub(asyncio.get_running_loop())
        sensors = create_sensors()
        for s in sensors.values():
            s.add_listener(store.add)
            s.add_listener(lambda ev: hub.publish_threadsafe({"type": "event", **ev.to_dict()}))
        # Detection counts / last event come from the stored history, so they survive restarts
        # and stay consistent with what the event log shows.
        counts, last = store.activation_counts(), store.last_events()
        for name, s in sensors.items():
            s.restore_stats(counts.get(name, 0), last.get(name))
        for name in store.disabled_sensors():  # restore saved on/off settings
            if name in sensors:
                sensors[name].disable()

        app.state.mock, app.state.store, app.state.hub, app.state.sensors = mock, store, hub, sensors
        try:
            yield
        finally:
            for s in sensors.values():
                s.close()
            store.close()
            if mock:
                Device.pin_factory.reset()
                Device.pin_factory = None

    app = FastAPI(title="HomeAuto", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.environ.get("HOMEAUTO_CORS", "http://localhost:5173").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_sensor(name: str):
        try:
            return app.state.sensors[name]
        except KeyError:
            raise HTTPException(404, f"unknown sensor {name!r}") from None

    @app.get("/api/info")
    def info():
        return {"mock": app.state.mock}

    @app.get("/api/wiring")
    def wiring():
        return build_wiring()

    @app.get("/api/sensors")
    def list_sensors():
        return [s.snapshot() for s in app.state.sensors.values()]

    @app.get("/api/sensors/{name}")
    def read_sensor(name: str):
        return get_sensor(name).snapshot()

    @app.get("/api/events")
    def events(limit: int = Query(50, ge=1, le=500), sensor: str | None = None):
        return app.state.store.recent(limit, sensor)

    @app.delete("/api/events")
    def clear_events(sensor: str | None = None):
        deleted = app.state.store.clear(sensor)
        # the counters are derived from the history, so they reset with it
        for name, s in app.state.sensors.items():
            if sensor is None or name == sensor:
                s.reset_stats()
        app.state.hub.publish_threadsafe({"type": "events_cleared", "sensor": sensor})
        return {"deleted": deleted}

    @app.put("/api/sensors/{name}/enabled")
    def set_enabled(name: str, body: EnabledBody):
        s = get_sensor(name)
        (s.enable if body.enabled else s.disable)()
        app.state.store.set_enabled(name, body.enabled)
        snap = s.snapshot()
        app.state.hub.publish_threadsafe({"type": "sensor_state", "sensor": snap})
        return snap

    @app.post("/api/sensors/{name}/simulate")
    def simulate(name: str, body: SimulateBody):
        if not app.state.mock:
            raise HTTPException(403, "simulate is only available in mock mode")
        s = get_sensor(name)
        if not s.enabled:
            raise HTTPException(409, f"sensor {name!r} is disabled")
        pin = Device.pin_factory.pin(s.pin)
        # drive the pin to the level that means active / idle for this sensor
        (pin.drive_high if body.active == s._active_state else pin.drive_low)()
        return s.snapshot()

    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        with app.state.hub.subscribe() as q:
            try:
                await websocket.send_json(
                    {"type": "snapshot", "sensors": [s.snapshot() for s in app.state.sensors.values()]}
                )
                while True:
                    await websocket.send_json(await q.get())
            except WebSocketDisconnect:
                pass

    # Serve the built React app (npm run build) if present, e.g. on the Pi.
    static_dir = os.environ.get("HOMEAUTO_STATIC") or str(
        Path(__file__).resolve().parents[2] / "frontend" / "dist"
    )
    if Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")

    return app


app = create_app()
