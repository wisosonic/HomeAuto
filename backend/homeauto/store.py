"""SQLite storage: event history and per-sensor settings. Written from gpiozero
threads, so access is locked."""

from __future__ import annotations

import sqlite3
import threading

from homeauto.base import SensorEvent


class EventStore:
    def __init__(self, path: str = "homeauto.db") -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS events (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       sensor TEXT NOT NULL,
                       kind TEXT NOT NULL,
                       active INTEGER NOT NULL,
                       timestamp REAL NOT NULL)"""
            )
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS sensor_settings (sensor TEXT PRIMARY KEY, enabled INTEGER NOT NULL)"
            )
            self._db.commit()

    # -- events ----------------------------------------------------------
    def add(self, ev: SensorEvent) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO events (sensor, kind, active, timestamp) VALUES (?,?,?,?)",
                (ev.sensor, ev.kind, int(ev.active), ev.timestamp),
            )
            self._db.commit()

    def recent(self, limit: int = 50, sensor: str | None = None) -> list[dict]:
        sql = "SELECT sensor, kind, active, timestamp FROM events"
        args: list = []
        if sensor:
            sql += " WHERE sensor = ?"
            args.append(sensor)
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(limit)
        with self._lock:
            rows = self._db.execute(sql, args).fetchall()
        return [{**dict(r), "active": bool(r["active"])} for r in rows]

    def clear(self, sensor: str | None = None) -> int:
        """Delete all events (or one sensor's). Returns the number deleted."""
        with self._lock:
            if sensor:
                cur = self._db.execute("DELETE FROM events WHERE sensor = ?", (sensor,))
            else:
                cur = self._db.execute("DELETE FROM events")
            self._db.commit()
            return cur.rowcount

    # -- sensor settings -------------------------------------------------
    def disabled_sensors(self) -> set[str]:
        with self._lock:
            rows = self._db.execute("SELECT sensor FROM sensor_settings WHERE enabled = 0").fetchall()
        return {r["sensor"] for r in rows}

    def set_enabled(self, sensor: str, enabled: bool) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO sensor_settings (sensor, enabled) VALUES (?, ?) "
                "ON CONFLICT(sensor) DO UPDATE SET enabled = excluded.enabled",
                (sensor, int(enabled)),
            )
            self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()
