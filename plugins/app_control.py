"""
plugins/app_control.py — Thin delegation layer over the OS adapter.

Application open/close logic has moved to adapters/windows|macos|linux/adapter.py.
This module exposes the same public API (open_application / close_application)
so fast_lane.py and planner.py require no changes.
"""
from __future__ import annotations

from adapters import adapter
from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


def open_application(name: str) -> str:
    """Open an application by friendly name, executable, or path."""
    sec = check_command(name)
    if not sec.safe:
        return f"Blocked: {sec.reason}"
    return adapter.open_app(name)


def close_application(name: str) -> str:
    """Close / kill a running application by name."""
    return adapter.close_app(name)
