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
        return f"Unknown action '{action}'. Use: shutdown, restart, sleep, lock, cancel."

    try:
        subprocess.run(commands[action], check=True)
        log.info("System action executed: %s", action)
        return f"System {action} initiated."
    except subprocess.CalledProcessError as e:
        log.error("System action failed: %s", e)
        return f"Failed to {action}: {e}"


def control_wifi(enable: bool) -> str:
    """Enable or disable Wi-Fi adapter."""
    state = "enable" if enable else "disable"
    try:
        result = subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", state],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("Wi-Fi %sd.", state)
            return f"Wi-Fi {state}d."
        return f"Wi-Fi {state} failed: {result.stderr.strip()}"
    except Exception as e:
        return f"Wi-Fi control error: {e}"


def get_battery_status() -> str:
    """Return current battery level info."""
    try:
        import psutil
        batt = psutil.sensors_battery()
        if batt:
            return f"Battery: {batt.percent:.0f}% {'(charging)' if batt.power_plugged else '(on battery)'}."
        return "No battery information available."
    except ImportError:
        return "psutil not installed; cannot read battery status."
