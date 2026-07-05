"""
memory/memory_manager.py — SQLite-backed action log and pattern store.
"""
import sqlite3
from datetime import datetime



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

CREATE TABLE IF NOT EXISTS reminders (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT    NOT NULL,
    message   TEXT    NOT NULL,
    due_time  TEXT    NOT NULL,
    completed INTEGER DEFAULT 0
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
            conn.executescript(_SCHEMA)
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
            conn.execute("DELETE FROM reminders")
            conn.commit()

    def add_reminder(self, message: str, due_time: datetime) -> int:
        """Store a new reminder."""
        now = datetime.now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO reminders (timestamp, message, due_time, completed) "
                "VALUES (?, ?, ?, 0)",
                (now.isoformat(), message, due_time.isoformat()),
            )
            conn.commit()
            return cur.lastrowid

    def get_due_reminders(self) -> list[dict]:
        """Return reminders that are due and not yet completed."""
        now = datetime.now().isoformat()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, message, due_time FROM reminders "
                "WHERE completed = 0 AND due_time <= ?",
                (now,),
            ).fetchall()
        return [{"id": r[0], "message": r[1], "due_time": r[2]} for r in rows]

    def mark_reminder_completed(self, reminder_id: int) -> None:
        """Mark a reminder as completed."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE reminders SET completed = 1 WHERE id = ?",
                (reminder_id,),
            )
            conn.commit()

    def get_all_reminders(self, include_completed: bool = False) -> list[dict]:
        """Return all reminders."""
        query = "SELECT id, message, due_time, completed FROM reminders"
        if not include_completed:
            query += " WHERE completed = 0"
        query += " ORDER BY due_time ASC"
        
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        return [
            {"id": r[0], "message": r[1], "due_time": r[2], "completed": bool(r[3])}
            for r in rows
        ]

    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder by ID."""
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
            conn.commit()
            return cur.rowcount > 0
