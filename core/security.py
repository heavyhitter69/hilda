"""
core/security.py — Safety filter for Hilda.
Blocks dangerous commands before they reach the execution layer.
"""
import re
from dataclasses import dataclass
from typing import Tuple

from core.logger import get_logger

log = get_logger(__name__)

# ── Blocklist ─────────────────────────────────────────────────────────────────
# Each entry is (regex_pattern, human_readable_reason).
# Patterns are case-insensitive.
BLOCKLIST: list[Tuple[str, str]] = [
    # Disk destruction
    (r"\bformat\s+(c:|d:|e:|\w:)", "disk formatting"),
    (r"\bdiskpart\b", "diskpart utility"),
    (r"\bdd\s+if=", "raw disk write (dd)"),
    # System file deletion
    (r"(delete|del|rm)\s+.*system32", "system32 deletion"),
    (r"(delete|del|rm)\s+.*windows\\system", "Windows system deletion"),
    (r"rm\s+-rf\s+/", "root filesystem deletion"),
    # Generic destructive deletes / wipes
    (r"\brm\s+-rf\b", "recursive delete"),
    (r"\bdel\s+/s\b", "recursive delete"),
    (r"\brmdir\s+/s\b", "recursive directory delete"),
    (r"\berase\s+/s\b", "recursive erase"),
    # Registry destruction
    (r"reg\s+delete\s+HKLM\\SYSTEM", "critical registry deletion"),
    # Anti-security
    (r"disable.*(antivirus|defender|firewall)", "disabling security software"),
    (r"net\s+stop\s+(mpssvc|wscsvc|windefend)", "stopping security services"),
    # Self-replication / malware-like
    (r"(start-process|invoke-expression)\s+.*\.exe", "arbitrary executable launch via script"),
    # Credential theft
    (r"(mimikatz|procdump|lsass)", "credential dumping tool"),
]

_COMPILED = [(re.compile(pat, re.IGNORECASE), reason) for pat, reason in BLOCKLIST]


@dataclass
class SecurityResult:
    safe: bool
    reason: str = ""


def check_command(command: str) -> SecurityResult:
    """
    Evaluate a command string against the blocklist.

    Returns SecurityResult(safe=True) if the command is safe,
    or SecurityResult(safe=False, reason=...) if blocked.
    """
    for pattern, reason in _COMPILED:
        if pattern.search(command):
            log.warning("BLOCKED command — matched '%s': %s", reason, command[:120])
            return SecurityResult(safe=False, reason=f"Command blocked: {reason}.")

    log.debug("Security check passed: %s", command[:80])
    return SecurityResult(safe=True)
