"""Read/write optional user_settings.json (offline prefs in WRITABLE_ROOT)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


def settings_path(base_dir: Path) -> Path:
    return base_dir / "user_settings.json"


def read_json(base_dir: Path) -> dict[str, Any]:
    path = settings_path(base_dir)
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def write_json(base_dir: Path, updates: dict[str, Any]) -> None:
    path = settings_path(base_dir)
    current = read_json(base_dir)
    current.update({k: v for k, v in updates.items() if v is not None})
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")


def get_tts_voice_hint(base_dir: Path) -> Optional[str]:
    hint = read_json(base_dir).get("tts_voice_hint")
    if hint is None:
        return None
    s = str(hint).strip()
    return s or None


def set_tts_voice_hint(base_dir: Path, hint: str) -> None:
    write_json(base_dir, {"tts_voice_hint": str(hint).strip()})


def get_user_display_name(writable_root: Path) -> str:
    """Fresh read each call — used after setup wizard updates JSON without restart."""
    env_name = (os.getenv("USER_DISPLAY_NAME") or "").strip()
    if env_name:
        return env_name
    name = str(read_json(writable_root).get("user_display_name") or "").strip()
    return name


def set_user_display_name(writable_root: Path, name: str) -> None:
    write_json(writable_root, {"user_display_name": str(name).strip()})
