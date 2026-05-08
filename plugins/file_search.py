"""
plugins/file_search.py — Search for files by name or keyword.
"""
import os
from pathlib import Path
from core.logger import get_logger

log = get_logger(__name__)


def search_files(query: str, path: str = "C:\\Users") -> list[str]:
    """
    Search for files whose name contains the query string.
    Returns a list of absolute paths (up to 20 matches).
    """
    query_lower = query.lower()
    matches: list[str] = []
    root = Path(path)

    if not root.exists():
        root = Path.home()

    try:
        for dirpath, _, filenames in os.walk(root):
            # Skip hidden / system dirs
            parts = Path(dirpath).parts
            skip_dirs = {"$recycle.bin", "windows", "appdata", "programdata"}
            if any(p.lower() in skip_dirs for p in parts):
                continue
            for fname in filenames:
                if query_lower in fname.lower():
                    matches.append(os.path.join(dirpath, fname))
                    if len(matches) >= 20:
                        return matches
    except PermissionError:
        pass
    except Exception as e:
        log.error("File search error: %s", e)

    log.info("File search '%s': %d results.", query, len(matches))
    return matches


def open_file(path: str) -> str:
    """Open a file with its default application."""
    import subprocess
    try:
        os.startfile(path)
        log.info("Opened file: %s", path)
        return f"Opened {path}."
    except Exception as e:
        log.error("Failed to open file %s: %s", path, e)
        return f"Could not open file: {e}"


def search_and_open(query: str, root: str = "C:\\Users") -> str:
    """
    Search for a file by query and open the first/best match.
    Intended for "open my resume.pdf" style commands.
    """
    results = search_files(query, root)
    if not results:
        return f"No files found matching '{query}'."
    return open_file(results[0])
