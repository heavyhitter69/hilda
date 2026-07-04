"""
adapters/__init__.py — OS adapter factory.

Imports the correct platform adapter at startup and exposes it as `adapter`.
All plugin files import from here:

    from adapters import adapter
    adapter.set_volume(50)
"""
from __future__ import annotations

import sys

from adapters.base import SystemAdapterBase  # noqa: F401 — re-exported for type hints

if sys.platform == "win32":
    from adapters.windows.adapter import WindowsAdapter as _AdapterClass
elif sys.platform == "darwin":
    from adapters.macos.adapter import MacAdapter as _AdapterClass  # type: ignore[assignment]
else:
    from adapters.linux.adapter import LinuxAdapter as _AdapterClass  # type: ignore[assignment]

# Singleton instance used by all plugins
adapter: SystemAdapterBase = _AdapterClass()  # type: ignore[assignment]

__all__ = ["adapter", "SystemAdapterBase"]
