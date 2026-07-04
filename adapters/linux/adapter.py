"""
adapters/linux/adapter.py — Linux concrete implementation of SystemAdapterBase.
Uses systemctl, pactl/nmcli/rfkill, and xdg-open.
Assumes PipeWire/PulseAudio and systemd.
"""
from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path

from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


def _run(cmd: list[str], timeout: int = 5) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


class LinuxAdapter:

    # ── Volume ────────────────────────────────────────────────────────────────

    def get_volume(self) -> int:
        try:
            r = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
            m = re.search(r"(\d+)%", r.stdout)
            return int(m.group(1)) if m else -1
        except Exception:
            return -1

    def set_volume(self, level: int) -> str:
        level = max(0, min(100, level))
        try:
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{level}%"], check=True)
            return f"Volume set to {level} percent."
        except Exception as e:
            return f"I couldn't set volume: {e}"

    def is_muted(self) -> bool:
        try:
            r = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
            return "yes" in r.stdout.lower()
        except Exception:
            return False

    def set_muted(self, muted: bool) -> str:
        try:
            val = "1" if muted else "0"
            subprocess.run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", val], check=True)
            return "Muted." if muted else "Unmuted."
        except Exception as e:
            return f"I couldn't change the mute state: {e}"

    # ── Power ─────────────────────────────────────────────────────────────────

    def shutdown(self) -> str:
        try:
            subprocess.run(["systemctl", "poweroff"], check=True)
            return "Shutting down."
        except Exception as e:
            return f"I couldn't shutdown: {e}"

    def restart(self) -> str:
        try:
            subprocess.run(["systemctl", "reboot"], check=True)
            return "Restarting."
        except Exception as e:
            return f"I couldn't restart: {e}"

    def sleep(self) -> str:
        try:
            subprocess.run(["systemctl", "suspend"], check=True)
            return "Going to sleep."
        except Exception as e:
            return f"I couldn't suspend: {e}"

    def lock(self) -> str:
        import shutil
        for cmd in (["loginctl", "lock-session"], ["xdg-screensaver", "lock"]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, check=True)
                    return "Screen locked."
                except Exception:
                    continue
        return "I couldn't lock the screen. No supported lock command found."

    def cancel_shutdown(self) -> str:
        try:
            subprocess.run(["systemctl", "cancel"], check=True)
            return "Shutdown cancelled."
        except Exception as e:
            return f"I couldn't cancel the shutdown: {e}"

    # ── Network ───────────────────────────────────────────────────────────────

    def set_wifi(self, enable: bool) -> str:
        state = "on" if enable else "off"
        try:
            subprocess.run(["nmcli", "radio", "wifi", state], check=True)
            return f"Wi-Fi turned {state}."
        except Exception as e:
            return f"I couldn't turn Wi-Fi {state}: {e}"

    def set_bluetooth(self, enable: bool) -> str:
        state = "on" if enable else "off"
        try:
            subprocess.run(["rfkill", "unblock" if enable else "block", "bluetooth"], check=True)
            return f"Bluetooth turned {state}."
        except Exception as e:
            return f"I couldn't turn Bluetooth {state}: {e}"

    # ── Application control ───────────────────────────────────────────────────

    def open_app(self, name: str) -> str:
        import shutil
        sec = check_command(name)
        if not sec.safe:
            return f"Blocked: {sec.reason}"
        try:
            p = Path(name).expanduser()
            if p.exists():
                subprocess.Popen(["xdg-open", str(p)])
                return f"Opening {name}."
            gtk_launch = shutil.which("gtk-launch")
            if gtk_launch:
                subprocess.Popen([gtk_launch, name])
            else:
                subprocess.Popen([name])
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

    # ── Media ─────────────────────────────────────────────────────────────────

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

    # ── System information ────────────────────────────────────────────────────

    def get_system_info(self) -> str:
        try:
            import psutil
            r = _run(["grep", "model name", "/proc/cpuinfo"])
            lines = r.stdout.splitlines()
            cpu_name = lines[0].split(":", 1)[1].strip() if lines else platform.processor()
            mem = psutil.virtual_memory()
            total_ram = round(mem.total / (1024 ** 3), 2)
            return (
                f"OS: {platform.system()} {platform.release()}\n"
                f"CPU: {cpu_name}\n"
                f"RAM: {total_ram} GB"
            )
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
            subprocess.run("rm -rf ~/.local/share/Trash/*", shell=True, check=True)
            return "Trash emptied."
        except Exception as e:
            return f"I couldn't empty the trash: {e}"
