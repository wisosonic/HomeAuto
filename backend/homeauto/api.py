"""FastAPI app.

REST:
  GET  /api/info                    {"mock": bool}
  GET  /api/sensors                 all sensor snapshots
  GET  /api/sensors/{name}          one snapshot
  GET  /api/events?limit=&sensor=   recent history (newest first)
  POST /api/sensors/{name}/simulate mock mode only: {"active": true|false}
WebSocket:
  /ws   first message {"type":"snapshot","sensors":[...]}, then
        {"type":"event", ...} per sensor change.

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


class SimulateBody(BaseModel):
    active: bool


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
            s.add_listener(hub.publish_threadsafe)

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

    @app.get("/api/sensors")
    def list_sensors():
        return [s.snapshot() for s in app.state.sensors.values()]

    @app.get("/api/sensors/{name}")
    def read_sensor(name: str):
        return get_sensor(name).snapshot()

    @app.get("/api/events")
    def events(limit: int = Query(50, ge=1, le=500), sensor: str | None = None):
        return app.state.store.recent(limit, sensor)

    @app.post("/api/sensors/{name}/simulate")
    def simulate(name: str, body: SimulateBody):
        if not app.state.mock:
            raise HTTPException(403, "simulate is only available in mock mode")
        s = get_sensor(name)
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
                    ev = await q.get()
                    await websocket.send_json({"type": "event", **ev.to_dict()})
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
