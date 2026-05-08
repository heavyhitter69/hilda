"""
voice/audio_manager.py — Coordinates the full voice pipeline.

Flow:
  WakeWordDetector fires → optional greeting TTS → record audio → STT → agent → TTS
"""
import asyncio
import os
import threading
from typing import Optional

from config.settings import settings
from config.user_settings_file import get_user_display_name
from core.logger import get_logger
from voice.wake_word import WakeWordDetector

log = get_logger(__name__)


def _greeting_line() -> str:
    """Personalised line after wake word, before listening for a command."""
    name = get_user_display_name(settings.WRITABLE_ROOT).strip()
    if not name:
        try:
            name = (os.getenv("USERNAME") or os.getenv("USER") or "").strip()
        except Exception:
            name = ""
    if name:
        return f"Hi {name}, how may I help you?"
    return "Hi, how may I help you?"


class AudioManager:
    """
    Manages the end-to-end voice interaction lifecycle.
    Must be started after the asyncio event loop is running.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._active = False
        self._detector: Optional[WakeWordDetector] = None

    def _on_wake(self) -> None:
        """Called by WakeWordDetector (background thread) when wake word heard."""
        if self._active:
            return
        self._active = True
        asyncio.run_coroutine_threadsafe(self._handle_voice(), self._loop)

    async def _handle_voice(self) -> None:
        """Async: greeting → record → transcribe → agent → TTS."""
        from core import websocket_server
        from voice.speech_to_text import listen_and_transcribe
        from voice.text_to_speech import speak
        from core.agent import get_agent

        loop = asyncio.get_event_loop()

        try:
            greeting = _greeting_line()
            log.info("Post-wake greeting: %s", greeting)
            await websocket_server.broadcast_state("speaking")
            await websocket_server.broadcast_message("assistant", greeting)
            await loop.run_in_executor(None, speak, greeting)

            await websocket_server.broadcast_state("listening")
            log.info("Listening for user speech…")

            text = await loop.run_in_executor(None, listen_and_transcribe)

            if not text.strip():
                log.info("No speech detected after wake.")
                await websocket_server.broadcast_message(
                    "assistant",
                    "I didn't catch that — say it again, or type your request.",
                )
                await websocket_server.broadcast_state("idle")
                return

            agent = get_agent()
            await agent.handle_text(text)

        except Exception as e:
            log.error("Voice pipeline error: %s", e)
            from core import websocket_server as ws

            await ws.broadcast_state("idle")
        finally:
            self._active = False

    def start(self) -> None:
        """Start the wake word detector."""
        self._detector = WakeWordDetector(on_wake=self._on_wake)
        self._detector.start()
        log.info("AudioManager started — waiting for wake word.")

    def stop(self) -> None:
        """Shutdown the wake word detector."""
        if self._detector:
            self._detector.stop()
        log.info("AudioManager stopped.")

    def pause_mic(self) -> None:
        """Temporarily stop the wake detector so enrollment can use the mic."""
        if self._detector:
            log.info("AudioManager: pausing wake detector for mic hand-off.")
            self._detector.stop()

    def resume_mic(self) -> None:
        """Restart the wake detector after enrollment releases the mic."""
        if self._detector:
            log.info("AudioManager: resuming wake detector.")
            self._detector.start()


_instance: Optional["AudioManager"] = None


def get_audio_manager() -> Optional["AudioManager"]:
    return _instance


def set_audio_manager(mgr: "AudioManager") -> None:
    global _instance
    _instance = mgr
