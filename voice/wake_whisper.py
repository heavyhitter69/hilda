"""
Whisper-based wake: listen for an utterance that names the assistant (e.g. Hey Hilda).

No Picovoice / .ppn required. CPU cost: energy-gated capture + one Whisper pass per
attempt. Pair with voice enrollment for better accent handling (initial_prompt).
"""
from __future__ import annotations

import re
import threading
import time
from typing import Callable

import numpy as np

from config.settings import settings
from core.logger import get_logger
from core.websocket_server import broadcast_state_from_thread
from voice.enrollment_store import build_whisper_initial_prompt
from voice.speech_to_text import record_next_utterance, transcribe

log = get_logger(__name__)


def _is_wake_utterance(text: str) -> bool:
    t = (text or "").lower()
    a = (settings.ASSISTANT_NAME or "hilda").lower()
    if a not in t and "hilda" not in t:
        return False
    # Greeting words or very short “Hilda” only
    if re.search(rf"\b(hey|hello|hi|ok|okay|yo)\b.*\b{re.escape(a)}\b", t):
        return True
    if re.search(rf"^\s*{re.escape(a)}\b", t) and len(t) < 40:
        return True
    if re.search(rf"\b{re.escape(a)}\b", t) and len(t) < 24:
        return True
    return False


def _run_whisper_wake_loop(on_wake: Callable[[], None], stop_event: threading.Event) -> None:
    log.info(
        "Whisper wake mode — say “Hey %s” (or similar). Enrolment improves accuracy.",
        settings.ASSISTANT_NAME,
    )
    cooldown_until = 0.0
    while not stop_event.is_set():
        if time.time() < cooldown_until:
            time.sleep(0.15)
            continue
        try:
            max_s = float(settings.WAKE_MAX_UTTERANCE_SECS)
            sil = float(settings.WAKE_SILENCE_SECS)
            pcm = record_next_utterance(
                max_secs=max_s,
                silence_secs=sil,
                speech_chunks_needed=2,
                on_speech_start=lambda: broadcast_state_from_thread("listening"),
            )
            if not pcm or len(pcm) < 8000:
                continue
            # Quick energy check: skip near-silent clips
            arr = np.frombuffer(pcm, dtype=np.int16)
            if float(np.max(np.abs(arr))) < 120:
                broadcast_state_from_thread("idle")
                continue
            broadcast_state_from_thread("thinking")
            prompt = build_whisper_initial_prompt()
            text = transcribe(pcm, initial_prompt=prompt or None)
            if _is_wake_utterance(text):
                log.info("Whisper wake matched: %s", text[:80])
                on_wake()
                cooldown_until = time.time() + float(settings.WAKE_COOLDOWN_SECS)
            else:
                broadcast_state_from_thread("idle")
        except Exception as e:
            if not stop_event.is_set():
                log.warning("Whisper wake loop error: %s", e)
            time.sleep(0.3)
