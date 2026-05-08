"""Persist voice enrollment metadata under WRITABLE_ROOT/enrollment/."""
from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def enrollment_dir() -> Path:
    d = settings.WRITABLE_ROOT / "enrollment"
    d.mkdir(parents=True, exist_ok=True)
    return d


def enrollment_json_path() -> Path:
    return enrollment_dir() / "enrollment.json"


def load_enrollment() -> dict[str, Any]:
    p = enrollment_json_path()
    if not p.is_file():
        return {"version": 1, "phrases": []}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {"version": 1, "phrases": []}
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "phrases": []}


def save_enrollment(data: dict[str, Any]) -> None:
    enrollment_dir()
    enrollment_json_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def append_phrase_take(
    phrase_id: str,
    target_prompt: str,
    transcript: str,
    wav_relative: str,
) -> None:
    data = load_enrollment()
    phrases = list(data.get("phrases") or [])
    # Replace existing entry for same id
    phrases = [p for p in phrases if p.get("id") != phrase_id]
    phrases.append(
        {
            "id": phrase_id,
            "target": target_prompt,
            "transcript": transcript.strip(),
            "wav": wav_relative,
        }
    )
    data["phrases"] = phrases
    data["version"] = 1
    save_enrollment(data)
    log.info("Enrollment saved for phrase_id=%s", phrase_id)


def write_wav(path: Path, pcm: bytes, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)


def build_whisper_initial_prompt(max_chars: int = 1800) -> str:
    """
    Concatenate enrollment transcripts so Whisper biases toward this user’s voice/accent.
    """
    from config.user_settings_file import get_user_display_name

    data = load_enrollment()
    bits: list[str] = []
    name = get_user_display_name(settings.WRITABLE_ROOT).strip()
    if name:
        bits.append(f"The user's name is {name}. The assistant is named Hilda.")
    else:
        bits.append("The assistant is named Hilda.")

    for p in data.get("phrases") or []:
        t = str(p.get("transcript") or "").strip()
        tgt = str(p.get("target") or "").strip()
        if t:
            bits.append(t)
        elif tgt:
            bits.append(tgt)

    out = " ".join(bits).strip()
    if len(out) > max_chars:
        out = out[:max_chars]
    return out


def enrollment_completion_ratio() -> tuple[int, int]:
    """Return (completed_count, total_prompts)."""
    from voice.enrollment_data import ENROLLMENT_PHRASES

    done = {p["id"] for p in load_enrollment().get("phrases") or []}
    total = len(ENROLLMENT_PHRASES)
    n = sum(1 for x in ENROLLMENT_PHRASES if x["id"] in done)
    return n, total
