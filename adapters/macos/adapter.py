"""
adapters/macos/adapter.py — macOS concrete implementation of SystemAdapterBase.
Uses osascript for system control and networksetup for Wi-Fi.
"""
from __future__ import annotations

import platform
import subprocess
from pathlib import Path

from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


def _osa(script: str, timeout: int = 5) -> str:
    try:
        r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception as e:
        log.error("osascript error: %s", e)
        return ""


class MacAdapter:

    def get_volume(self) -> int:
        out = _osa("output volume of (get volume settings)")
        try:
            return int(out)
        except ValueError:
            return -1

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        _osa(f"set volume output volume {level}")
        return f"Volume set to {level} percent."

    def is_muted(self) -> bool:
        return _osa("output muted of (get volume settings)").lower() == "true"

    def set_muted(self, muted: bool) -> str:
        _osa(f"set volume output muted {'true' if muted else 'false'}")
        return "Muted." if muted else "Unmuted."

    def shutdown(self) -> str:
        _osa('tell app "System Events" to shut down')
        return "Shutting down."

    def restart(self) -> str:
        _osa('tell app "System Events" to restart')
        return "Restarting."

    def sleep(self) -> str:
        _osa('tell app "System Events" to sleep')
        return "Going to sleep."

    def lock(self) -> str:
        try:
            subprocess.run(
                ["/System/Library/CoreServices/Menu Extras/User.menu/Contents/Resources/CGSession", "-suspend"],
                check=True,
            )
            return "Screen locked."
        except Exception as e:
            return f"I couldn't lock the screen: {e}"

    def cancel_shutdown(self) -> str:
        return "Shutdown cancellation is not supported on macOS."

    def set_wifi(self, enable: bool) -> str:
        state = "on" if enable else "off"
        try:
            subprocess.run(["networksetup", "-setnetworkserviceenabled", "Wi-Fi", state], check=True)
            return f"Wi-Fi turned {state}."
        except Exception as e:
            return f"I couldn't turn Wi-Fi {state}: {e}"

    def set_bluetooth(self, enable: bool) -> str:
        import shutil
        state = "on" if enable else "off"
        if not shutil.which("blueutil"):
            return "blueutil is not installed. Run: brew install blueutil"
        try:
            subprocess.run(["blueutil", "-p", "1" if enable else "0"], check=True)
            return f"Bluetooth turned {state}."
        except Exception as e:
            return f"I couldn't turn Bluetooth {state}: {e}"

    def open_app(self, name: str) -> str:
        sec = check_command(name)
        if not sec.safe:
            return f"Blocked: {sec.reason}"
        try:
            p = Path(name).expanduser()
            if p.exists():
                subprocess.Popen(["open", str(p)])
            else:
                subprocess.Popen(["open", "-a", name])
            return f"Opening {name}."
        except Exception as e:
            return f"I couldn't open {name}: {e}"

    def close_app(self, name: str) -> str:
        try:
            result = subprocess.run(["pkill", "-f", name], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Closed {name}."
            return f"Couldn't find a running process for '{name}'."
        except Exception as e:
            return f"Error closing {name}: {e}"

    def media_play_pause(self) -> str:
        try:
            import pyautogui; pyautogui.press("playpause"); return "Toggled playback."
        except Exception:
            return "I couldn't control the media."

    def media_next(self) -> str:
        try:
            import pyautogui; pyautogui.press("nexttrack"); return "Next track."
        except Exception:
            return "I couldn't skip the track."

    def media_prev(self) -> str:
        try:
            import pyautogui; pyautogui.press("prevtrack"); return "Previous track."
        except Exception:
            return "I couldn't go back."

    def get_system_info(self) -> str:
        try:
            import psutil
            r = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True)
            cpu_name = r.stdout.strip() or platform.processor()
            mem = psutil.virtual_memory()
            total_ram = round(mem.total / (1024 ** 3), 2)
            return f"OS: macOS {platform.mac_ver()[0]}\nCPU: {cpu_name}\nRAM: {total_ram} GB"
        except Exception as e:
            return f"I couldn't retrieve system info: {e}"

    def get_battery_status(self) -> str:
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt:
                charging = "charging" if batt.power_plugged else "discharging"
                return f"Battery at {batt.percent:.0f}% and {charging}."
            return "No battery detected."
        except Exception:
            return "I couldn't read the battery status."

    def empty_trash(self) -> str:
        try:
            subprocess.run(["osascript", "-e", 'tell app "Finder" to empty trash'], check=True)
            return "Trash emptied."
        except Exception as e:
            return f"I couldn't empty the trash: {e}"
