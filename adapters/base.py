"""
adapters/base.py — Abstract protocol that every OS adapter must implement.

All methods are synchronous; async callers should wrap them in
asyncio.to_thread() when calling from an event loop.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SystemAdapterBase(Protocol):
    """
    Defines the complete OS-level contract for Hilda.
    Each platform (Windows / macOS / Linux) supplies a concrete class.
    """

    # ── Volume ────────────────────────────────────────────────────────────────

    def get_volume(self) -> int:
        """Return the current master volume level (0–100)."""
        ...

    def set_volume(self, level: int) -> str:
        """Set master volume to an absolute level (0–100)."""
        ...

    def is_muted(self) -> bool:
        """Return True if the audio output is currently muted."""
        ...

    def set_muted(self, muted: bool) -> str:
        """Mute or unmute the audio output."""
        ...

    # ── Power management ─────────────────────────────────────────────────────

    def shutdown(self) -> str:
        """Initiate a graceful system shutdown."""
        ...

    def restart(self) -> str:
        """Initiate a system restart."""
        ...

    def sleep(self) -> str:
        """Put the system to sleep / suspend."""
        ...

    def lock(self) -> str:
        """Lock the workstation / screen."""
        ...

    def cancel_shutdown(self) -> str:
        """Cancel a pending shutdown or restart (where supported)."""
        ...

    # ── Network ───────────────────────────────────────────────────────────────

    def set_wifi(self, enable: bool) -> str:
        """Enable or disable the Wi-Fi adapter."""
        ...

    def set_bluetooth(self, enable: bool) -> str:
        """Enable or disable the Bluetooth radio."""
        ...

    # ── Application control ───────────────────────────────────────────────────

    def open_app(self, name: str) -> str:
        """Open an application by friendly name or path."""
        ...

    def close_app(self, name: str) -> str:
        """Close / kill a running application by name."""
        ...

    # ── Media ─────────────────────────────────────────────────────────────────

    def media_play_pause(self) -> str:
        """Toggle media play/pause."""
        ...

    def media_next(self) -> str:
        """Skip to the next media track."""
        ...

    def media_prev(self) -> str:
        """Go back to the previous media track."""
        ...

    # ── System information ────────────────────────────────────────────────────

    def get_system_info(self) -> str:
        """Return a human-readable OS / CPU / RAM summary."""
        ...

    def get_battery_status(self) -> str:
        """Return battery level and charging state."""
        ...

    def empty_trash(self) -> str:
        """Empty the system recycle bin / trash."""
        ...
