"""
vision/screen_capture.py — Continuous screen capture using MSS.
"""
import threading
import time
from typing import Callable, Optional

import mss
from PIL import Image

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def capture_fullscreen() -> Image.Image:
    """Grab the primary monitor and return a PIL Image."""
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # primary monitor
        shot = sct.grab(monitor)
        return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")


class ScreenCaptureLoop:
    """
    Background thread that captures the screen at a set FPS
    and calls a callback with each PIL Image.
    """

    def __init__(self, on_frame: Callable[[Image.Image], None]) -> None:
        self._on_frame = on_frame
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
            name="screen-capture",
        )
        self._thread.start()
        log.info("ScreenCaptureLoop started at %d FPS.", settings.SCREEN_CAPTURE_FPS)

    def _loop(self) -> None:
        interval = 1.0 / max(settings.SCREEN_CAPTURE_FPS, 1)
        while not self._stop.is_set():
            try:
                frame = capture_fullscreen()
                self._on_frame(frame)
            except Exception as e:
                log.error("Screen capture error: %s", e)
            time.sleep(interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        log.info("ScreenCaptureLoop stopped.")
