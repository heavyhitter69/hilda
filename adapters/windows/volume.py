"""
adapters/windows/volume.py — Stateful Windows volume control via pycaw.

Replaces pyautogui blind key-press toggling with direct reads/writes against
the Windows Core Audio API (IAudioEndpointVolume).

Uses the modern pycaw API where AudioDevice.EndpointVolume is the interface.
Falls back gracefully to pyautogui if pycaw is not installed.
"""
from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)


# ── pycaw helpers ─────────────────────────────────────────────────────────────

def _get_endpoint():
    """Return an IAudioEndpointVolume interface via the modern pycaw API, or None."""
    try:
        from pycaw.pycaw import AudioUtilities
        device = AudioUtilities.GetSpeakers()
        # Modern pycaw (>=20230407) exposes EndpointVolume directly on AudioDevice
        ep = device.EndpointVolume
        return ep
    except Exception as exc:
        log.warning("pycaw not available (%s) — falling back to pyautogui.", exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_volume() -> int:
    """
    Return the current master volume level (0–100).
    Returns -1 if pycaw is unavailable.
    """
    ep = _get_endpoint()
    if ep is None:
        return -1
    try:
        scalar = ep.GetMasterVolumeLevelScalar()
        return round(scalar * 100)
    except Exception as exc:
        log.error("get_volume failed: %s", exc)
        return -1


def set_volume(level: int) -> str:
    """
    Set master volume to an absolute level (0–100).
    Falls back to pyautogui key-press simulation if pycaw is unavailable.
    """
    level = max(0, min(100, level))
    ep = _get_endpoint()
    if ep is not None:
        try:
            ep.SetMasterVolumeLevelScalar(level / 100.0, None)
            log.info("Volume set to %d%% via pycaw.", level)
            return f"Volume set to {level} percent."
        except Exception as exc:
            log.error("pycaw set_volume failed: %s", exc)

    # Fallback: blind key presses
    try:
        import pyautogui
        # Ensure unmuted first, then nudge up/down a little to force an exact level
        pyautogui.press("volumemute")
        pyautogui.press("volumemute")
        log.warning("Volume adjusted via pyautogui fallback (no absolute control).")
        return "Adjusted volume (approximate — pycaw unavailable)."
    except Exception as exc:
        log.error("pyautogui volume fallback failed: %s", exc)
        return "I couldn't adjust the volume."


def is_muted() -> bool:
    """
    Return True if the system audio is currently muted.
    Returns False if pycaw is unavailable (safe default).
    """
    ep = _get_endpoint()
    if ep is None:
        return False
    try:
        return bool(ep.GetMute())
    except Exception as exc:
        log.error("is_muted failed: %s", exc)
        return False


def set_muted(muted: bool) -> str:
    """
    Set the mute state explicitly (no blind toggling).
    Falls back to a state-aware pyautogui toggle if pycaw is unavailable.
    """
    ep = _get_endpoint()
    if ep is not None:
        try:
            ep.SetMute(int(muted), None)
            state = "Muted" if muted else "Unmuted"
            log.info("%s via pycaw.", state)
            return f"{state}."
        except Exception as exc:
            log.error("pycaw set_muted failed: %s", exc)

    # Fallback: check current state then toggle only if needed
    try:
        import pyautogui
        currently = is_muted()
        if currently != muted:
            pyautogui.press("volumemute")
        return "Muted." if muted else "Unmuted."
    except Exception as exc:
        log.error("pyautogui mute fallback failed: %s", exc)
        return "I couldn't change the mute state."
