"""Schedule rules: enable chosen sensors between a start and an end time.

Model: a sensor's *baseline* is the manual on/off setting kept in ``sensor_settings`` (EventStore).
A rule never touches the baseline; while its window is open it only *holds* its sensors enabled.
The effective state is therefore ``baseline OR held by an open rule``, recomputed by
``reconcile()``. When a rule ends (or is deleted) the sensor simply falls back to its baseline,
which is exactly the state it had before the rule, with nothing to snapshot or restore.
Times are epoch seconds (UTC), like event timestamps.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time

MAX_NAME = 60


class ScheduleError(Exception):
    """An expected failure that maps to an HTTP status."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status, self.message = status, message


def status_of(rule: dict, now: float) -> str:
    if now < rule["start"]:
        return "upcoming"
    return "active" if now < rule["end"] else "ended"


class ScheduleStore:
    def __init__(self, path: str = ":memory:") -> None:
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute(
                """CREATE TABLE IF NOT EXISTS schedule_rules (
                       id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT NOT NULL,
                       sensors TEXT NOT NULL,
                       start REAL NOT NULL,
                       end REAL NOT NULL,
                       created_by TEXT NOT NULL,
                       created_at REAL NOT NULL)"""
            )
            self._db.commit()

    @staticmethod
    def _row(r: sqlite3.Row) -> dict:
        return {
            "id": r["id"], "name": r["name"], "sensors": json.loads(r["sensors"]),
            "start": r["start"], "end": r["end"], "created_by": r["created_by"], "created_at": r["created_at"],
        }

    @staticmethod
    def validate(name: str, sensors: list[str], start: float, end: float, known: set[str], now: float) -> tuple:
        name = name.strip()
        if not name or len(name) > MAX_NAME:
            raise ScheduleError(422, f"name must be 1 to {MAX_NAME} characters")
        chosen = sorted(set(sensors))
        if not chosen:
            raise ScheduleError(422, "select at least one sensor")
        unknown = [s for s in chosen if s not in known]
        if unknown:
            raise ScheduleError(422, f"unknown sensors: {', '.join(unknown)}")
        if end <= start:
            raise ScheduleError(422, "the end must be after the start")
        if end <= now:
            raise ScheduleError(422, "the end is already in the past")
        return name, chosen

    def list(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM schedule_rules ORDER BY start, id").fetchall()
        return [self._row(r) for r in rows]

    def get(self, rule_id: int) -> dict:
        with self._lock:
            r = self._db.execute("SELECT * FROM schedule_rules WHERE id = ?", (rule_id,)).fetchone()
        if not r:
            raise ScheduleError(404, "no such rule")
        return self._row(r)

    def create(self, name: str, sensors: list[str], start: float, end: float, user: str) -> dict:
        with self._lock:
            cur = self._db.execute(
                "INSERT INTO schedule_rules (name, sensors, start, end, created_by, created_at) VALUES (?,?,?,?,?,?)",
                (name, json.dumps(sensors), start, end, user, time.time()),
            )
            self._db.commit()
            rule_id = cur.lastrowid
        return self.get(rule_id)

    def update(self, rule_id: int, name: str, sensors: list[str], start: float, end: float) -> dict:
        self.get(rule_id)
        with self._lock:
            self._db.execute(
                "UPDATE schedule_rules SET name=?, sensors=?, start=?, end=? WHERE id=?",
                (name, json.dumps(sensors), start, end, rule_id),
            )
            self._db.commit()
        return self.get(rule_id)

    def delete(self, rule_id: int) -> None:
        self.get(rule_id)
        with self._lock:
            self._db.execute("DELETE FROM schedule_rules WHERE id = ?", (rule_id,))
            self._db.commit()

    def holds(self, now: float) -> dict[str, dict]:
        """sensor -> the open rule that holds it enabled the longest (the one ending last)."""
        held: dict[str, dict] = {}
        for rule in self.list():
            if rule["start"] <= now < rule["end"]:
                for s in rule["sensors"]:
                    if s not in held or rule["end"] > held[s]["end"]:
                        held[s] = rule
        return held

    def close(self) -> None:
        with self._lock:
            self._db.close()
