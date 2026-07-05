"""
plugins/plugin_loader.py — Extensible plugin system for Hilda.

Scans a user_plugins/ directory for Python files that define custom tools.
Each plugin file should define:
  PLUGIN_NAME: str
  PLUGIN_DESCRIPTION: str
  PLUGIN_TOOLS: list[StructuredTool]
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _plugins_dir() -> Path:
    """Return the user plugins directory, creating it if needed."""
    d = settings.WRITABLE_ROOT / "user_plugins"
    d.mkdir(parents=True, exist_ok=True)
    return d


def discover_plugins() -> list[dict[str, Any]]:
    """
    Scan the user_plugins directory and load any valid plugin files.

    Returns a list of plugin info dicts:
    [{"name": ..., "description": ..., "tools": [...], "path": ...}]
    """
    plugins_dir = _plugins_dir()
    discovered = []

    # Also create a README if it doesn't exist
    readme = plugins_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Hilda User Plugins\n\n"
            "Place Python plugin files here. Each file should define:\n\n"
            "```python\n"
            "from langchain_core.tools import StructuredTool\n\n"
            "PLUGIN_NAME = 'my_plugin'\n"
            "PLUGIN_DESCRIPTION = 'What my plugin does'\n"
            "PLUGIN_TOOLS = [\n"
            "    StructuredTool.from_function(...),\n"
            "]\n"
            "```\n\n"
            "See plugin_template.py in the plugins/ directory for a full example.\n",
            encoding="utf-8",
        )

    for py_file in plugins_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        try:
            plugin = _load_plugin_file(py_file)
            if plugin:
                discovered.append(plugin)
                log.info(
                    "Loaded plugin: %s (%d tools) from %s",
                    plugin["name"],
                    len(plugin["tools"]),
                    py_file.name,
                )
        except Exception as e:
            log.error("Failed to load plugin %s: %s", py_file.name, e)

    return discovered


def _load_plugin_file(path: Path) -> dict[str, Any] | None:
    """Load a single plugin file and extract its tools."""
    module_name = f"hilda_user_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        log.error("Plugin %s failed to load: %s", path.name, e)
        del sys.modules[module_name]
        return None

    name = getattr(module, "PLUGIN_NAME", None)
    description = getattr(module, "PLUGIN_DESCRIPTION", "")
    tools = getattr(module, "PLUGIN_TOOLS", [])

    if not name:
        log.debug("Skipping %s — no PLUGIN_NAME defined.", path.name)
        del sys.modules[module_name]
        return None

    if not tools:
        log.debug("Plugin %s has no PLUGIN_TOOLS — skipping.", name)
        del sys.modules[module_name]
        return None

    return {
        "name": name,
        "description": description,
        "tools": tools,
        "path": str(path),
    }


def get_all_plugin_tools() -> list:
    """Return all tools from all discovered plugins."""
    plugins = discover_plugins()
    all_tools = []
    for p in plugins:
        all_tools.extend(p["tools"])
    return all_tools
