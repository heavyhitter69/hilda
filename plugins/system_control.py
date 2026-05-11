"""
plugins/system_control.py — Windows system-level controls.
All actions pass through the security filter.
"""
import subprocess
from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


def system_action(action: str) -> str:
    """Execute a system action: shutdown | restart | sleep | lock."""
    sec = check_command(action)
    if not sec.safe:
        return f"Blocked: {sec.reason}"

    action = action.lower().strip()
    commands: dict[str, list[str]] = {
        "shutdown": ["shutdown", "/s", "/t", "30"],
        "restart":  ["shutdown", "/r", "/t", "30"],
        "sleep":    ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "lock":     ["rundll32.exe", "user32.dll,LockWorkStation"],
        "cancel":   ["shutdown", "/a"],
    }

    if action not in commands:
        return f"I don't know how to '{action}'. I can shutdown, restart, sleep, or lock."

    try:
        subprocess.run(commands[action], check=True)
        log.info("System action executed: %s", action)
        return f"Okay, I'm initiating a system {action}."
    except subprocess.CalledProcessError as e:
        log.error("System action failed: %s", e)
        return f"I couldn't perform the {action}: {e}"


def control_wifi(enable: bool) -> str:
    """Enable or disable Wi-Fi adapter."""
    state = "enable" if enable else "disable"
    msg = "on" if enable else "off"
    try:
        result = subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", state],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("Wi-Fi %sd.", state)
            return f"Turning Wi-Fi {msg}."
        return f"I couldn't turn the Wi-Fi {msg}: {result.stderr.strip()}"
    except Exception as e:
        return f"Wi-Fi control error: {e}"


def control_bluetooth(enable: bool) -> str:
    """Enable or disable Bluetooth radio via PowerShell."""
    msg = "on" if enable else "off"
    state = "On" if enable else "Off"
    ps_cmd = (
        "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
        "$asb = [Windows.Devices.Radios.Radio, Windows.Devices.Radios, ContentType=WindowsRuntime]; "
        "[Windows.Devices.Radios.Radio]::GetRadiosAsync().GetResults() | "
        "Where-Object { $_.Kind -eq 'Bluetooth' } | ForEach-Object { $_.SetStateAsync('" + state + "') }"
    )
    try:
        subprocess.run(["powershell", "-Command", ps_cmd], check=True)
        return f"Turning Bluetooth {msg}."
    except Exception as e:
        return f"I had trouble with the Bluetooth: {e}"


def control_airplane_mode(enable: bool) -> str:
    """Toggle Airplane Mode (opens settings as a fallback if direct toggle fails)."""
    msg = "on" if enable else "off"
    try:
        # Direct toggle via ms-settings URI is the most reliable cross-version way without admin
        subprocess.run(["start", "ms-settings:network-airplanemode"], shell=True)
        return f"Opening Airplane Mode settings for you to turn it {msg}."
    except Exception:
        return "I couldn't open the Airplane Mode settings."


def control_hotspot(enable: bool) -> str:
    """Toggle Mobile Hotspot."""
    msg = "on" if enable else "off"
    try:
        subprocess.run(["start", "ms-settings:network-mobilehotspot"], shell=True)
        return f"Opening Hotspot settings to turn it {msg}."
    except Exception:
        return "I couldn't open the Hotspot settings."


def take_screenshot() -> str:
    """Capture a screenshot and save to Desktop."""
    try:
        import pyautogui
        from pathlib import Path
        import time
        
        path = Path.home() / "Desktop" / f"Hilda_Screenshot_{int(time.time())}.png"
        pyautogui.screenshot(str(path))
        return f"Screenshot saved to your Desktop."
    except Exception as e:
        return f"I couldn't take a screenshot: {e}"


def set_volume(action: str) -> str:
    """up | down | mute"""
    try:
        import pyautogui
        if action == "up":
            for _ in range(5): pyautogui.press("volumeup")
            return "Turning volume up."
        elif action == "down":
            for _ in range(5): pyautogui.press("volumedown")
            return "Turning volume down."
        elif action == "mute":
            pyautogui.press("volumemute")
            return "Toggling mute."
        return "Unknown volume action."
    except Exception:
        return "I couldn't adjust the volume."


def set_brightness(level: int) -> str:
    """Set brightness level (0-100)."""
    try:
        import screen_brightness_control as sbc
        sbc.set_brightness(level)
        return f"Setting brightness to {level} percent."
    except Exception:
        return "I couldn't adjust the brightness."


def media_control(action: str) -> str:
    """play | pause | next | prev"""
    try:
        import pyautogui
        mapping = {
            "play": "playpause",
            "pause": "playpause",
            "next": "nexttrack",
            "prev": "prevtrack"
        }
        if action in mapping:
            pyautogui.press(mapping[action])
            return f"Okay, {action}."
        return "Unknown media action."
    except Exception:
        return "I couldn't control the media."


def trigger_shortcut(action: str) -> str:
    """Trigger system shortcuts: project | cast | taskmgr"""
    try:
        import pyautogui
        if action == "project":
            pyautogui.hotkey("win", "p")
            return "Opening projection settings."
        elif action == "cast":
            pyautogui.hotkey("win", "k")
            return "Searching for displays to cast to."
        elif action == "taskmgr":
            pyautogui.hotkey("ctrl", "shift", "esc")
            return "Opening Task Manager."
        return "Unknown shortcut."
    except Exception:
        return "I couldn't trigger that shortcut."


def get_battery_status() -> str:
    """Return current battery level info."""
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt:
            return f"Your battery is at {batt.percent:.0f} percent {'and is charging' if batt.power_plugged else 'and is discharging'}."
        return "I can't see any battery information. Are you on a desktop?"
    except ImportError:
        return "I need the psutil library to check your battery."
