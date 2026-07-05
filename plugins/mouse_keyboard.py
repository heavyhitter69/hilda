"""
plugins/mouse_keyboard.py — Mouse and keyboard automation via PyAutoGUI.
"""

import pyautogui
from core.logger import get_logger

log = get_logger(__name__)

# Safety: fail-safe corner to abort automation (move mouse to top-left)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05  # 50 ms between PyAutoGUI calls


def move_mouse(x: int, y: int) -> str:
    """Move the mouse to (x, y) with a smooth tween."""
    pyautogui.moveTo(x, y, duration=0.3, tween=pyautogui.easeOutQuad)
    log.debug("Moved mouse to (%d, %d)", x, y)
    return f"Moved mouse to ({x}, {y})."


def click(x: int, y: int, button: str = "left") -> str:
    """Click at (x, y)."""
    pyautogui.click(x, y, button=button)
    log.info("Clicked (%d, %d) [%s]", x, y, button)
    return f"Clicked ({x}, {y})."


def double_click(x: int, y: int) -> str:
    """Double-click at (x, y)."""
    pyautogui.doubleClick(x, y)
    return f"Double-clicked ({x}, {y})."


def type_text(text: str, interval: float = 0.05) -> str:
    """Type text via keyboard with a natural interval between characters."""
    pyautogui.typewrite(text, interval=interval)
    log.info("Typed text: '%s'", text[:40])
    return f"Typed: '{text}'."


def paste_text(text: str) -> str:
    """
    Paste text quickly by putting it on the clipboard and pressing Ctrl+V.
    This is much faster (and more accurate) than typing character-by-character.
    """
    import subprocess
    if not text:
        return "Nothing to paste."
    # Clipboard via PowerShell reading from stdin (avoids quoting/here-string breakage).
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-STA",
            "-Command",
            "Add-Type -AssemblyName System.Windows.Forms;"
            "[System.Windows.Forms.Clipboard]::SetText([Console]::In.ReadToEnd())",
        ],
        input=text,
        capture_output=True,
        text=True,
    )
    pyautogui.hotkey("ctrl", "v")
    log.info("Pasted text: '%s'", text[:40])
    return "Pasted text."


def hotkey(*keys: str) -> str:
    """Press a keyboard hotkey combination, e.g. hotkey('ctrl', 'c')."""
    pyautogui.hotkey(*keys)
    log.info("Hotkey: %s", "+".join(keys))
    return f"Pressed {'+'.join(keys)}."


def scroll(clicks: int, x: int = None, y: int = None) -> str:
    """Scroll up (positive) or down (negative) by `clicks` steps."""
    if x is not None and y is not None:
        pyautogui.scroll(clicks, x=x, y=y)
    else:
        pyautogui.scroll(clicks)
    direction = "up" if clicks > 0 else "down"
    log.debug("Scrolled %s %d clicks.", direction, abs(clicks))
    return f"Scrolled {direction}."


def screenshot_region(left: int, top: int, width: int, height: int):
    """Capture a screen region and return a PIL Image."""
    import mss
    from PIL import Image as PILImage
    with mss.mss() as sct:
        monitor = {"left": left, "top": top, "width": width, "height": height}
        shot = sct.grab(monitor)
        return PILImage.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
