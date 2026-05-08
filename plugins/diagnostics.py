"""
plugins/diagnostics.py — Quick local PC health snapshot (no LLM).
"""
import subprocess

from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)

_PS_SNAPSHOT = r"""
$os = Get-CimInstance Win32_OperatingSystem
$freeMb = [math]::Round(($os.FreePhysicalMemory / 1MB), 1)
$totalMb = [math]::Round(($os.TotalVisibleMemorySize / 1MB), 1)
$uptime = (Get-Date) - $os.LastBootUpTime
$disks = Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | ForEach-Object {
  $f = [math]::Round($_.FreeSpace / 1GB, 1)
  $s = [math]::Round($_.Size / 1GB, 1)
  "  {0} {1} GB free of {2} GB" -f $_.DeviceId, $f, $s
}
"OS: {0}`nUptime: {1}d {2}h`nMemory free: {3} / {4} GB`nDisks:`n{5}" -f `
  $os.Caption, $uptime.Days, $uptime.Hours, $freeMb, $totalMb, ($disks -join "`n")
""".strip()


def quick_pc_snapshot() -> str:
    """Return a short hardware / disk / memory summary via PowerShell."""
    sec = check_command(_PS_SNAPSHOT)
    if not sec.safe:
        return f"Can't run diagnostics. {sec.reason}"
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _PS_SNAPSHOT],
            capture_output=True,
            text=True,
            timeout=25,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode == 0 and out:
            log.info("PC snapshot OK.")
            return out[:2500]
        return (err or out or "Diagnostics command returned no output.")[:2000]
    except subprocess.TimeoutExpired:
        return "Diagnostics timed out."
    except Exception as e:
        log.error("Diagnostics failed: %s", e)
        return f"Diagnostics error: {e}"
