"""SQLite event history. Written from gpiozero threads, so access is locked."""

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
            self._db.commit()

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

    def close(self) -> None:
        with self._lock:
            self._db.close()
