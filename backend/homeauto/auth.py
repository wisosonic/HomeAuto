"""Authentication and authorisation: users, roles and permissions, stored in SQLite.

Model
  * a **permission** is a fixed string defined in PERMISSIONS (code decides what exists);
  * a **role** is a named set of permissions (stored, editable via the API);
  * a **user** has exactly one role. Their permissions are the role's permissions.

Built-in roles (cannot be deleted): ``admin`` (always every permission, locked),
``operator`` and ``viewer`` (editable defaults).

Sessions are opaque random bearer tokens. Only the SHA-256 of a token is stored, so a copy of the
database cannot be replayed. Passwords are hashed with scrypt (standard library, no extra package).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time
from contextlib import contextmanager

# permission -> description (shown in the role editor)
PERMISSIONS: dict[str, str] = {
    "sensors.view": "See sensor states and the live feed",
    "sensors.control": "Enable or disable sensors",
    "sensors.simulate": "Trigger sensors (mock mode only)",
    "events.view": "See the event history",
    "events.clear": "Delete the event history",
    "wiring.view": "See wiring and pin configuration",
    "users.manage": "Create, edit and delete users",
    "roles.manage": "Create, edit and delete roles",
}

DEFAULT_ROLES: dict[str, list[str]] = {
    "admin": list(PERMISSIONS),
    "operator": [
        "sensors.view", "sensors.control", "sensors.simulate",
        "events.view", "events.clear", "wiring.view",
    ],
    "viewer": ["sensors.view", "events.view", "wiring.view"],
}
LOCKED_ROLE = "admin"  # always holds every permission

SESSION_TTL = 12 * 3600  # seconds
MAX_FAILURES = 5  # failed logins before a username is locked...
LOCKOUT_SECONDS = 60  # ...for this long

_USERNAME = re.compile(r"^[a-z0-9_.-]{3,32}$")
_ROLE_NAME = re.compile(r"^[a-z0-9_-]{2,32}$")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


class AuthError(Exception):
    """An expected failure that maps to an HTTP status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


# -- passwords ---------------------------------------------------------------
def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return f"scrypt${_SCRYPT['n']}${_SCRYPT['r']}${_SCRYPT['p']}${_b64(salt)}${_b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(dk)
        cand = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(cand, expected)


_DUMMY_HASH = hash_password("not-a-real-password")  # burns the same time for unknown usernames


def _check_password_policy(password: str) -> None:
    if not 8 <= len(password) <= 128:
        raise AuthError(422, "password must be 8 to 128 characters")


def _norm_username(username: str) -> str:
    u = username.strip().lower()
    if not _USERNAME.match(u):
        raise AuthError(422, "username must be 3-32 characters: letters, digits, '.', '_' or '-'")
    return u


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthStore:
    def __init__(self, path: str = ":memory:", session_ttl: int = SESSION_TTL) -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._lock = threading.RLock()
        self._ttl = session_ttl
        self._failures: dict[str, tuple[int, float]] = {}  # username -> (count, locked_until)
        with self._tx() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS roles (
                    name TEXT PRIMARY KEY, builtin INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS role_permissions (
                    role TEXT NOT NULL REFERENCES roles(name) ON DELETE CASCADE ON UPDATE CASCADE,
                    permission TEXT NOT NULL,
                    PRIMARY KEY (role, permission));
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL REFERENCES roles(name) ON UPDATE CASCADE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL);
                """
            )
            for name, perms in DEFAULT_ROLES.items():
                if not db.execute("SELECT 1 FROM roles WHERE name = ?", (name,)).fetchone():
                    db.execute("INSERT INTO roles (name, builtin) VALUES (?, 1)", (name,))
                    db.executemany("INSERT INTO role_permissions VALUES (?, ?)", [(name, p) for p in perms])
            # admin always has everything, including permissions added by a later version
            db.executemany(
                "INSERT OR IGNORE INTO role_permissions VALUES (?, ?)", [(LOCKED_ROLE, p) for p in PERMISSIONS]
            )
            # drop permissions that no longer exist in code
            marks = ",".join("?" * len(PERMISSIONS))
            db.execute(f"DELETE FROM role_permissions WHERE permission NOT IN ({marks})", list(PERMISSIONS))

    @contextmanager
    def _tx(self):
        with self._lock:
            try:
                yield self._db
                self._db.commit()
            except BaseException:
                self._db.rollback()
                raise

    # -- bootstrap ---------------------------------------------------------------
    def bootstrap_admin(self, password: str | None = None) -> tuple[str, str] | None:
        """If there are no users yet, create ``admin``. Returns (username, password) if created."""
        with self._lock:
            if self._db.execute("SELECT 1 FROM users LIMIT 1").fetchone():
                return None
            password = password or secrets.token_urlsafe(12)
            self.create_user("admin", password, LOCKED_ROLE)
            return "admin", password

    # -- users -------------------------------------------------------------------
    def _perms(self, role: str) -> list[str]:
        rows = self._db.execute(
            "SELECT permission FROM role_permissions WHERE role = ? ORDER BY permission", (role,)
        ).fetchall()
        return [r["permission"] for r in rows]

    def _public(self, row: sqlite3.Row) -> dict:
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "active": bool(row["active"]),
            "created_at": row["created_at"],
            "permissions": self._perms(row["role"]),
        }

    def _user_row(self, username: str) -> sqlite3.Row:
        row = self._db.execute("SELECT * FROM users WHERE username = ?", (username.strip().lower(),)).fetchone()
        if not row:
            raise AuthError(404, f"unknown user {username!r}")
        return row

    def _require_manager_left(self) -> None:
        """At least one active user must keep ``users.manage``, or nobody could administer the system."""
        n = self._db.execute(
            "SELECT COUNT(*) FROM users u JOIN role_permissions rp ON rp.role = u.role "
            "WHERE u.active = 1 AND rp.permission = 'users.manage'"
        ).fetchone()[0]
        if n == 0:
            raise AuthError(409, "this would leave no active user able to manage users")

    def list_users(self) -> list[dict]:
        with self._lock:
            return [self._public(r) for r in self._db.execute("SELECT * FROM users ORDER BY username")]

    def get_user(self, username: str) -> dict:
        with self._lock:
            return self._public(self._user_row(username))

    def create_user(self, username: str, password: str, role: str) -> dict:
        username = _norm_username(username)
        _check_password_policy(password)
        pw_hash = hash_password(password)
        with self._tx() as db:
            if not db.execute("SELECT 1 FROM roles WHERE name = ?", (role,)).fetchone():
                raise AuthError(422, f"unknown role {role!r}")
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash, role, created_at) VALUES (?,?,?,?)",
                    (username, pw_hash, role, time.time()),
                )
            except sqlite3.IntegrityError:
                raise AuthError(409, f"user {username!r} already exists") from None
            return self._public(self._user_row(username))

    def update_user(
        self, username: str, *, role: str | None = None, active: bool | None = None, password: str | None = None
    ) -> dict:
        if password is not None:
            _check_password_policy(password)
        pw_hash = hash_password(password) if password is not None else None
        with self._tx() as db:
            row = self._user_row(username)
            if role is not None:
                if not db.execute("SELECT 1 FROM roles WHERE name = ?", (role,)).fetchone():
                    raise AuthError(422, f"unknown role {role!r}")
                db.execute("UPDATE users SET role = ? WHERE id = ?", (role, row["id"]))
            if active is not None:
                db.execute("UPDATE users SET active = ? WHERE id = ?", (int(active), row["id"]))
            if pw_hash is not None:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (pw_hash, row["id"]))
            if active is False or pw_hash is not None:
                db.execute("DELETE FROM sessions WHERE user_id = ?", (row["id"],))  # force re-login
            self._require_manager_left()
            return self._public(self._user_row(username))

    def delete_user(self, username: str) -> None:
        with self._tx() as db:
            row = self._user_row(username)
            db.execute("DELETE FROM users WHERE id = ?", (row["id"],))  # sessions cascade
            self._require_manager_left()

    def change_password(self, username: str, current: str, new: str, keep_token: str | None = None) -> None:
        """Self-service password change. Other sessions of the user are ended; ``keep_token`` survives."""
        _check_password_policy(new)
        with self._tx() as db:
            row = self._user_row(username)
            if not verify_password(current, row["password_hash"]):
                raise AuthError(403, "current password is incorrect")
            db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new), row["id"]))
            db.execute(
                "DELETE FROM sessions WHERE user_id = ? AND token_hash != ?",
                (row["id"], _hash_token(keep_token) if keep_token else ""),
            )

    # -- login / sessions --------------------------------------------------------
    def authenticate(self, username: str, password: str) -> dict:
        """Check credentials, with a temporary lockout after repeated failures."""
        key = username.strip().lower()[:64]
        now = time.time()
        with self._lock:
            count, locked_until = self._failures.get(key, (0, 0.0))
            if locked_until > now:
                raise AuthError(429, "too many failed attempts, try again in a minute")
            row = self._db.execute("SELECT * FROM users WHERE username = ?", (key,)).fetchone()
        ok = verify_password(password, row["password_hash"] if row else _DUMMY_HASH)
        if not (ok and row and row["active"]):
            with self._lock:
                if len(self._failures) > 1000:  # bound memory against random-username floods
                    self._failures = {k: v for k, v in self._failures.items() if v[1] > now}
                count = 0 if locked_until and locked_until <= now else count  # lock expired: start over
                count += 1
                self._failures[key] = (count, now + LOCKOUT_SECONDS if count >= MAX_FAILURES else 0.0)
            raise AuthError(401, "invalid username or password")
        with self._lock:
            self._failures.pop(key, None)
            return self._public(row)

    def create_session(self, user_id: int) -> tuple[str, float]:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._tx() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))  # housekeeping
            db.execute(
                "INSERT INTO sessions VALUES (?,?,?,?)", (_hash_token(token), user_id, now, now + self._ttl)
            )
        return token, now + self._ttl

    def user_for_token(self, token: str | None) -> dict | None:
        if not token or not isinstance(token, str):
            return None
        with self._lock:
            row = self._db.execute(
                "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.token_hash = ? AND s.expires_at > ? AND u.active = 1",
                (_hash_token(token), time.time()),
            ).fetchone()
            return self._public(row) if row else None

    def revoke_token(self, token: str) -> None:
        with self._tx() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))

    # -- roles -------------------------------------------------------------------
    @staticmethod
    def _check_permissions(permissions: list[str]) -> list[str]:
        unknown = sorted(set(permissions) - set(PERMISSIONS))
        if unknown:
            raise AuthError(422, f"unknown permissions: {', '.join(unknown)}")
        return sorted(set(permissions))

    def _role(self, row: sqlite3.Row) -> dict:
        users = self._db.execute("SELECT COUNT(*) FROM users WHERE role = ?", (row["name"],)).fetchone()[0]
        return {
            "name": row["name"],
            "builtin": bool(row["builtin"]),
            "locked": row["name"] == LOCKED_ROLE,
            "permissions": self._perms(row["name"]),
            "users": users,
        }

    def list_roles(self) -> list[dict]:
        with self._lock:
            return [self._role(r) for r in self._db.execute("SELECT * FROM roles ORDER BY builtin DESC, name")]

    def _role_row(self, name: str) -> sqlite3.Row:
        row = self._db.execute("SELECT * FROM roles WHERE name = ?", (name,)).fetchone()
        if not row:
            raise AuthError(404, f"unknown role {name!r}")
        return row

    def create_role(self, name: str, permissions: list[str]) -> dict:
        name = name.strip().lower()
        if not _ROLE_NAME.match(name):
            raise AuthError(422, "role name must be 2-32 characters: letters, digits, '_' or '-'")
        perms = self._check_permissions(permissions)
        with self._tx() as db:
            try:
                db.execute("INSERT INTO roles (name, builtin) VALUES (?, 0)", (name,))
            except sqlite3.IntegrityError:
                raise AuthError(409, f"role {name!r} already exists") from None
            db.executemany("INSERT INTO role_permissions VALUES (?, ?)", [(name, p) for p in perms])
            return self._role(self._role_row(name))

    def update_role(self, name: str, permissions: list[str]) -> dict:
        perms = self._check_permissions(permissions)
        with self._tx() as db:
            row = self._role_row(name)
            if row["name"] == LOCKED_ROLE:
                raise AuthError(409, "the admin role always has every permission and cannot be edited")
            db.execute("DELETE FROM role_permissions WHERE role = ?", (name,))
            db.executemany("INSERT INTO role_permissions VALUES (?, ?)", [(name, p) for p in perms])
            self._require_manager_left()
            return self._role(row)

    def delete_role(self, name: str) -> None:
        with self._tx() as db:
            row = self._role_row(name)
            if row["builtin"]:
                raise AuthError(409, f"{name!r} is a built-in role and cannot be deleted")
            n = db.execute("SELECT COUNT(*) FROM users WHERE role = ?", (name,)).fetchone()[0]
            if n:
                raise AuthError(409, f"role {name!r} is still assigned to {n} user(s)")
            db.execute("DELETE FROM roles WHERE name = ?", (name,))

    def close(self) -> None:
        with self._lock:
            self._db.close()
