"""
memory/conversation_store.py — Persistent conversation threads.

Saves and loads full conversation threads to/from disk so Hilda
can maintain context across restarts and reference past conversations.
"""
from __future__ import annotations

import json

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _conversations_dir() -> Path:
    d = settings.WRITABLE_ROOT / "memory" / "conversations"
    d.mkdir(parents=True, exist_ok=True)
    return d


class ConversationThread:
    """A single conversation thread with messages and metadata."""

    def __init__(
        self,
        thread_id: Optional[str] = None,
        title: str = "New conversation",
        messages: Optional[list[dict]] = None,
    ) -> None:
        self.id = thread_id or str(uuid.uuid4())[:8]
        self.title = title
        self.messages: list[dict] = messages or []
        self.created_at: str = datetime.now().isoformat()
        self.updated_at: str = self.created_at
        self.summary: str = ""
        self.turn_count: int = len(self.messages) // 2

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        self.updated_at = datetime.now().isoformat()
        if role == "assistant":
            self.turn_count += 1

    def get_history(self, max_turns: int = 20) -> list[dict]:
        """Return the last N turns as [{"role": ..., "content": ...}] for LLM context."""
        recent = self.messages[-(max_turns * 2):]
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "messages": self.messages,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "summary": self.summary,
            "turn_count": self.turn_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConversationThread":
        thread = cls(
            thread_id=data.get("id"),
            title=data.get("title", "Untitled"),
            messages=data.get("messages", []),
        )
        thread.created_at = data.get("created_at", thread.created_at)
        thread.updated_at = data.get("updated_at", thread.updated_at)
        thread.summary = data.get("summary", "")
        thread.turn_count = data.get("turn_count", 0)
        return thread


class ConversationStore:
    """Manages persistent conversation threads on disk."""

    def __init__(self) -> None:
        self._dir = _conversations_dir()

    def _thread_path(self, thread_id: str) -> Path:
        return self._dir / f"{thread_id}.json"

    def save(self, thread: ConversationThread) -> None:
        """Save a conversation thread to disk."""
        try:
            path = self._thread_path(thread.id)
            path.write_text(
                json.dumps(thread.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.debug("Saved conversation '%s' (%d messages)", thread.id, len(thread.messages))
        except Exception as e:
            log.error("Failed to save conversation %s: %s", thread.id, e)

    def load(self, thread_id: str) -> Optional[ConversationThread]:
        """Load a conversation thread from disk."""
        path = self._thread_path(thread_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ConversationThread.from_dict(data)
        except Exception as e:
            log.error("Failed to load conversation %s: %s", thread_id, e)
            return None

    def list_conversations(self, limit: int = 20) -> list[dict[str, Any]]:
        """List recent conversations with their titles and metadata."""
        threads = []
        try:
            for path in sorted(self._dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                if len(threads) >= limit:
                    break
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    threads.append({
                        "id": data.get("id", path.stem),
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", ""),
                        "turn_count": data.get("turn_count", 0),
                        "summary": data.get("summary", "")[:100],
                    })
                except Exception:
                    continue
        except Exception as e:
            log.error("list_conversations failed: %s", e)
        return threads

    def get_latest(self, max_age_minutes: int = 30) -> Optional[ConversationThread]:
        """Load the most recent conversation if it's recent enough to resume."""
        convos = self.list_conversations(limit=1)
        if not convos:
            return None
        latest = convos[0]
        updated = latest.get("updated_at", "")
        if updated:
            try:
                dt = datetime.fromisoformat(updated)
                age = (datetime.now() - dt).total_seconds() / 60
                if age <= max_age_minutes:
                    return self.load(latest["id"])
            except Exception:
                pass
        return None

    def delete(self, thread_id: str) -> bool:
        """Delete a conversation thread."""
        path = self._thread_path(thread_id)
        try:
            if path.exists():
                path.unlink()
                return True
        except Exception as e:
            log.error("Failed to delete conversation %s: %s", thread_id, e)
        return False

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search conversations by content (basic text search)."""
        matches = []
        q_low = query.lower()
        try:
            for path in self._dir.glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    messages = data.get("messages", [])
                    for msg in messages:
                        if q_low in (msg.get("content") or "").lower():
                            matches.append({
                                "id": data.get("id", path.stem),
                                "title": data.get("title", "Untitled"),
                                "match_preview": msg["content"][:100],
                                "updated_at": data.get("updated_at", ""),
                            })
                            break
                except Exception:
                    continue
                if len(matches) >= limit:
                    break
        except Exception as e:
            log.error("search_conversations failed: %s", e)
        return matches


def auto_title_conversation(messages: list[dict]) -> str:
    """Generate a short title for a conversation based on its content."""
    if not messages:
        return "New conversation"

    # Use the first user message as a basis
    first_user = next(
        (m["content"] for m in messages if m.get("role") == "user"),
        None,
    )
    if not first_user:
        return "New conversation"

    # Try LLM-based titling
    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "Generate a very short title (3-6 words) for this conversation. Respond with ONLY the title, nothing else."},
                {"role": "user", "content": f"First message: {first_user[:200]}"},
            ],
            options={"temperature": 0.3, "num_predict": 20},
        )
        title = response["message"]["content"].strip().strip('"').strip("'")
        if title and len(title) < 80:
            return title
    except Exception:
        pass

    # Fallback: truncate first message
    words = first_user.split()[:6]
    return " ".join(words) + ("…" if len(first_user.split()) > 6 else "")
