"""
core/context_awareness.py — Real-time desktop context for Hilda.

Detects the user's active window, running apps, clipboard, and system state
so the LLM prompt can reference what the user is currently doing.
"""
from __future__ import annotations


import sys
import subprocess
from datetime import datetime


from core.logger import get_logger

log = get_logger(__name__)


# ── Active Window ─────────────────────────────────────────────────────────────

def get_active_window() -> dict[str, str]:
    """
    Return the currently focused window title and process name.
    Returns {"title": "...", "process": "..."} or empty strings on failure.
    """
    if sys.platform == "win32":
        return _get_active_window_windows()
    elif sys.platform == "darwin":
        return _get_active_window_macos()
    else:
        return _get_active_window_linux()


def _get_active_window_windows() -> dict[str, str]:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {"title": "", "process": ""}

        # Get window title
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value or ""

        # Get process name
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = ""
        try:
            import psutil
            proc = psutil.Process(pid.value)
            process_name = proc.name()
        except Exception:
            pass

        return {"title": title, "process": process_name}
    except Exception as e:
        log.debug("get_active_window failed: %s", e)
        return {"title": "", "process": ""}


def _get_active_window_macos() -> dict[str, str]:
    try:
        script = '''
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            set frontTitle to ""
            try
                tell process frontApp
                    set frontTitle to name of front window
                end tell
            end try
            return frontApp & "||" & frontTitle
        end tell
        '''
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and "||" in r.stdout:
            parts = r.stdout.strip().split("||", 1)
            return {"title": parts[1] if len(parts) > 1 else "", "process": parts[0]}
    except Exception as e:
        log.debug("get_active_window (macOS) failed: %s", e)
    return {"title": "", "process": ""}


def _get_active_window_linux() -> dict[str, str]:
    try:
        r = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3,
        )
        title = r.stdout.strip() if r.returncode == 0 else ""

        r2 = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowpid"],
            capture_output=True, text=True, timeout=3,
        )
        process_name = ""
        if r2.returncode == 0 and r2.stdout.strip():
            try:
                import psutil
                proc = psutil.Process(int(r2.stdout.strip()))
                process_name = proc.name()
            except Exception:
                pass
        return {"title": title, "process": process_name}
    except Exception as e:
        log.debug("get_active_window (Linux) failed: %s", e)
    return {"title": "", "process": ""}


# ── Clipboard ─────────────────────────────────────────────────────────────────

def get_clipboard_text(max_chars: int = 200) -> str:
    """Read the current clipboard text content, truncated."""
    try:
        if sys.platform == "win32":
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-Clipboard -Format Text -ErrorAction SilentlyContinue"],
                capture_output=True, text=True, timeout=3,
            )
            text = (r.stdout or "").strip()
        elif sys.platform == "darwin":
            r = subprocess.run(
                ["pbpaste"], capture_output=True, text=True, timeout=3,
            )
            text = (r.stdout or "").strip()
        else:
            r = subprocess.run(
                ["xclip", "-selection", "clipboard", "-o"],
                capture_output=True, text=True, timeout=3,
            )
            text = (r.stdout or "").strip()

        if len(text) > max_chars:
            return text[:max_chars] + "…"
        return text
    except Exception as e:
        log.debug("get_clipboard_text failed: %s", e)
        return ""


# ── Running Apps ──────────────────────────────────────────────────────────────

def get_running_apps() -> list[str]:
    """Return a deduplicated list of user-facing running application names."""
    try:
        import psutil
        skip = {
            "svchost.exe", "csrss.exe", "dwm.exe", "winlogon.exe",
            "services.exe", "smss.exe", "lsass.exe", "wininit.exe",
            "fontdrvhost.exe", "conhost.exe", "registry.exe",
            "system", "idle", "kernel_task", "launchd", "systemd",
            "loginwindow", "windowserver", "mdworker", "mds_stores",
            "spoolsv.exe", "taskhostw.exe", "sihost.exe",
            "runtimebroker.exe", "searchhost.exe", "startmenuexperiencehost.exe",
            "textinputhost.exe", "shellexperiencehost.exe",
            "securityhealthservice.exe", "sgrmbroker.exe",
            "ctfmon.exe", "dllhost.exe", "taskmgr.exe",
        }
        apps = set()
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").strip()
            if name and name.lower() not in skip and not name.startswith("_"):
                # Clean up common exe suffix for readability
                display = name.replace(".exe", "").replace(".app", "")
                if display and len(display) > 1:
                    apps.add(display)
        return sorted(apps)[:25]
    except Exception as e:
        log.debug("get_running_apps failed: %s", e)
        return []


# ── Battery ───────────────────────────────────────────────────────────────────

def get_battery_brief() -> str:
    """Short battery string for context injection."""
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt:
            status = "charging" if batt.power_plugged else "on battery"
            return f"{batt.percent:.0f}% ({status})"
    except Exception:
        pass
    return ""


# ── Full Snapshot ─────────────────────────────────────────────────────────────

def build_context_snapshot() -> dict:
    """
    Build a complete context snapshot of the user's desktop state.
    Used to inject into the LLM system prompt.
    """
    win = get_active_window()
    return {
        "active_window": win.get("title", ""),
        "active_app": win.get("process", ""),
        "clipboard_preview": get_clipboard_text(200),
        "running_apps": get_running_apps(),
        "time": datetime.now().strftime("%I:%M %p, %A"),
        "battery": get_battery_brief(),
    }
