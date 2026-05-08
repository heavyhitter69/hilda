"""
Wake detection — uses Whisper phrase natively.
"""
import struct
import threading
from typing import Callable


from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_FRAME_LENGTH = 512
_SAMPLE_RATE = 16000





def _run_whisper_wake(on_wake: Callable[[], None], stop_event: threading.Event) -> None:
    from voice.wake_whisper import _run_whisper_wake_loop

    _run_whisper_wake_loop(on_wake, stop_event)


def _dispatch(on_wake: Callable[[], None], stop_event: threading.Event) -> None:
    _run_whisper_wake(on_wake, stop_event)


class WakeWordDetector:
    """Background thread for wake detection."""

    def __init__(self, on_wake: Callable[[], None]) -> None:
        self._on_wake = on_wake
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=_dispatch,
            args=(self._on_wake, self._stop),
            daemon=True,
            name="wake-word-detector",
        )
        self._thread.start()
        log.info("WakeWordDetector started (engine=whisper_phrase).")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        log.info("WakeWordDetector stopped.")
