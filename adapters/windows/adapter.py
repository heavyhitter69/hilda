"""
adapters/windows/adapter.py — Windows concrete implementation of SystemAdapterBase.

All OS-specific logic for Windows lives here; plugin files delegate to this class
instead of containing inline `if sys.platform == "win32"` blocks.
"""
from __future__ import annotations

import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


# ── Application name → executable map ────────────────────────────────────────

APP_MAP: dict[str, str] = {
    "notepad":       "notepad.exe",
    "chrome":        "chrome.exe",
    "firefox":       "firefox.exe",
    "edge":          "msedge.exe",
    "vscode":        "code.exe",
    "vs code":       "code.exe",
    "explorer":      "explorer.exe",
    "calculator":    "calc.exe",
    "paint":         "mspaint.exe",
    "word":          "WINWORD.EXE",
    "excel":         "EXCEL.EXE",
    "powershell":    "powershell.exe",
    "terminal":      "wt.exe",
    "spotify":       "Spotify.exe",
    "discord":       "Discord.exe",
    "slack":         "slack.exe",
    "zoom":          "Zoom.exe",
    "obs":           "obs64.exe",
    "steam":         "steam.exe",
    "epic":          "EpicGamesLauncher.exe",
    "battlenet":     "Battle.net.exe",
    "origin":        "Origin.exe",
    "uplay":         "upc.exe",
    "ubisoft":       "upc.exe",
    "photoshop":     "Photoshop.exe",
    "premiere":      "Premiere.exe",
    "after effects": "AfterFX.exe",
    "illustrator":   "Illustrator.exe",
    "blender":       "blender.exe",
    "postman":       "Postman.exe",
    "docker":        "Docker Desktop.exe",
    "vlc":           "vlc.exe",
    "handbrake":     "Handbrake.exe",
}

_BANNED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg", ".ico"}


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("_", " ").split()).strip()


def _score_name(query: str, label: str) -> int:
    q, l = _norm(query), _norm(label)
    if not q or not l:
        return 0
    if q == l:
        return 100
    if l.startswith(q):
        return 80
    if q in l:
        return 60
    return 0


# ── App resolution helpers ────────────────────────────────────────────────────

@dataclass(frozen=True)
class _Candidate:
    kind: str
    value: str
    score: int


def _iter_start_menu_dirs() -> Iterable[Path]:
    for env in ("APPDATA", "PROGRAMDATA"):
        v = os.environ.get(env)
        if v:
            yield Path(v) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def _find_start_menu_shortcut(query: str) -> Optional[_Candidate]:
    q = _norm(query)
    if not q:
        return None
    best: Optional[_Candidate] = None
    for root in _iter_start_menu_dirs():
        if not root.exists():
            continue
        try:
            for lnk in root.rglob("*.lnk"):
                sc = _score_name(q, lnk.stem)
                if sc <= 0:
                    continue
                cand = _Candidate("lnk", str(lnk), sc + 30)
                if best is None or cand.score > best.score:
                    best = cand
        except Exception:
            continue
    return best


def _find_uwp_startapp(query: str) -> Optional[_Candidate]:
    q = _norm(query)
    if not q:
        return None
    q_safe = q.replace('"', "")
    ps = f"""
$q = "{q_safe}"
$apps = Get-StartApps | Where-Object {{ $_.Name -and $_.AppID }} | ForEach-Object {{
  [PSCustomObject]@{{ Name = $_.Name; AppID = $_.AppID; NL = $_.Name.ToLower() }}
}}
$ql = $q.ToLower()
$best = $apps | Where-Object {{ $_.NL -like "*"+$ql+"*" }} | Sort-Object -Property @{{ Expression = {{
  if ($_.NL -eq $ql) {{ 0 }}
  elseif ($_.NL.StartsWith($ql)) {{ 1 }}
  else {{ 2 }}
}} }}, Name | Select-Object -First 1
if ($best) {{ Write-Output ($best.Name + "||" + $best.AppID) }}
""".strip()
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=3,
        )
        out = (r.stdout or "").strip()
        if r.returncode == 0 and "||" in out:
            name, appid = out.split("||", 1)
            target = f"shell:AppsFolder\\{appid.strip()}"
            return _Candidate("uwp", target, _score_name(q, name) + 40)
    except Exception:
        pass
    return None


def _find_common_install_exe(query: str) -> Optional[_Candidate]:
    q = _norm(query)
    if not q:
        return None
    roots: list[Path] = []
    for env in ("LOCALAPPDATA", "PROGRAMFILES", "PROGRAMFILES(X86)"):
        v = os.environ.get(env)
        if v:
            roots.append(Path(v))

    best: Optional[_Candidate] = None
    exe_name = q.replace(" ", "")
    exe_name2 = q.replace(" ", "-")
    wanted = {f"{exe_name}.exe", f"{exe_name2}.exe", f"{q}.exe"}

    def consider(p: Path) -> None:
        nonlocal best
        sc = _score_name(q, p.stem)
        if sc <= 0:
            return
        cand = _Candidate("exe", str(p), sc + 20)
        if best is None or cand.score > best.score:
            best = cand

    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.glob("*/*.exe"):
                if p.name.lower() in wanted:
                    return _Candidate("exe", str(p), 120)
                consider(p)
            for p in root.glob("*/*/*.exe"):
                if p.name.lower() in wanted:
                    return _Candidate("exe", str(p), 120)
                consider(p)
        except Exception:
            continue
    return best


def _resolve_app_target(name: str) -> str:
    raw = (name or "").strip().strip('"').strip("'")
    if not raw:
        return raw

    try:
        p = Path(raw).expanduser()
        if p.exists():
            return str(p)
    except OSError:
        pass

    mapped = APP_MAP.get(_norm(raw), raw)
    if mapped != raw:
        return mapped

    c1 = _find_start_menu_shortcut(raw)
    if c1:
        return c1.value

    c2 = _find_uwp_startapp(raw)
    if c2:
        return c2.value

    c3 = _find_common_install_exe(raw)
    if c3:
        return c3.value

    # Last resort: shallow search in user-facing folders
    home = Path.home()
    search_dirs = [
        home, home / "Desktop", home / "OneDrive" / "Desktop",
        home / "Documents", home / "Downloads",
    ]
    q = _norm(raw).replace(" folder", "").strip()
    is_folder_req = "folder" in _norm(raw)
    best_path: Optional[Path] = None
    best_score = -1

    for sdir in search_dirs:
        if not sdir.exists():
            continue
        try:
            for item in sdir.iterdir():
                sc = _score_name(q, item.name)
                if sc <= 0:
                    continue
                if item.is_file() and item.suffix.lower() in _BANNED_EXTS:
                    sc -= 500
                if item.is_dir():
                    sc += 200 if is_folder_req else -50
                if item.is_file() and item.suffix.lower() in {".lnk", ".exe", ".app"}:
                    sc += 200
                if sc > best_score and sc > 50:
                    best_score = sc
                    best_path = item
        except Exception:
            continue

    return str(best_path) if best_path is not None else raw


# ── WindowsAdapter ────────────────────────────────────────────────────────────

class WindowsAdapter:
    """Concrete Windows implementation of SystemAdapterBase."""

    # ── Volume ────────────────────────────────────────────────────────────────

    def get_volume(self) -> int:
        from adapters.windows.volume import get_volume
        return get_volume()

    def set_volume(self, level: int) -> str:
        from adapters.windows.volume import set_volume
        return set_volume(level)

    def is_muted(self) -> bool:
        from adapters.windows.volume import is_muted
        return is_muted()

    def set_muted(self, muted: bool) -> str:
        from adapters.windows.volume import set_muted
        return set_muted(muted)

    # ── Power ─────────────────────────────────────────────────────────────────

    def shutdown(self) -> str:
        try:
            subprocess.run(["shutdown", "/s", "/t", "30"], check=True)
            return "Okay, shutting down in 30 seconds."
        except Exception as e:
            return f"I couldn't initiate shutdown: {e}"

    def restart(self) -> str:
        try:
            subprocess.run(["shutdown", "/r", "/t", "30"], check=True)
            return "Restarting in 30 seconds."
        except Exception as e:
            return f"I couldn't initiate restart: {e}"

    def sleep(self) -> str:
        try:
            subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=True
            )
            return "Going to sleep."
        except Exception as e:
            return f"I couldn't put the PC to sleep: {e}"

    def lock(self) -> str:
        try:
            subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            return "Locked."
        except Exception as e:
            return f"I couldn't lock the screen: {e}"

    def cancel_shutdown(self) -> str:
        try:
            subprocess.run(["shutdown", "/a"], check=True)
            return "Shutdown cancelled."
        except Exception as e:
            return f"I couldn't cancel the shutdown: {e}"

    # ── Network ───────────────────────────────────────────────────────────────

    def set_wifi(self, enable: bool) -> str:
        act = "enable" if enable else "disable"
        state = "on" if enable else "off"
        try:
            subprocess.run(
                ["netsh", "interface", "set", "interface", "Wi-Fi", act], check=True
            )
            return f"Wi-Fi turned {state}."
        except Exception as e:
            return f"I couldn't turn Wi-Fi {state}: {e}"

    def set_bluetooth(self, enable: bool) -> str:
        state = "on" if enable else "off"
        ps_state = "On" if enable else "Off"
        ps_cmd = (
            "Add-Type -AssemblyName System.Runtime.WindowsRuntime; "
            "[Windows.Devices.Radios.Radio]::GetRadiosAsync().GetResults() | "
            "Where-Object { $_.Kind -eq 'Bluetooth' } | "
            f"ForEach-Object {{ $_.SetStateAsync('{ps_state}') }}"
        )
        try:
            subprocess.run(["powershell", "-Command", ps_cmd], check=True)
            return f"Bluetooth turned {state}."
        except Exception as e:
            return f"I couldn't turn Bluetooth {state}: {e}"

    # ── Application control ───────────────────────────────────────────────────

    def open_app(self, name: str) -> str:
        sec = check_command(name)
        if not sec.safe:
            return f"Blocked: {sec.reason}"
        target = _resolve_app_target(name)
        try:
            subprocess.Popen(f'start "" "{target}"', shell=True)
            log.info("Opened application: %s (%s)", name, target)
            return f"Opening {name}."
        except Exception as e:
            log.error("Failed to open %s: %s", name, e)
            return f"I couldn't open {name}: {e}"

    def close_app(self, name: str) -> str:
        exe = APP_MAP.get(_norm(name), name)
        if not exe.lower().endswith(".exe"):
            exe += ".exe"
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/IM", exe],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                log.info("Closed application: %s", exe)
                return f"Closed {name}."
            return f"Couldn't close {name}: {result.stderr.strip()}"
        except Exception as e:
            return f"Error closing {name}: {e}"

    # ── Media ─────────────────────────────────────────────────────────────────

    def media_play_pause(self) -> str:
        try:
            import pyautogui
            pyautogui.press("playpause")
            return "Toggled playback."
        except Exception:
            return "I couldn't control the media."

    def media_next(self) -> str:
        try:
            import pyautogui
            pyautogui.press("nexttrack")
            return "Next track."
        except Exception:
            return "I couldn't skip the track."

    def media_prev(self) -> str:
        try:
            import pyautogui
            pyautogui.press("prevtrack")
            return "Previous track."
        except Exception:
            return "I couldn't go back."

    # ── System information ────────────────────────────────────────────────────

    def get_system_info(self) -> str:
        try:
            import psutil
            os_info = f"{platform.system()} {platform.release()} ({platform.version()})"
            cpu_name = platform.processor()
            mem = psutil.virtual_memory()
            total_ram = round(mem.total / (1024 ** 3), 2)
            return f"OS: {os_info}\nCPU: {cpu_name}\nRAM: {total_ram} GB"
        except Exception as e:
            log.error("get_system_info failed: %s", e)
            return f"I couldn't retrieve system info: {e}"

    def get_battery_status(self) -> str:
        try:
            import psutil
            batt = psutil.sensors_battery()
            if batt:
                charging = "charging" if batt.power_plugged else "discharging"
                return f"Battery at {batt.percent:.0f}% and {charging}."
            return "No battery detected. You may be on a desktop."
        except Exception:
            return "I couldn't read the battery status."

    def empty_trash(self) -> str:
        try:
            subprocess.run(
                ["powershell", "-Command",
                 "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                check=True,
            )
            return "Recycle bin emptied."
        except Exception as e:
            log.error("empty_trash failed: %s", e)
            return f"I couldn't empty the recycle bin: {e}"
