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


def _run_porcupine_wake(on_wake: Callable[[], None], stop_event: threading.Event) -> None:
    import pvporcupine
    import sounddevice as sd
    import numpy as np

    access_key = settings.PORCUPINE_ACCESS_KEY
    if not access_key:
        log.warning("No PORCUPINE_ACCESS_KEY set. Falling back to whisper wake.")
        _run_whisper_wake(on_wake, stop_event)
        return

    keyword = getattr(settings, "PORCUPINE_KEYWORD", "computer")
    keyword_path = getattr(settings, "PORCUPINE_KEYWORD_PATH", "")

    try:
        if keyword_path:
            porcupine = pvporcupine.create(access_key=access_key, keyword_paths=[keyword_path])
        else:
            porcupine = pvporcupine.create(access_key=access_key, keywords=[keyword])
    except Exception as e:
        log.error("Failed to initialize Porcupine: %s", e)
        _run_whisper_wake(on_wake, stop_event)
        return

    log.info("Porcupine wake word detector started.")

    try:
        with sd.InputStream(samplerate=porcupine.sample_rate, blocksize=porcupine.frame_length,
                            dtype='int16', channels=1) as stream:
            while not stop_event.is_set():
                data, _ = stream.read(porcupine.frame_length)
                pcm = np.frombuffer(bytes(data), dtype=np.int16)
                result = porcupine.process(pcm)
                if result >= 0:
                    log.info("Porcupine wake word detected!")
                    on_wake()
    except Exception as e:
        log.error("Porcupine stream error: %s", e)
    finally:
        porcupine.delete()


def _dispatch(on_wake: Callable[[], None], stop_event: threading.Event) -> None:
    engine = getattr(settings, "WAKE_ENGINE", "whisper_phrase")
    if engine == "porcupine":
        _run_porcupine_wake(on_wake, stop_event)
    else:
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
