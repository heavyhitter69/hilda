"""
plugins/system_control.py — Thin delegation layer over the OS adapter.

All platform-specific logic has moved to adapters/windows|macos|linux/adapter.py.
This file remains the public interface that planner.py and fast_lane.py call.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from adapters import adapter
from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


# ── Power ─────────────────────────────────────────────────────────────────────

def system_action(action: str) -> str:
    """Execute a system action: shutdown | restart | sleep | lock | cancel."""
    sec = check_command(action)
    if not sec.safe:
        return f"Blocked: {sec.reason}"

    dispatch = {
        "shutdown": adapter.shutdown,
        "restart":  adapter.restart,
        "sleep":    adapter.sleep,
        "lock":     adapter.lock,
        "cancel":   adapter.cancel_shutdown,
    }
    fn = dispatch.get(action.lower().strip())
    if fn is None:
        return f"I don't know how to '{action}'."
    try:
        return fn()
    except Exception as e:
        log.error("system_action '%s' failed: %s", action, e)
        return f"I couldn't perform the {action}: {e}"


# ── Network ───────────────────────────────────────────────────────────────────

def control_wifi(enable: bool) -> str:
    """Enable or disable Wi-Fi adapter."""
    try:
        return adapter.set_wifi(enable)
    except Exception as e:
        log.error("control_wifi failed: %s", e)
        return f"I couldn't control Wi-Fi: {e}"


def control_bluetooth(enable: bool) -> str:
    """Enable or disable Bluetooth radio."""
    try:
        return adapter.set_bluetooth(enable)
    except Exception as e:
        log.error("control_bluetooth failed: %s", e)
        return f"I couldn't control Bluetooth: {e}"


def control_airplane_mode(enable: bool) -> str:
    """Toggle Airplane Mode (opens settings — direct toggle requires admin)."""
    import subprocess, sys
    msg = "on" if enable else "off"
    try:
        if sys.platform == "win32":
            subprocess.run(["start", "ms-settings:network-airplanemode"], shell=True)
            return f"Opening Airplane Mode settings to turn it {msg}."
        return f"Airplane Mode settings is Windows-only. Please toggle manually."
    except Exception:
        return "I couldn't open the Airplane Mode settings."


def control_hotspot(enable: bool) -> str:
    """Toggle Mobile Hotspot settings."""
    import subprocess, sys
    msg = "on" if enable else "off"
    try:
        if sys.platform == "win32":
            subprocess.run(["start", "ms-settings:network-mobilehotspot"], shell=True)
            return f"Opening Hotspot settings to turn it {msg}."
        return "Hotspot settings is Windows-only. Please toggle manually."
    except Exception:
        return "I couldn't open the Hotspot settings."


# ── Volume ────────────────────────────────────────────────────────────────────

def set_volume(action: str, level: Optional[int] = None) -> str:
    """
    Stateful volume control.
    action: up | down | mute | unmute | set
    level:  0-100, used only when action='set'
    """
    try:
        if action == "set" and level is not None:
            return adapter.set_volume(level)

        if action == "up":
            current = adapter.get_volume()
            new_level = min(100, (current if current >= 0 else 50) + 10)
            return adapter.set_volume(new_level)

        if action == "down":
            current = adapter.get_volume()
            new_level = max(0, (current if current >= 0 else 50) - 10)
            return adapter.set_volume(new_level)

        if action == "mute":
            return adapter.set_muted(True)

        if action == "unmute":
            return adapter.set_muted(False)

        return f"Unknown volume action '{action}'."
    except Exception as e:
        log.error("set_volume failed: %s", e)
        return "I couldn't adjust the volume."


def get_volume() -> int:
    """Return current volume level (0-100), or -1 if unavailable."""
    try:
        return adapter.get_volume()
    except Exception:
        return -1


# ── Media ─────────────────────────────────────────────────────────────────────

def media_control(action: str) -> str:
    """play | pause | next | prev"""
    try:
        if action in ("play", "pause"):
            return adapter.media_play_pause()
        if action == "next":
            return adapter.media_next()
        if action in ("prev", "previous"):
            return adapter.media_prev()
        return f"Unknown media action '{action}'."
    except Exception as e:
        log.error("media_control failed: %s", e)
        return "I couldn't control the media."


# ── Display & peripherals ─────────────────────────────────────────────────────

def set_brightness(level: int) -> str:
    """Set display brightness (0-100)."""
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"Brightness set to {level} percent."
    except Exception as e:
        log.error("set_brightness failed: %s", e)
        return "I couldn't adjust the brightness."


def take_screenshot() -> str:
    """Capture a screenshot and save to Desktop."""
    try:
        import pyautogui, time
        from pathlib import Path
        path = Path.home() / "Desktop" / f"Hilda_Screenshot_{int(time.time())}.png"
        pyautogui.screenshot(str(path))
        return "Screenshot saved to your Desktop."
    except Exception as e:
        log.error("take_screenshot failed: %s", e)
        return f"I couldn't take a screenshot: {e}"


def trigger_shortcut(action: str) -> str:
    """Trigger system shortcuts: project | cast | taskmgr"""
    try:
        import pyautogui
        mapping = {
            "project": ("win", "p"),
            "cast":    ("win", "k"),
            "taskmgr": ("ctrl", "shift", "esc"),
        }
        keys = mapping.get(action)
        if keys:
            pyautogui.hotkey(*keys)
            labels = {"project": "projection settings", "cast": "cast menu", "taskmgr": "Task Manager"}
            return f"Opening {labels.get(action, action)}."
        return f"Unknown shortcut '{action}'."
    except Exception as e:
        log.error("trigger_shortcut failed: %s", e)
        return "I couldn't trigger that shortcut."


# ── System info ───────────────────────────────────────────────────────────────

def get_battery_status() -> str:
    """Return current battery level and charging state."""
    return adapter.get_battery_status()


def get_detailed_system_info() -> str:
    """Return OS, CPU, and RAM info."""
    return adapter.get_system_info()


def empty_recycle_bin() -> str:
    """Empty the system recycle bin / trash."""
    return adapter.empty_trash()
