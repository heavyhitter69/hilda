"""
plugins/contacts_manager.py — Local contacts store for Hilda.

Simple JSON-based contacts with fuzzy search.
Integrates with email for auto-completing recipients.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _contacts_path() -> Path:
    p = settings.WRITABLE_ROOT / "memory" / "contacts.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_contacts() -> list[dict[str, Any]]:
    path = _contacts_path()
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_contacts(contacts: list[dict[str, Any]]) -> None:
    path = _contacts_path()
    path.write_text(json.dumps(contacts, indent=2, ensure_ascii=False), encoding="utf-8")


def add_contact(
    name: str,
    email: str = "",
    phone: str = "",
    notes: str = "",
) -> str:
    """Add or update a contact."""
    contacts = _load_contacts()

    # Check for existing contact
    existing = next((c for c in contacts if c.get("name", "").lower() == name.lower()), None)
    if existing:
        if email:
            existing["email"] = email
        if phone:
            existing["phone"] = phone
        if notes:
            existing["notes"] = notes
        existing["updated_at"] = datetime.now().isoformat()
        _save_contacts(contacts)
        return f"Updated contact: {name}."

    contact = {
        "name": name,
        "email": email,
        "phone": phone,
        "notes": notes,
        "created_at": datetime.now().isoformat(),
    }
    contacts.append(contact)
    _save_contacts(contacts)
    log.info("Contact added: %s", name)
    return f"Added contact: {name}."


def find_contact(query: str) -> str:
    """Search contacts by name, email, or phone (fuzzy match)."""
    contacts = _load_contacts()
    q = query.lower()

    matches = []
    for c in contacts:
        searchable = " ".join([
            c.get("name", ""),
            c.get("email", ""),
            c.get("phone", ""),
            c.get("notes", ""),
        ]).lower()
        if q in searchable:
            matches.append(c)

    if not matches:
        return f"No contacts found matching '{query}'."

    lines = [f"Found {len(matches)} contact(s):"]
    for c in matches:
        parts = [c.get("name", "Unknown")]
        if c.get("email"):
            parts.append(f"📧 {c['email']}")
        if c.get("phone"):
            parts.append(f"📱 {c['phone']}")
        if c.get("notes"):
            parts.append(f"({c['notes'][:50]})")
        lines.append("  • " + " — ".join(parts))

    return "\n".join(lines)


def list_contacts() -> str:
    """List all contacts."""
    contacts = _load_contacts()
    if not contacts:
        return "No contacts saved yet."

    lines = [f"Your contacts ({len(contacts)} total):"]
    for c in sorted(contacts, key=lambda x: x.get("name", "").lower()):
        info = c.get("name", "Unknown")
        if c.get("email"):
            info += f" — {c['email']}"
        lines.append(f"  • {info}")

    return "\n".join(lines)


def delete_contact(name: str) -> str:
    """Delete a contact by name."""
    contacts = _load_contacts()
    q = name.lower()
    remaining = [c for c in contacts if c.get("name", "").lower() != q]
    removed = len(contacts) - len(remaining)

    if removed == 0:
        return f"No contact found named '{name}'."

    _save_contacts(remaining)
    return f"Deleted contact: {name}."


def get_email_for_name(name: str) -> Optional[str]:
    """Look up an email address by contact name. Used for email auto-complete."""
    contacts = _load_contacts()
    q = name.lower()
    for c in contacts:
        if q in c.get("name", "").lower() and c.get("email"):
            return c["email"]
    return None
