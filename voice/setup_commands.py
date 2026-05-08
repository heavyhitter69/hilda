"""
Setup wizard helpers (blocking) — invoked from websocket_server via thread pool.

Lists Windows/pyttsx3 voices, previews, saves user's choice to user_settings.json,
and captures a practice utterance via Whisper for the mic-check step.
"""
from __future__ import annotations

from typing import Any

import pyttsx3

from config.settings import settings
from config.user_settings_file import set_tts_voice_hint, set_user_display_name
from voice.enrollment_data import ENROLLMENT_PHRASES
from voice.enrollment_store import (
    append_phrase_take,
    build_whisper_initial_prompt,
    enrollment_dir,
    load_enrollment,
    write_wav,
)
from core.logger import get_logger
from voice.speech_to_text import listen_and_transcribe, record_until_silence, transcribe
from voice.text_to_speech import preview_voice_sample, set_active_voice_hint

log = get_logger(__name__)


def hint_for_voice_display_name(name: str) -> str:
    """Produce a substring that matches pyttsx3 voices via `hint in v.name.lower()`."""
    n = (name or "").split("|")[0].strip()
    if " - " in n:
        n = n.split(" - ")[0].strip()
    low = n.lower().strip()
    return low[:120] if low else "zira"


def list_voices() -> list[dict[str, Any]]:
    eng = pyttsx3.init()
    voices = eng.getProperty("voices") or []
    base_voices = [{"id": v.id, "name": (v.name or "").strip()} for v in voices]
    
    premium_aliases = [
        {"alias": "Nova", "desc": "Calm · Mid-range Voice"},
        {"alias": "Ursa", "desc": "Engaged · Mid-range Voice"},
        {"alias": "Vega", "desc": "Bright · High-pitch Voice"},
        {"alias": "Orion", "desc": "Deep · Low-pitch Voice"},
    ]
    
    results = []
    for i, p in enumerate(premium_aliases):
        base = base_voices[i % len(base_voices)] if base_voices else {"id": "default", "name": "default"}
        results.append({
            "id": f"{base['id']}||{p['alias']}",
            "name": p["alias"],
            "desc": p["desc"],
            "baseName": base["name"]
        })
    return results


def save_selected_voice(voice_id: str) -> dict[str, Any]:
    for v in list_voices():
        if v["id"] == voice_id:
            hint = hint_for_voice_display_name(v.get("baseName", v["name"]))
            set_tts_voice_hint(settings.WRITABLE_ROOT, hint)
            set_active_voice_hint(hint)
            log.info("Setup saved TTS voice hint: %s", hint[:60])
            return {"ok": True, "hint": hint, "voiceName": v["name"]}
    raise ValueError("Unknown voice")


def list_enrollment_phrases() -> dict[str, Any]:
    by_id = {
        str(p.get("id") or ""): p
        for p in (load_enrollment().get("phrases") or [])
        if p.get("id")
    }
    phrases = []
    for p in ENROLLMENT_PHRASES:
        rec = by_id.get(p["id"])
        tr = (rec or {}).get("transcript") or ""
        phrases.append(
            {
                "id": p["id"],
                "prompt": p["prompt"],
                "hint": p["hint"],
                "recorded": rec is not None,
                "transcript": tr,
            }
        )
    return {"ok": True, "phrases": phrases}


def save_enrollment_phrase(phrase_id: str) -> dict[str, Any]:
    from voice.audio_manager import get_audio_manager
    phrase = next((x for x in ENROLLMENT_PHRASES if x["id"] == phrase_id), None)
    if not phrase:
        raise ValueError("unknown phrase_id")
    mgr = get_audio_manager()
    try:
        if mgr:
            mgr.pause_mic()
        import time; time.sleep(0.4)  # let sounddevice fully release
        pcm = record_until_silence()
    finally:
        if mgr:
            mgr.resume_mic()
    rel_wav = f"clips/{phrase_id}.wav"
    clip = enrollment_dir() / rel_wav
    write_wav(clip, pcm)
    prompt = build_whisper_initial_prompt()
    text = transcribe(pcm, initial_prompt=prompt or None)
    append_phrase_take(phrase_id, phrase["prompt"], text, rel_wav)
    log.info("Enrollment phrase %s transcript=%s", phrase_id, text[:60])
    return {"ok": True, "transcript": text, "target": phrase["prompt"]}


def transcribe_voice_check() -> dict[str, Any]:
    """Blocking: record once (silence-terminated) then Whisper."""
    text = listen_and_transcribe().strip()
    return {"ok": True, "transcript": text}


async def run_setup_action(action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Async wrapper executing blocking setup work on the default executor."""
    import asyncio

    loop = asyncio.get_event_loop()
    try:
        if action == "list_voices":
            voices = await loop.run_in_executor(None, list_voices)
            return {"ok": True, "voices": voices}
        if action == "preview_voice":
            vid = str(payload.get("voice_id") or "")
            if "||" in vid:
                vid = vid.split("||")[0]
            phrase = payload.get("phrase")

            def _pv() -> None:
                preview_voice_sample(vid, phrase if isinstance(phrase, str) else None)

            await loop.run_in_executor(None, _pv)
            return {"ok": True}
        if action == "save_voice":
            vid = str(payload.get("voice_id") or "")
            return await loop.run_in_executor(None, save_selected_voice, vid)
        if action == "practice_transcribe":
            return await loop.run_in_executor(None, transcribe_voice_check)
        if action == "save_display_name":
            nm = str(payload.get("display_name") or "").strip()
            if not nm:
                return {"ok": False, "error": "empty name"}
            await loop.run_in_executor(None, lambda: set_user_display_name(settings.WRITABLE_ROOT, nm))
            return {"ok": True}
        if action == "list_enrollment_phrases":
            return list_enrollment_phrases()
        if action == "enrollment_record":
            pid = str(payload.get("phrase_id") or "").strip()
            return await loop.run_in_executor(None, save_enrollment_phrase, pid)
        if action == "env_info":
            return {
                "ok": True,
                "assistantName": settings.ASSISTANT_NAME,
                "wakeEngine": getattr(settings, "WAKE_ENGINE", "whisper_phrase"),
                "wakeKeyword": settings.PORCUPINE_KEYWORD
                if not (settings.PORCUPINE_KEYWORD_PATH or "").strip()
                else "custom_wake_model",
                "hasPorcupineKey": bool(settings.PORCUPINE_ACCESS_KEY.strip()),
            }
        return {"ok": False, "error": f"unknown action: {action}"}
    except Exception as e:
        log.exception("setup action failed")
        return {"ok": False, "error": str(e)}
