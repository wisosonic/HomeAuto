import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from homeauto.api import create_app
from homeauto.auth import PERMISSIONS, AuthError, AuthStore, hash_password, verify_password
from test_api import ADMIN_PW, session, ws_connect


def login(c, username, password):
    return c.post("/api/auth/login", json={"username": username, "password": password})


def as_user(c, username, password):
    """A second client on the same app, logged in as another user."""
    other = TestClient(c.app)
    r = login(other, username, password)
    assert r.status_code == 200, r.text
    other.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return other


@pytest.fixture
def client():
    with session() as c:
        yield c


def make_user(c, username, role, password="password-123"):
    assert c.post("/api/users", json={"username": username, "password": password, "role": role}).status_code == 201
    return as_user(c, username, password)


# -- passwords ---------------------------------------------------------------
def test_password_hash_roundtrip():
    h = hash_password("correct horse")
    assert "correct horse" not in h
    assert verify_password("correct horse", h)
    assert not verify_password("wrong", h)
    assert not verify_password("x", "garbage")
    assert hash_password("a-password") != hash_password("a-password")  # salted


# -- login / sessions --------------------------------------------------------
def test_endpoints_require_login(client):
    anon = TestClient(client.app)
    for method, path in [
        ("get", "/api/sensors"), ("get", "/api/events"), ("get", "/api/wiring"), ("get", "/api/users"),
        ("get", "/api/auth/me"), ("delete", "/api/events"), ("post", "/api/auth/logout"),
    ]:
        assert getattr(anon, method)(path).status_code == 401, path
    assert anon.get("/api/info").status_code == 200  # public


def test_bad_token_rejected(client):
    r = TestClient(client.app).get("/api/sensors", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


def test_login_logout(client):
    me = client.get("/api/auth/me").json()
    assert me["username"] == "admin" and me["role"] == "admin"
    assert set(me["permissions"]) == set(PERMISSIONS)
    assert "password" not in str(me)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401  # token is dead


def test_wrong_password_and_unknown_user_look_the_same(client):
    a = login(client, "admin", "wrong-password")
    b = login(client, "nobody", "wrong-password")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_lockout_after_repeated_failures(client):
    for _ in range(5):
        assert login(client, "admin", "bad-password").status_code == 401
    assert login(client, "admin", ADMIN_PW).status_code == 429  # even the right password, while locked


def test_username_is_case_insensitive(client):
    assert login(client, "  ADMIN ", ADMIN_PW).status_code == 200


def test_expired_session(tmp_path):
    store = AuthStore(str(tmp_path / "a.db"), session_ttl=-1)
    store.bootstrap_admin("password-123")
    uid = store.get_user("admin")["id"]
    token, _ = store.create_session(uid)
    assert store.user_for_token(token) is None


def test_only_hash_of_token_is_stored(tmp_path):
    store = AuthStore(str(tmp_path / "a.db"))
    store.bootstrap_admin("password-123")
    token, _ = store.create_session(store.get_user("admin")["id"])
    rows = store._db.execute("SELECT token_hash FROM sessions").fetchall()
    assert [r[0] for r in rows] and token not in [r[0] for r in rows]


# -- bootstrap ---------------------------------------------------------------
def test_bootstrap_only_once(tmp_path):
    store = AuthStore(str(tmp_path / "a.db"))
    created = store.bootstrap_admin()  # generated password
    assert created and created[0] == "admin" and len(created[1]) >= 12
    assert store.bootstrap_admin("other-password") is None
    assert [u["username"] for u in store.list_users()] == ["admin"]
    assert store.authenticate("admin", created[1])["role"] == "admin"


def test_users_survive_restart(tmp_path):
    db = str(tmp_path / "h.db")
    with session(db) as c:
        c.post("/api/users", json={"username": "ann", "password": "password-123", "role": "viewer"})
    with session(db) as c:
        assert {u["username"] for u in c.get("/api/users").json()} == {"admin", "ann"}
        assert login(c, "ann", "password-123").status_code == 200


# -- permissions -------------------------------------------------------------
def test_viewer_can_read_but_not_change(client):
    v = make_user(client, "vera", "viewer")
    assert v.get("/api/sensors").status_code == 200
    assert v.get("/api/events").status_code == 200
    assert v.get("/api/wiring").status_code == 200
    assert v.put("/api/sensors/pir/enabled", json={"enabled": False}).status_code == 403
    assert v.post("/api/sensors/pir/simulate", json={"active": True}).status_code == 403
    assert v.delete("/api/events").status_code == 403
    assert v.get("/api/users").status_code == 403
    assert v.get("/api/roles").status_code == 403


def test_operator_can_operate_but_not_administer(client):
    o = make_user(client, "olga", "operator")
    assert o.put("/api/sensors/pir/enabled", json={"enabled": False}).status_code == 200
    assert o.delete("/api/events").status_code == 200
    assert o.get("/api/users").status_code == 403
    assert o.post("/api/roles", json={"name": "x1", "permissions": []}).status_code == 403


def test_custom_role_permissions_take_effect(client):
    r = client.post("/api/roles", json={"name": "guard", "permissions": ["sensors.view", "events.clear"]})
    assert r.status_code == 201 and r.json()["permissions"] == ["events.clear", "sensors.view"]
    g = make_user(client, "gus", "guard")
    assert g.get("/api/sensors").status_code == 200
    assert g.get("/api/events").status_code == 403  # no events.view
    assert g.delete("/api/events").status_code == 200
    # editing the role applies to existing users straight away, no re-login
    client.put("/api/roles/guard", json={"permissions": ["events.view"]})
    assert g.get("/api/events").status_code == 200
    assert g.get("/api/sensors").status_code == 403


def test_roles_manage_vs_users_manage(client):
    client.post("/api/roles", json={"name": "hr", "permissions": ["users.manage"]})
    hr = make_user(client, "hana", "hr")
    assert hr.get("/api/roles").status_code == 200  # users.manage may list roles to assign them
    assert hr.get("/api/permissions").status_code == 200
    assert hr.post("/api/roles", json={"name": "zzz", "permissions": []}).status_code == 403


def test_websocket_requires_auth(client):
    anon = TestClient(client.app)
    with pytest.raises(WebSocketDisconnect) as e:
        with anon.websocket_connect("/ws") as ws:
            ws.send_json({"type": "auth", "token": "bogus"})
            ws.receive_json()
    assert e.value.code == 4401
    with pytest.raises(WebSocketDisconnect):  # not an auth message
        with anon.websocket_connect("/ws") as ws:
            ws.send_json({"type": "hello"})
            ws.receive_json()


def test_websocket_hides_events_without_permission(client):
    client.post("/api/roles", json={"name": "glance", "permissions": ["sensors.view"]})
    g = make_user(client, "gil", "glance")
    with ws_connect(g) as ws:
        assert ws.receive_json()["type"] == "snapshot"
        client.post("/api/sensors/pir/simulate", json={"active": True})  # event: filtered out
        client.put("/api/sensors/rain/enabled", json={"enabled": False})  # sensor_state: delivered
        assert ws.receive_json()["type"] == "sensor_state"


# -- user management ---------------------------------------------------------
def test_user_validation_and_duplicates(client):
    ok = {"username": "bob", "password": "password-123", "role": "viewer"}
    assert client.post("/api/users", json=ok).status_code == 201
    assert client.post("/api/users", json={**ok, "username": "BOB"}).status_code == 409
    assert client.post("/api/users", json={**ok, "username": "x y"}).status_code == 422
    assert client.post("/api/users", json={**ok, "username": "carl", "password": "short"}).status_code == 422
    assert client.post("/api/users", json={**ok, "username": "carl", "role": "nope"}).status_code == 422


def test_user_list_never_exposes_hashes(client):
    assert "scrypt" not in client.get("/api/users").text


def test_disable_user_ends_sessions(client):
    v = make_user(client, "vera", "viewer")
    assert v.get("/api/sensors").status_code == 200
    client.patch("/api/users/vera", json={"active": False})
    assert v.get("/api/sensors").status_code == 401
    assert login(client, "vera", "password-123").status_code == 401
    client.patch("/api/users/vera", json={"active": True})
    assert login(client, "vera", "password-123").status_code == 200


def test_admin_password_reset_kills_old_sessions(client):
    v = make_user(client, "vera", "viewer")
    client.patch("/api/users/vera", json={"password": "brand-new-pass"})
    assert v.get("/api/sensors").status_code == 401
    assert login(client, "vera", "password-123").status_code == 401
    assert login(client, "vera", "brand-new-pass").status_code == 200


def test_change_own_password(client):
    v = make_user(client, "vera", "viewer")
    other_session = as_user(client, "vera", "password-123")
    bad = v.post("/api/auth/password", json={"current_password": "wrong-one", "new_password": "another-pass1"})
    assert bad.status_code == 403
    ok = v.post("/api/auth/password", json={"current_password": "password-123", "new_password": "another-pass1"})
    assert ok.status_code == 200
    assert v.get("/api/auth/me").status_code == 200  # this session stays
    assert other_session.get("/api/auth/me").status_code == 401  # others end
    assert login(client, "vera", "another-pass1").status_code == 200


def test_delete_user(client):
    v = make_user(client, "vera", "viewer")
    assert client.delete("/api/users/vera").status_code == 200
    assert v.get("/api/sensors").status_code == 401
    assert client.delete("/api/users/vera").status_code == 404


def test_cannot_lock_everyone_out(client):
    assert client.delete("/api/users/admin").status_code == 409  # yourself
    assert client.patch("/api/users/admin", json={"active": False}).status_code == 409  # last manager
    assert client.patch("/api/users/admin", json={"role": "viewer"}).status_code == 409
    # with a second admin it is allowed, and then the remaining one is protected
    make_user(client, "root2", "admin")
    other = as_user(client, "root2", "password-123")
    assert other.patch("/api/users/admin", json={"role": "viewer"}).status_code == 200
    assert other.patch("/api/users/root2", json={"role": "viewer"}).status_code == 409
    assert other.delete("/api/users/root2").status_code == 409


def test_cannot_strip_last_manager_via_role(client):
    client.post("/api/roles", json={"name": "hr", "permissions": ["users.manage", "roles.manage"]})
    client.post("/api/users", json={"username": "hana", "password": "password-123", "role": "hr"})
    client.patch("/api/users/admin", json={"role": "viewer"})  # fine: hana still manages users
    hana = as_user(client, "hana", "password-123")
    assert hana.put("/api/roles/hr", json={"permissions": ["roles.manage"]}).status_code == 409


# -- role management ---------------------------------------------------------
def test_role_rules(client):
    assert client.put("/api/roles/admin", json={"permissions": []}).status_code == 409  # locked
    assert client.delete("/api/roles/viewer").status_code == 409  # built-in
    assert client.post("/api/roles", json={"name": "r1", "permissions": ["bogus.perm"]}).status_code == 422
    assert client.post("/api/roles", json={"name": "Bad Name", "permissions": []}).status_code == 422
    assert client.post("/api/roles", json={"name": "r1", "permissions": []}).status_code == 201
    assert client.post("/api/roles", json={"name": "r1", "permissions": []}).status_code == 409
    client.post("/api/users", json={"username": "rob", "password": "password-123", "role": "r1"})
    assert client.delete("/api/roles/r1").status_code == 409  # in use
    client.delete("/api/users/rob")
    assert client.delete("/api/roles/r1").status_code == 200
    assert client.delete("/api/roles/r1").status_code == 404


def test_role_list_shape(client):
    roles = {r["name"]: r for r in client.get("/api/roles").json()}
    assert set(roles) >= {"admin", "operator", "viewer"}
    assert roles["admin"]["locked"] and roles["admin"]["builtin"] and roles["admin"]["users"] == 1
    assert not roles["viewer"]["locked"]
    names = {p["name"] for p in client.get("/api/permissions").json()}
    assert names == set(PERMISSIONS)


def test_admin_role_gains_new_permissions_on_upgrade(tmp_path):
    db = str(tmp_path / "a.db")
    store = AuthStore(db)
    store._db.execute("DELETE FROM role_permissions WHERE role='admin' AND permission='roles.manage'")
    store._db.commit()
    store.close()
    store = AuthStore(db)  # re-open: admin is topped up
    assert "roles.manage" in {r["name"]: r for r in store.list_roles()}["admin"]["permissions"]


def test_auth_error_type():
    store = AuthStore()
    with pytest.raises(AuthError) as e:
        store.get_user("ghost")
    assert e.value.status == 404
