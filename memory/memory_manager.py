"""
memory/memory_manager.py — SQLite-backed action log and pattern store.
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

settings.MEMORY_DB.parent.mkdir(parents=True, exist_ok=True)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS actions (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    hour      INTEGER NOT NULL,
    weekday   INTEGER NOT NULL,
    action    TEXT    NOT NULL,
    response  TEXT
);
"""


class MemoryManager:
    """Simple SQLite CRUD layer for storing user interactions."""

    def __init__(self) -> None:
        self._db = str(settings.MEMORY_DB)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_SCHEMA)
            conn.commit()

    def log_action(self, action: str, response: str = "") -> None:
        """Store a user action with its timestamp."""
        now = datetime.now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO actions (timestamp, hour, weekday, action, response) "
                "VALUES (?, ?, ?, ?, ?)",
                (now.isoformat(), now.hour, now.weekday(), action, response),
            )
            conn.commit()
        log.debug("Logged action: '%s'", action[:60])

    def get_recent(self, limit: int = 20) -> list[dict]:
        """Return the most recent actions as a list of dicts."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT timestamp, action, response FROM actions "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [{"timestamp": r[0], "action": r[1], "response": r[2]} for r in rows]

    def get_actions_by_hour(self, hour: int) -> list[str]:
        """Return distinct actions historically performed at a given hour."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT action FROM actions WHERE hour = ? LIMIT 10",
                (hour,),
            ).fetchall()
        return [r[0] for r in rows]

    def clear(self) -> None:
        """Delete all stored actions (for testing)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM actions")
            conn.commit()
