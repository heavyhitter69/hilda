"""
plugins/app_control.py — Open and close Windows applications.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)

# Map friendly names → executable names
APP_MAP: dict[str, str] = {
    "notepad":    "notepad.exe",
    "chrome":     "chrome.exe",
    "firefox":    "firefox.exe",
    "edge":       "msedge.exe",
    "vscode":     "code.exe",
    "vs code":    "code.exe",
    "explorer":   "explorer.exe",
    "calculator": "calc.exe",
    "paint":      "mspaint.exe",
    "word":       "WINWORD.EXE",
    "excel":      "EXCEL.EXE",
    "powershell": "powershell.exe",
    "terminal":   "wt.exe",
    "spotify":    "Spotify.exe",
    "discord":    "Discord.exe",
    "slack":      "slack.exe",
    "zoom":       "Zoom.exe",
    "obs":        "obs64.exe",
}


_BANNED_USER_FILE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".bmp",
    ".svg",
    ".ico",
}


@dataclass(frozen=True)
class _Candidate:
    kind: str  # "lnk" | "exe" | "uwp" | "path"
    value: str
    score: int


def _norm(s: str) -> str:
    return " ".join((s or "").lower().replace("_", " ").split()).strip()


def _score_name(query: str, label: str) -> int:
    """
    Higher is better. Prefer exact match, then prefix, then substring.
    """
    q = _norm(query)
    l = _norm(label)
    if not q or not l:
        return 0
    if q == l:
        return 100
    if l.startswith(q):
        return 80
    if q in l:
        return 60
    return 0


def _iter_start_menu_dirs() -> Iterable[Path]:
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    if appdata:
        yield Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if programdata:
        yield Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


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
                label = lnk.stem
                sc = _score_name(q, label)
                if sc <= 0:
                    continue
                cand = _Candidate(kind="lnk", value=str(lnk), score=sc + 30)
                if best is None or cand.score > best.score:
                    best = cand
        except Exception:
            continue
    return best


def _find_uwp_startapp(query: str) -> Optional[_Candidate]:
    """
    Resolve installed Start Menu/UWP apps using PowerShell Get-StartApps.
    If found, return an AppsFolder launch target like:
      shell:AppsFolder\\<AppID>
    """
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
            capture_output=True,
            text=True,
            timeout=3,
        )
        out = (r.stdout or "").strip()
        if r.returncode == 0 and "||" in out:
            name, appid = out.split("||", 1)
            target = f"shell:AppsFolder\\{appid.strip()}"
            return _Candidate(kind="uwp", value=target, score=_score_name(q, name) + 40)
    except Exception:
        pass

    return None


def _find_common_install_exe(query: str) -> Optional[_Candidate]:
    """
    Shallow search in common install roots for an executable matching the query.
    Avoid a full disk walk.
    """
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
        cand = _Candidate(kind="exe", value=str(p), score=sc + 20)
        if best is None or cand.score > best.score:
            best = cand

    for root in roots:
        if not root.exists():
            continue
        try:
            for p in root.glob("*/*.exe"):
                if p.name.lower() in wanted:
                    return _Candidate(kind="exe", value=str(p), score=120)
                consider(p)
            for p in root.glob("*/*/*.exe"):
                if p.name.lower() in wanted:
                    return _Candidate(kind="exe", value=str(p), score=120)
                consider(p)
        except Exception:
            continue

    return best


def _resolve_app_target(name: str) -> str:
    """
    Resolve an "open <name>" request to the best launch target.
    Prefers apps (Start menu shortcuts, UWP AppIDs, executables) over user files.
    """
    raw = (name or "").strip().strip('"').strip("'")
    if not raw:
        return raw

    # If the user gave an explicit existing path, honor it.
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

    # Last resort: look in user folders, but avoid obvious images.
    base = Path.home()
    search_dirs = [
        base,
        base / "Documents",
        base / "Documentos",
        base / "Desktop",
        base / "Downloads",
        base / "OneDrive" / "Documents",
        base / "OneDrive" / "Documentos",
        base / "OneDrive" / "Desktop",
    ]

    q = _norm(raw).replace(" folder", "").strip()
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
                if item.is_file() and item.suffix.lower() in _BANNED_USER_FILE_EXTS:
                    sc -= 100
                if item.is_dir():
                    sc += 10
                if item.is_file() and item.suffix.lower() in {".lnk", ".exe"}:
                    sc += 40
                if sc > best_score:
                    best_score = sc
                    best_path = item
        except Exception:
            continue

    if best_path is not None and best_score > 0:
        return str(best_path)

    return raw

def open_application(name: str) -> str:
    """Open an application by friendly name or executable name."""
    sec = check_command(name)
    if not sec.safe:
        return f"Blocked: {sec.reason}"

    target = _resolve_app_target(name)
            
    try:
        # Use 'start ""' to let the Windows shell properly open files, folders, or EXEs
        # without spaces in Paths breaking the command. 
        subprocess.Popen(f'start "" "{target}"', shell=True)
        log.info("Opened application: %s (%s)", name, target)
        return f"Opening {name}."
    except Exception as e:
        log.error("Failed to open %s: %s", name, e)
        return f"I couldn't open {name}: {e}"


def close_application(name: str) -> str:
    """Terminate a running process by name."""
    exe = APP_MAP.get(name.lower().strip(), name)
    if not exe.endswith(".exe"):
        exe += ".exe"
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/IM", exe],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("Closed application: %s", exe)
            return f"Closed {name}."
        return f"Couldn't close {name}: {result.stderr.strip()}"
    except Exception as e:
        log.error("taskkill failed for %s: %s", exe, e)
        return f"Error closing {name}: {e}"
