"""
core/fast_lane.py — Deterministic desktop command routing (no LLM).

Maps common phrases directly to the same tool implementations used by the
LangChain planner so simple actions avoid cloud/local LLM latency.
"""
from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Any, Callable, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_tool_open_app: Optional[Callable[..., str]] = None
_tool_close_app: Optional[Callable[..., str]] = None
_tool_search_youtube: Optional[Callable[..., str]] = None
_tool_type_text: Optional[Callable[..., str]] = None
_tool_paste_text: Optional[Callable[..., str]] = None
_tool_file_search: Optional[Callable[..., str]] = None
_tool_open_path: Optional[Callable[..., str]] = None
_tool_search_and_open_file: Optional[Callable[..., str]] = None
_tool_system_action: Optional[Callable[..., str]] = None
_tool_run_powershell: Optional[Callable[..., str]] = None
_tool_dictate_and_enter: Optional[Callable[..., str]] = None
_tool_scroll: Optional[Callable[..., str]] = None
_tool_quick_pc_snapshot: Optional[Callable[[], str]] = None


def _bind_tools() -> None:
    global _tool_open_app, _tool_close_app, _tool_search_youtube
    global _tool_type_text, _tool_paste_text, _tool_file_search, _tool_open_path
    global _tool_search_and_open_file, _tool_system_action, _tool_run_powershell
    global _tool_dictate_and_enter, _tool_scroll, _tool_quick_pc_snapshot
    if _tool_open_app is not None:
        return
    from core import planner as p
    from plugins.diagnostics import quick_pc_snapshot

    _tool_open_app = p.tool_open_app
    _tool_close_app = p.tool_close_app
    _tool_search_youtube = p.tool_search_youtube
    _tool_type_text = p.tool_type_text
    _tool_paste_text = p.tool_paste_text
    _tool_file_search = p.tool_file_search
    _tool_open_path = p.tool_open_path
    _tool_search_and_open_file = p.tool_search_and_open_file
    _tool_system_action = p.tool_system_action
    _tool_run_powershell = p.tool_run_powershell
    _tool_dictate_and_enter = p.tool_dictate_and_enter
    _tool_scroll = p.tool_scroll
    _tool_quick_pc_snapshot = quick_pc_snapshot


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
    if not settings.USE_FAST_LANE:
        return None

    _bind_tools()
    fn: Any
    text = _strip_assistant_prefix(user_text)
    if not text.strip():
        return None

    low = text.lower()

    # ── Dictation ──────────────────────────────────────────────────────────
    if any(
        p in low
        for p in (
            "dictate",
            "voice type",
            "type what i say",
            "write what i say",
            "start dictation",
            "dictation mode",
        )
    ):
        log.info("Fast lane: dictation")
        return _tool_dictate_and_enter("paste")

    # ── PC diagnostics ─────────────────────────────────────────────────────
    if any(
        p in low
        for p in (
            "diagnose",
            "diagnostic",
            "health check",
            "pc health",
            "check my pc",
            "system report",
            "disk space",
            "memory usage",
            "cpu usage",
            "computer slow",
            "what's wrong with my pc",
            "whats wrong with my pc",
        )
    ):
        log.info("Fast lane: PC snapshot")
        return _tool_quick_pc_snapshot()

    # ── System actions ─────────────────────────────────────────────────────
    if re.match(
        r"^\s*lock(?:\s+(?:my\s+)?(?:pc|computer|screen|workstation|it))?\s*[.!?]?\s*$",
        low,
    ):
        return _tool_system_action("lock")
    if re.search(r"\bcancel\b\s+(?:the\s+)?(?:shutdown|restart)", low):
        return _tool_system_action("cancel")
    if "sleep" in low or "suspend" in low:
        return _tool_system_action("sleep")
    if "shutdown" in low or "turn off computer" in low or "power off" in low:
        return _tool_system_action("shutdown")
    if "restart" in low or "reboot" in low:
        return _tool_system_action("restart")

    # ── PowerShell one-liner ────────────────────────────────────────────────
    if low.startswith("run ") or (low.startswith("powershell") and len(low) > 12):
        cmd = re.sub(r"^\s*run\s+", "", text, flags=re.I).strip()
        cmd = re.sub(r"^\s*(in\s+)?powershell[,:]?\s*", "", cmd, flags=re.I).strip()
        if cmd:
            log.info("Fast lane: powershell")
            return _tool_run_powershell(cmd)

    # ── YouTube ─────────────────────────────────────────────────────────────
    yt_match = re.search(
        r"(youtube|on youtube)(?:\s+for)?\s+(.+)$|search\s+youtube\s+for\s+(.+)$|^play\s+(.+)\s+on\s+youtube",
        low,
    )
    if yt_match:
        q = next((g for g in yt_match.groups() if g), None)
        if q:
            topic = _clean_target(q)
            log.info("Fast lane: YouTube")
            return _tool_search_youtube(topic)

    # ── Google search ───────────────────────────────────────────────────────
    g_match = re.search(
        r"(?:google|search\s+google)(?:\s+for)?\s+(.+)$|look\s+up\s+(.+)\s+on\s+google",
        low,
    )
    if g_match:
        q = next((g for g in g_match.groups() if g), None)
        if q:
            query = _clean_target(q)
            from plugins.browser_control import open_url_default_browser

            url = "https://www.google.com/search?q=" + urllib.parse.quote(query)
            log.info("Fast lane: Google")
            return open_url_default_browser(url)

    # ── Open URL / navigate ─────────────────────────────────────────────────
    nav_match = re.search(
        r"\b(navigate|go)\s+to\s+(.+)$|\bopen\s+(?:the\s+)?(?:website|site|link)\s+(.+)$",
        text,
        re.I,
    )
    if nav_match:
        target = next((g for g in nav_match.groups() if g), None)
        if target:
            frag = _clean_target(target)
            if _looks_like_url(frag):
                from plugins.browser_control import open_url_default_browser

                return open_url_default_browser(frag)

    # ── Find files ───────────────────────────────────────────────────────────
    find_match = re.search(
        r"\b(find|search\s+for)\s+(?:a\s+)?(?:file\s+)?(?:named\s+|called\s+)?(.+)$",
        low,
    )
    if find_match:
        q = _clean_target(find_match.group(2))
        if len(q) > 1:
            log.info("Fast lane: file search")
            return _tool_file_search(q, str(Path.home()))

    open_file_match = re.search(r"\b(open|launch)\s+(?:my\s+)?(?:the\s+)?file\s+(.+)$", low)
    if open_file_match:
        q = _clean_target(open_file_match.group(2))
        if q:
            return _tool_search_and_open_file(q, str(Path.home()))

    # ── Close app ───────────────────────────────────────────────────────────
    close_match = re.search(r"\b(close|quit|exit|kill)\s+(?:the\s+)?(.+)$", low)
    if close_match:
        target = _clean_target(close_match.group(2))
        target = re.sub(r"\b(app|application|program)\b", "", target, flags=re.I).strip()
        if target:
            log.info("Fast lane: close")
            return _tool_close_app(target)

    # ── Type / paste ─────────────────────────────────────────────────────────
    paste_match = re.search(r"\bpaste\b\s*[:\s]+\s*(.+)$", text, re.I | re.DOTALL)
    if paste_match:
        body = paste_match.group(1).strip()
        if body:
            return _tool_paste_text(body)

    type_match = re.search(r"(?im)^\s*type\s+(?!of\s)(\S.*)$", text)
    if type_match:
        typed = type_match.group(1).strip()
        if typed:
            if len(typed) > 160 or "\n" in typed:
                return _tool_paste_text(typed)
            log.info("Fast lane: keyboard type")
            return _tool_type_text(typed)

    # ── Scroll ───────────────────────────────────────────────────────────────
    scroll_m = re.match(r"^\s*scroll\s+(up|down)(?:\s+(\d+))?\s*$", low)
    if scroll_m:
        direction = scroll_m.group(1)
        n = int(scroll_m.group(2)) if scroll_m.group(2) else 3
        clicks = n if direction == "up" else -n
        return _tool_scroll(clicks)

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
                return _tool_open_path(str(kf))
            resolved = _resolve_path(inner)
            if resolved:
                return _tool_open_path(resolved)

        resolved = _resolve_path(raw_target)
        if resolved:
            log.info("Fast lane: resolved path")
            return _tool_open_path(resolved)

        if _looks_like_path(raw_target):
            pth = Path(raw_target).expanduser()
            try:
                if pth.exists():
                    return _tool_open_path(str(pth.resolve()))
            except OSError:
                pass

        if _looks_like_url(raw_target):
            from plugins.browser_control import open_url_default_browser

            return open_url_default_browser(raw_target)

        kf = _known_folder_path(tgt_norm)
        if kf:
            return _tool_open_path(str(kf))

        appish = _clean_target(raw_target)
        if any(
            ext in appish.lower()
            for ext in (
                ".pdf",
                ".doc",
                ".docx",
                ".txt",
                ".xlsx",
                ".ppt",
                ".png",
                ".jpg",
                ".jpeg",
                ".csv",
                ".zip",
            )
        ):
            return _tool_search_and_open_file(appish, str(Path.home()))

        log.info("Fast lane: open app %s", appish[:40])
        return _tool_open_app(appish)

    return None
