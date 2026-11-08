"""FastAPI app.

REST (everything except /api/info and /api/auth/login needs `Authorization: Bearer <token>`;
the permission in brackets is required):
  GET  /api/info                    {"mock": bool}                      (public)
  POST /api/auth/login              {"username","password"} -> {"token","expires_at","user"}
  POST /api/auth/logout             end this session
  GET  /api/auth/me                 current user + permissions
  POST /api/auth/password           {"current_password","new_password"}
  GET/POST /api/users, PATCH/DELETE /api/users/{username}     [users.manage]
  GET  /api/roles, /api/permissions                           [users.manage or roles.manage]
  POST /api/roles, PUT/DELETE /api/roles/{name}               [roles.manage]
  GET  /api/wiring[?enabled_only=]  pin map + breadboard layout       [wiring.view]
  GET  /api/sensors, /api/sensors/{name}                              [sensors.view]
  GET  /api/events?limit=&sensor=   recent history (newest first)     [events.view]
  DELETE /api/events?sensor=        clear history                     [events.clear]
  PUT  /api/sensors/{name}/enabled  {"enabled": bool}                 [sensors.control]
  POST /api/sensors/{name}/simulate mock mode only                    [sensors.simulate]
WebSocket:
  /ws   the client's first message must be {"type":"auth","token":"..."} (needs sensors.view),
        then the server sends {"type":"snapshot","sensors":[...]}, then
        {"type":"event", ...} (only with events.view), {"type":"sensor_state","sensor":{...}},
        {"type":"events_cleared","sensor":null|name}.
        The token goes in a message, not the URL, so it never lands in access logs.

Run on the Pi:      uvicorn homeauto.api:app --host 0.0.0.0
Run without a Pi:   HOMEAUTO_MOCK=1 uvicorn homeauto.api:app --reload
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from gpiozero import Device
from pydantic import BaseModel

from homeauto.auth import PERMISSIONS, AuthError, AuthStore
from homeauto.hub import EventHub
from homeauto.pinmap import DEFAULT_PINS
from homeauto.sensors import SENSOR_TYPES, create_sensors
from homeauto.store import EventStore
from homeauto.wiring import build_wiring


class SimulateBody(BaseModel):
    active: bool


class EnabledBody(BaseModel):
    enabled: bool


class LoginBody(BaseModel):
    username: str
    password: str


class PasswordBody(BaseModel):
    current_password: str
    new_password: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str


class UserUpdate(BaseModel):
    role: str | None = None
    active: bool | None = None
    password: str | None = None  # admin reset


class RoleBody(BaseModel):
    permissions: list[str]


class RoleCreate(RoleBody):
    name: str


log = logging.getLogger("homeauto")
bearer = HTTPBearer(auto_error=False)


def create_app(
    *, mock: bool | None = None, db_path: str | None = None, admin_password: str | None = None
) -> FastAPI:
    mock = os.environ.get("HOMEAUTO_MOCK") == "1" if mock is None else mock
    db_path = db_path or os.environ.get("HOMEAUTO_DB", "homeauto.db")
    admin_password = admin_password or os.environ.get("HOMEAUTO_ADMIN_PASSWORD")

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

        auth = AuthStore(db_path)
        created = auth.bootstrap_admin(admin_password)  # first run only
        if created and not admin_password:
            # shown once; there is no other way to read it (only the hash is stored)
            print(f"[auth] first run: created user '{created[0]}' with password '{created[1]}'", flush=True)

        app.state.mock, app.state.store, app.state.hub, app.state.sensors = mock, store, hub, sensors
        app.state.auth = auth
        try:
            yield
        finally:
            for s in sensors.values():
                s.close()
            store.close()
            auth.close()
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

    @app.exception_handler(AuthError)
    async def auth_error(_: Request, exc: AuthError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> dict:
        user = app.state.auth.user_for_token(creds.credentials if creds else None)
        if not user:
            raise HTTPException(401, "not authenticated", headers={"WWW-Authenticate": "Bearer"})
        return user

    def require(*perms: str):
        """Dependency: the user must hold at least one of ``perms``."""
        assert perms and all(p in PERMISSIONS for p in perms), perms

        def dep(user: dict = Depends(current_user)) -> dict:
            if not any(p in user["permissions"] for p in perms):
                raise HTTPException(403, f"missing permission: {' or '.join(perms)}")
            return user

        return dep

    def get_sensor(name: str):
        try:
            return app.state.sensors[name]
        except KeyError:
            raise HTTPException(404, f"unknown sensor {name!r}") from None

    @app.get("/api/info")
    def info():
        return {"mock": app.state.mock}

    @app.get("/api/wiring", dependencies=[Depends(require("wiring.view"))])
    def wiring(enabled_only: bool = False):
        if not enabled_only:
            return build_wiring()
        return build_wiring(only={n for n, s in app.state.sensors.items() if s.enabled})

    @app.get("/api/sensors", dependencies=[Depends(require("sensors.view"))])
    def list_sensors():
        return [s.snapshot() for s in app.state.sensors.values()]

    @app.get("/api/sensors/{name}", dependencies=[Depends(require("sensors.view"))])
    def read_sensor(name: str):
        return get_sensor(name).snapshot()

    @app.get("/api/events", dependencies=[Depends(require("events.view"))])
    def events(limit: int = Query(50, ge=1, le=500), sensor: str | None = None):
        return app.state.store.recent(limit, sensor)

    @app.delete("/api/events", dependencies=[Depends(require("events.clear"))])
    def clear_events(sensor: str | None = None):
        deleted = app.state.store.clear(sensor)
        # the counters are derived from the history, so they reset with it
        for name, s in app.state.sensors.items():
            if sensor is None or name == sensor:
                s.reset_stats()
        app.state.hub.publish_threadsafe({"type": "events_cleared", "sensor": sensor})
        return {"deleted": deleted}

    @app.put("/api/sensors/{name}/enabled", dependencies=[Depends(require("sensors.control"))])
    def set_enabled(name: str, body: EnabledBody):
        s = get_sensor(name)
        (s.enable if body.enabled else s.disable)()
        app.state.store.set_enabled(name, body.enabled)
        snap = s.snapshot()
        app.state.hub.publish_threadsafe({"type": "sensor_state", "sensor": snap})
        return snap

    @app.post("/api/sensors/{name}/simulate", dependencies=[Depends(require("sensors.simulate"))])
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

    # -- auth ----------------------------------------------------------------
    @app.post("/api/auth/login")
    def login(body: LoginBody):
        auth = app.state.auth
        user = auth.authenticate(body.username, body.password)
        token, expires_at = auth.create_session(user["id"])
        return {"token": token, "expires_at": expires_at, "user": user}

    @app.post("/api/auth/logout")
    def logout(creds: HTTPAuthorizationCredentials = Depends(bearer), _: dict = Depends(current_user)):
        app.state.auth.revoke_token(creds.credentials)
        return {"ok": True}

    @app.get("/api/auth/me")
    def me(user: dict = Depends(current_user)):
        return user

    @app.post("/api/auth/password")
    def change_password(
        body: PasswordBody,
        creds: HTTPAuthorizationCredentials = Depends(bearer),
        user: dict = Depends(current_user),
    ):
        app.state.auth.change_password(user["username"], body.current_password, body.new_password, creds.credentials)
        return {"ok": True}

    # -- users and roles -----------------------------------------------------
    @app.get("/api/users", dependencies=[Depends(require("users.manage"))])
    def list_users():
        return app.state.auth.list_users()

    @app.post("/api/users", status_code=201, dependencies=[Depends(require("users.manage"))])
    def create_user(body: UserCreate):
        return app.state.auth.create_user(body.username, body.password, body.role)

    @app.patch("/api/users/{username}", dependencies=[Depends(require("users.manage"))])
    def update_user(username: str, body: UserUpdate):
        return app.state.auth.update_user(username, role=body.role, active=body.active, password=body.password)

    @app.delete("/api/users/{username}")
    def delete_user(username: str, user: dict = Depends(require("users.manage"))):
        if username.strip().lower() == user["username"]:
            raise HTTPException(409, "you cannot delete your own account")
        app.state.auth.delete_user(username)
        return {"ok": True}

    @app.get("/api/permissions", dependencies=[Depends(require("users.manage", "roles.manage"))])
    def list_permissions():
        return [{"name": k, "description": v} for k, v in PERMISSIONS.items()]

    @app.get("/api/roles", dependencies=[Depends(require("users.manage", "roles.manage"))])
    def list_roles():
        return app.state.auth.list_roles()

    @app.post("/api/roles", status_code=201, dependencies=[Depends(require("roles.manage"))])
    def create_role(body: RoleCreate):
        return app.state.auth.create_role(body.name, body.permissions)

    @app.put("/api/roles/{name}", dependencies=[Depends(require("roles.manage"))])
    def update_role(name: str, body: RoleBody):
        return app.state.auth.update_role(name, body.permissions)

    @app.delete("/api/roles/{name}", dependencies=[Depends(require("roles.manage"))])
    def delete_role(name: str):
        app.state.auth.delete_role(name)
        return {"ok": True}

    # -- live feed -----------------------------------------------------------
    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        user = None
        try:  # the first message must authenticate
            msg = await asyncio.wait_for(websocket.receive_json(), timeout=5)
            if isinstance(msg, dict) and msg.get("type") == "auth":
                user = app.state.auth.user_for_token(msg.get("token"))
        except Exception:
            pass
        if not user:
            await websocket.close(code=4401)  # not authenticated
            return
        if "sensors.view" not in user["permissions"]:
            await websocket.close(code=4403)  # authenticated, but the role may not see the feed
            return
        see_events = "events.view" in user["permissions"]
        with app.state.hub.subscribe() as q:
            try:
                await websocket.send_json(
                    {"type": "snapshot", "sensors": [s.snapshot() for s in app.state.sensors.values()]}
                )
                while True:
                    msg = await q.get()
                    if msg.get("type") == "event" and not see_events:
                        continue
                    await websocket.send_json(msg)
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
