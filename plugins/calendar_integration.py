"""
plugins/calendar_integration.py — Calendar management for Hilda.

Supports ICS file import and a local JSON-based event store.
Can show today's schedule, upcoming events, and add new events.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _events_path() -> Path:
    p = settings.WRITABLE_ROOT / "memory" / "calendar_events.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_events() -> list[dict[str, Any]]:
    path = _events_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_events(events: list[dict[str, Any]]) -> None:
    path = _events_path()
    path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")


def add_event(
    title: str,
    start_time: str,
    end_time: Optional[str] = None,
    description: str = "",
    location: str = "",
) -> str:
    """
    Add a calendar event.

    Parameters
    ----------
    title : str — event title
    start_time : str — start time in "YYYY-MM-DD HH:MM" or "HH:MM" (today) format
    end_time : str — optional end time
    description : str — event description
    location : str — event location
    """
    try:
        # Parse start time
        start = _parse_time(start_time)
        if start is None:
            return f"Could not parse time: {start_time}. Use 'YYYY-MM-DD HH:MM' or 'HH:MM'."

        end = _parse_time(end_time) if end_time else start + timedelta(hours=1)

        event = {
            "title": title,
            "start": start.isoformat(),
            "end": end.isoformat() if end else "",
            "description": description,
            "location": location,
            "created_at": datetime.now().isoformat(),
        }

        events = _load_events()
        events.append(event)
        _save_events(events)

        time_str = start.strftime("%I:%M %p on %A, %B %d")
        log.info("Calendar event added: %s at %s", title, time_str)
        return f"Added '{title}' to your calendar at {time_str}."

    except Exception as e:
        log.error("add_event failed: %s", e)
        return f"Could not add event: {e}"


def _parse_time(time_str: str) -> Optional[datetime]:
    """Parse a time string into a datetime object."""
    if not time_str:
        return None
    s = time_str.strip()

    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M",
        "%m/%d/%Y %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue

    # Try HH:MM (today)
    try:
        t = datetime.strptime(s, "%H:%M").time()
        dt = datetime.combine(datetime.now().date(), t)
        if dt < datetime.now():
            dt += timedelta(days=1)  # If time has passed, assume tomorrow
        return dt
    except ValueError:
        pass

    # Try "3pm", "3:30pm" style
    import re
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", s.lower())
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2) or 0)
        if m.group(3) == "pm" and hour != 12:
            hour += 12
        if m.group(3) == "am" and hour == 12:
            hour = 0
        dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt < datetime.now():
            dt += timedelta(days=1)
        return dt

    return None


def get_todays_events() -> str:
    """Return today's scheduled events."""
    events = _load_events()
    today = datetime.now().date()

    todays = []
    for e in events:
        try:
            start = datetime.fromisoformat(e["start"])
            if start.date() == today:
                todays.append(e)
        except Exception:
            continue

    if not todays:
        return "You have no events scheduled for today."

    todays.sort(key=lambda x: x.get("start", ""))
    lines = [f"Today's schedule ({today.strftime('%A, %B %d')}):"]
    for e in todays:
        start = datetime.fromisoformat(e["start"])
        time_str = start.strftime("%I:%M %p")
        loc = f" at {e['location']}" if e.get("location") else ""
        lines.append(f"  • {time_str} — {e['title']}{loc}")

    return "\n".join(lines)


def get_upcoming_events(days: int = 7) -> str:
    """Return events for the next N days."""
    events = _load_events()
    now = datetime.now()
    cutoff = now + timedelta(days=days)

    upcoming = []
    for e in events:
        try:
            start = datetime.fromisoformat(e["start"])
            if now <= start <= cutoff:
                upcoming.append(e)
        except Exception:
            continue

    if not upcoming:
        return f"No events scheduled in the next {days} days."

    upcoming.sort(key=lambda x: x.get("start", ""))
    lines = [f"Upcoming events (next {days} days):"]
    for e in upcoming:
        start = datetime.fromisoformat(e["start"])
        date_str = start.strftime("%a %b %d, %I:%M %p")
        lines.append(f"  • {date_str} — {e['title']}")

    return "\n".join(lines)


def delete_event(title_query: str) -> str:
    """Delete an event by title (fuzzy match)."""
    events = _load_events()
    q = title_query.lower()
    remaining = [e for e in events if q not in e.get("title", "").lower()]
    removed = len(events) - len(remaining)

    if removed == 0:
        return f"No events found matching '{title_query}'."

    _save_events(remaining)
    return f"Removed {removed} event(s) matching '{title_query}'."


def import_ics(path: str) -> str:
    """Import events from an ICS/iCal file."""
    try:
        from icalendar import Calendar
        p = Path(path).expanduser()
        if not p.exists():
            return f"File not found: {path}"

        cal = Calendar.from_ical(p.read_bytes())
        events = _load_events()
        imported = 0

        for component in cal.walk():
            if component.name == "VEVENT":
                title = str(component.get("SUMMARY", "Untitled"))
                start = component.get("DTSTART")
                end = component.get("DTEND")
                desc = str(component.get("DESCRIPTION", ""))
                loc = str(component.get("LOCATION", ""))

                event = {
                    "title": title,
                    "start": start.dt.isoformat() if start else "",
                    "end": end.dt.isoformat() if end else "",
                    "description": desc,
                    "location": loc,
                    "created_at": datetime.now().isoformat(),
                    "source": "ics_import",
                }
                events.append(event)
                imported += 1

        _save_events(events)
        return f"Imported {imported} events from {p.name}."

    except ImportError:
        return "ICS import requires icalendar. Install with: pip install icalendar"
    except Exception as e:
        log.error("ICS import failed: %s", e)
        return f"Could not import calendar: {e}"
