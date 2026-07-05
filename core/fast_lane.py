"""
core/fast_lane.py — Deterministic desktop command routing (no LLM).

Maps common phrases directly to the underlying tool implementations
so simple actions avoid cloud/local LLM latency.
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _strip_assistant_prefix(text: str) -> str:
    t = text.strip()
    if not t:
        return t
    name = (settings.ASSISTANT_NAME or "Hilda").strip()
    low = t.lower()
    cand = [
        f"{name.lower()},",
        f"{name.lower()} ",
        f"hey {name.lower()},",
        f"hey {name.lower()} ",
        "computer,",
        "computer ",
    ]
    for p in cand:
        if low.startswith(p):
            return t[len(p) :].lstrip(", ").strip()
    return t


def _clean_target(s: str) -> str:
    s = s.strip()
    s = re.sub(r"[.!?]+$", "", s)
    s = re.sub(r"\b(the|a|an|please)\b", " ", s, flags=re.I)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _known_folder_path(key: str) -> Optional[Path]:
    key = key.lower().strip()
    home = Path.home()
    mapping: dict[str, list[Path]] = {
        "downloads": [home / "Downloads", home / "Descargas"],
        "desktop": [home / "Desktop", home / "Escritorio", home / "OneDrive" / "Desktop"],
        "documents": [home / "Documents", home / "Documentos", home / "OneDrive" / "Documents"],
        "pictures": [home / "Pictures", home / "Imágenes", home / "OneDrive" / "Pictures"],
        "videos": [home / "Videos", home / "OneDrive" / "Videos"],
        "music": [home / "Music", home / "OneDrive" / "Music"],
        "home": [home],
    }
    for p in mapping.get(key, []):
        if p.exists():
            return p
    return None


def _looks_like_path(fragment: str) -> bool:
    f = fragment.strip()
    if not f:
        return False
    if ":" in f and ("\\" in f or "/" in f):
        return True
    if f.startswith(("~\\", "~/", "%", "\\\\")):
        return True
    if "/" in f or "\\" in f:
        return True
    if re.search(r"\.(pdf|docx?|txt|xlsx?|pptx?|png|jpe?g|gif|zip|rar|csv|md)\b", f, re.I):
        return True
    return False


def _resolve_path(fragment: str) -> Optional[str]:
    raw = fragment.strip().strip('"').strip("'")
    try:
        p = Path(raw).expanduser()
        if (
            not p.is_absolute()
            and not raw.startswith((".", "~"))
            and "\\" not in raw
            and "/" not in raw
            and ":" not in raw
        ):
            kf = _known_folder_path(raw)
            if kf is not None:
                p = kf
        if p.exists():
            return str(p.resolve())
    except OSError:
        pass
    return None


def _looks_like_url(fragment: str) -> bool:
    f = fragment.strip()
    if re.match(r"^https?://", f, re.I):
        return True
    if re.match(r"^www\.", f, re.I):
        return True
    if re.search(r"\b[a-z0-9-]+\.(com|org|net|io|edu|gov|dev|app)\b", f, re.I):
        return True
    return False


def try_dispatch(user_text: str) -> Optional[str]:
    """
    If the utterance is a simple desktop command, execute and return a result str.
    Return None to let the LangChain planner or LLM handle it.
    """
    if not getattr(settings, "USE_FAST_LANE", True):
        return None

    text = _strip_assistant_prefix(user_text)
    if not text.strip():
        return None

    low = text.lower()

    # ── PC diagnostics ─────────────────────────────────────────────────────
    if any(
        p in low
        for p in (
            "diagnose", "diagnostic", "health check", "pc health",
            "check my pc", "system report", "disk space", "memory usage",
            "cpu usage", "computer slow", "what's wrong with my pc",
        )
    ):
        from plugins.diagnostics import quick_pc_snapshot
        log.info("Fast lane: PC snapshot")
        return quick_pc_snapshot()

    # ── System actions ─────────────────────────────────────────────────────
    if re.match(r"^\s*lock(?:\s+(?:my\s+)?(?:pc|computer|screen|workstation|it))?\s*[.!?]?\s*$", low):
        from plugins.system_control import system_action
        return system_action("lock")
    if re.search(r"\bcancel\b\s+(?:the\s+)?(?:shutdown|restart)", low):
        from plugins.system_control import system_action
        return system_action("cancel")
    if "sleep" in low or "suspend" in low:
        from plugins.system_control import system_action
        return system_action("sleep")
    if "shutdown" in low or "turn off computer" in low or "power off" in low:
        from plugins.system_control import system_action
        return system_action("shutdown")
    if "restart" in low or "reboot" in low:
        from plugins.system_control import system_action
        return system_action("restart")

    # ── YouTube ─────────────────────────────────────────────────────────────
    yt_match = re.search(
        r"(youtube|on youtube)(?:\s+for)?\s+(.+)$|search\s+youtube\s+for\s+(.+)$|^play\s+(.+)\s+on\s+youtube",
        low,
    )
    if yt_match:
        q = next((g for g in yt_match.groups() if g), None)
        if q:
            topic = _clean_target(q)
            from plugins.browser_control import search_youtube_sync
            log.info("Fast lane: YouTube")
            return search_youtube_sync(topic)

    # ── Google search ───────────────────────────────────────────────────────
    g_match = re.search(
        r"(?:google|search\s+google)(?:\s+for)?\s+(.+)$|look\s+up\s+(.+)\s+on\s+google",
        low,
    )
    if g_match:
        q = next((g for g in g_match.groups() if g), None)
        if q:
            query = _clean_target(q)
            from plugins.browser_control import open_url_sync
            url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
            log.info("Fast lane: Google")
            return open_url_sync(url)

    # ── Open URL / navigate ─────────────────────────────────────────────────
    nav_match = re.search(
        r"\b(navigate|go)\s+to\s+(.+)$|\bopen\s+(?:the\s+)?(?:website|site|link)\s+(.+)$",
        text, re.I,
    )
    if nav_match:
        target = next((g for g in nav_match.groups() if g), None)
        if target:
            frag = _clean_target(target)
            if _looks_like_url(frag):
                from plugins.browser_control import open_url_sync
                return open_url_sync(frag)

    # ── Find files ───────────────────────────────────────────────────────────
    find_match = re.search(
        r"\b(find|search\s+for)\s+(?:a\s+)?(?:file\s+)?(?:named\s+|called\s+)?(.+)$",
        low,
    )
    if find_match:
        q = _clean_target(find_match.group(2))
        if len(q) > 1:
            from plugins.file_search import search_files
            log.info("Fast lane: file search")
            return search_files(q, str(Path.home()))

    open_file_match = re.search(r"\b(open|launch)\s+(?:my\s+)?(?:the\s+)?file\s+(.+)$", low)
    if open_file_match:
        q = _clean_target(open_file_match.group(2))
        if q:
            from plugins.file_search import search_and_open
            return search_and_open(q, str(Path.home()))

    # ── Close app ───────────────────────────────────────────────────────────
    close_match = re.search(r"\b(close|quit|exit|kill)\s+(?:the\s+)?(.+)$", low)
    if close_match:
        target = _clean_target(close_match.group(2))
        target = re.sub(r"\b(app|application|program)\b", "", target, flags=re.I).strip()
        if target:
            from plugins.app_control import close_application
            log.info("Fast lane: close")
            return close_application(target)

    # ── Type / paste ─────────────────────────────────────────────────────────
    paste_match = re.search(r"\bpaste\b\s*[:\s]+\s*(.+)$", text, re.I | re.DOTALL)
    if paste_match:
        body = paste_match.group(1).strip()
        if body:
            from plugins.mouse_keyboard import paste_text
            return paste_text(body)

    type_match = re.search(r"(?im)^\s*type\s+(?!of\s)(\S.*)$", text)
    if type_match:
        typed = type_match.group(1).strip()
        if typed:
            if len(typed) > 160 or "\n" in typed:
                from plugins.mouse_keyboard import paste_text
                return paste_text(typed)
            from plugins.mouse_keyboard import type_text
            log.info("Fast lane: keyboard type")
            return type_text(typed)

    # ── Scroll ───────────────────────────────────────────────────────────────
    scroll_m = re.match(r"^\s*scroll\s+(up|down)(?:\s+(\d+))?\s*$", low)
    if scroll_m:
        direction = scroll_m.group(1)
        n = int(scroll_m.group(2)) if scroll_m.group(2) else 3
        clicks = n if direction == "up" else -n
        from plugins.mouse_keyboard import scroll
        return scroll(clicks)

    # ── Open / launch / start ───────────────────────────────────────────────
    launch_match = re.match(
        r"(?im)^\s*(open|launch|start|show)\s+(?:the\s+|my\s+|this\s+)?(?:folder\s+)?(.+)\s*$",
        text.strip(),
    )
    if launch_match:
        raw_target = launch_match.group(2).strip()
        tgt_norm = raw_target.lower()

        folder_m = re.match(r"(?im)^folder\s+(.+)$", raw_target.strip())
        if folder_m:
            inner = folder_m.group(1).strip()
            kf = _known_folder_path(inner)
            if kf:
                from plugins.file_search import open_file
                return open_file(str(kf))
            resolved = _resolve_path(inner)
            if resolved:
                from plugins.file_search import open_file
                return open_file(resolved)

        resolved = _resolve_path(raw_target)
        if resolved:
            from plugins.file_search import open_file
            log.info("Fast lane: resolved path")
            return open_file(resolved)

        if _looks_like_path(raw_target):
            pth = Path(raw_target).expanduser()
            try:
                if pth.exists():
                    from plugins.file_search import open_file
                    return open_file(str(pth.resolve()))
            except OSError:
                pass

        if _looks_like_url(raw_target):
            from plugins.browser_control import open_url_sync
            return open_url_sync(raw_target)

        kf = _known_folder_path(tgt_norm)
        if kf:
            from plugins.file_search import open_file
            return open_file(str(kf))

        appish = _clean_target(raw_target)
        if any(ext in appish.lower() for ext in (".pdf", ".doc", ".docx", ".txt", ".xlsx", ".ppt", ".png", ".jpg", ".jpeg", ".csv", ".zip")):
            from plugins.file_search import search_and_open
            return search_and_open(appish, str(Path.home()))

        from plugins.app_control import open_application
        log.info("Fast lane: open app %s", appish[:40])
        return open_application(appish)

    # ── Hardware Toggles ───────────────────────────────────────────────────
    hw_match = re.search(r"\b(turn\s+)?(on|off|enable|disable)\s+(wifi|wi-fi|bluetooth|airplane\s+mode|hotspot)\b", low)
    if hw_match:
        state = hw_match.group(2) in ("on", "enable")
        target = hw_match.group(3).replace("wi-fi", "wifi").replace("airplane mode", "airplane")
        log.info("Fast lane: toggle %s to %s", target, state)
        from plugins.system_control import control_wifi, control_bluetooth
        if target == "wifi": return control_wifi(state)
        if target == "bluetooth": return control_bluetooth(state)

    # ── Volume & Media ─────────────────────────────────────────────────────
    if "volume up" in low or "increase volume" in low:
        from plugins.system_control import set_volume
        return set_volume("up")
    if "volume down" in low or "decrease volume" in low:
        from plugins.system_control import set_volume
        return set_volume("down")
    if "unmute" in low:
        from plugins.system_control import set_volume
        return set_volume("unmute")
    if "mute" in low:
        from plugins.system_control import set_volume
        return set_volume("mute")
    
    media_match = re.search(r"\b(play|pause|next|previous|prev)\s+(music|song|video|track|media)?\b", low)
    if media_match:
        act = media_match.group(1).replace("previous", "prev")
        from plugins.system_control import media_control
        return media_control(act)

    # ── Brightness ─────────────────────────────────────────────────────────
    bright_match = re.search(r"\b(set|change|put)\s+brightness\s+(to\s+)?(\d+)\b", low)
    if bright_match:
        lvl = int(bright_match.group(3))
        from plugins.system_control import set_brightness
        return set_brightness(lvl)

    # ── Screenshot ─────────────────────────────────────────────────────────
    if any(p in low for p in ("screenshot", "take a snap", "capture screen")):
        from plugins.system_control import take_screenshot
        return take_screenshot()

    # ── System Shortcuts ───────────────────────────────────────────────────
    if "project" in low or "projection" in low:
        from plugins.system_control import trigger_shortcut
        return trigger_shortcut("project")
    if "cast" in low or "screen mirror" in low:
        from plugins.system_control import trigger_shortcut
        return trigger_shortcut("cast")
    if "task manager" in low or "taskmgr" in low:
        from plugins.system_control import trigger_shortcut
        return trigger_shortcut("taskmgr")

    # ── Battery ────────────────────────────────────────────────────────────
    if any(p in low for p in ("battery", "power level", "charging")):
        from plugins.system_control import get_battery_status
        return get_battery_status()

    # ── Time & Date ────────────────────────────────────────────────────────
    if any(p in low for p in ("what time is it", "current time", "what's the time")):
        from plugins.info_control import get_current_time
        return get_current_time()
    if any(p in low for p in ("what's the date", "what is the date", "today's date", "todays date")):
        from plugins.info_control import get_current_date
        return get_current_date()

    # ── Reminders & Timers (Basic) ─────────────────────────────────────────
    rem_match = re.search(r"remind\s+me\s+to\s+(.+)\s+in\s+(\d+)\s+minutes?", low)
    if rem_match:
        msg = rem_match.group(1)
        mins = int(rem_match.group(2))
        from plugins.reminder_control import add_reminder
        return add_reminder(msg, str(mins))

    timer_match = re.search(r"set\s+(?:a\s+)?timer\s+for\s+(\d+)\s+(seconds?|minutes?)", low)
    if timer_match:
        val = int(timer_match.group(1))
        unit = timer_match.group(2)
        secs = val * 60 if unit.startswith("min") else val
        from plugins.timer_control import set_timer
        return set_timer(secs, f"Timer for {val} {unit}")

    # ── Miscellaneous ──────────────────────────────────────────────────────
    if any(p in low for p in ("empty", "clear")) and any(p in low for p in ("trash", "recycle bin", "bin")):
        from plugins.system_control import empty_recycle_bin
        return empty_recycle_bin()

    if any(p in low for p in ("system info", "pc info", "computer info", "specs", "specifications")):
        from plugins.system_control import get_detailed_system_info
        return get_detailed_system_info()

    return None
