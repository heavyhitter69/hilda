"""
plugins/__init__.py — Plugin registry.

Other modules import individual plugins directly, but this registry
provides a name → callable map for reflection and testing.
"""
from plugins.app_control    import open_application, close_application
from plugins.browser_control import open_url_sync, search_youtube_sync
from plugins.system_control  import system_action
from plugins.file_search     import search_files
from plugins.mouse_keyboard  import click, type_text, move_mouse, scroll

PLUGIN_REGISTRY: dict = {
    "open_application":   open_application,
    "close_application":  close_application,
    "open_url":           open_url_sync,
    "search_youtube":     search_youtube_sync,
    "system_action":      system_action,
    "search_files":       search_files,
    "click":              click,
    "type_text":          type_text,
    "move_mouse":         move_mouse,
    "scroll":             scroll,
}

__all__ = list(PLUGIN_REGISTRY.keys()) + ["PLUGIN_REGISTRY"]
