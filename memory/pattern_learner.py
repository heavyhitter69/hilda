"""
memory/pattern_learner.py — Detect habit patterns from stored actions.
"""
from datetime import datetime
from collections import Counter
from memory.memory_manager import MemoryManager
from core.logger import get_logger

log = get_logger(__name__)


class PatternLearner:
    """Analyses the memory database to detect recurring actions."""

    def __init__(self) -> None:
        self._mem = MemoryManager()

    def get_suggestion_now(self) -> str:
        """
        Check if the user tends to do something at this hour.
        Returns a proactive suggestion string, or empty string if nothing notable.
        """
        hour = datetime.now().hour
        actions = self._mem.get_actions_by_hour(hour)
        if not actions:
            return ""

        # Find the most common action at this hour
        counter = Counter(actions)
        top_action, count = counter.most_common(1)[0]
        if count < 2:
            return ""  # need at least 2 occurrences to suggest

        # Humanise hour
        period = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
        short = top_action[:60]
        suggestion = (
            f"Good {period}! I noticed you often {short} around this time. "
            f"Shall I do that now?"
        )
        log.info("Pattern suggestion: %s", suggestion)
        return suggestion

    def summarise_patterns(self) -> str:
        """Return a human-readable summary of detected habits."""
        recent = self._mem.get_recent(100)
        if not recent:
            return "No patterns detected yet — keep using me and I'll learn your habits!"

        hour_buckets: dict[int, list[str]] = {}
        for row in recent:
            try:
                dt = datetime.fromisoformat(row["timestamp"])
                hour_buckets.setdefault(dt.hour, []).append(row["action"])
            except Exception:
                continue

        lines = []
        for hour in sorted(hour_buckets.keys()):
            actions = hour_buckets[hour]
            top = Counter(actions).most_common(1)[0]
            time_str = f"{hour:02d}:00"
            lines.append(f"  {time_str} -> {top[0][:50]} ({top[1]} times)")

        return "Detected habits:\n" + "\n".join(lines) if lines else "Still learning…"
