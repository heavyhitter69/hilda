"""
plugins/timer_control.py — Quick in-memory timers.
"""
import threading
from core.logger import get_logger
from voice.text_to_speech import speak
from plugins.reminder_control import show_notification

log = get_logger(__name__)

def set_timer(seconds: int, message: str) -> str:
    """Set a timer for X seconds."""
    if seconds <= 0:
        return "The timer must be for at least one second."

    def _timer_thread():
        import time
        time.sleep(seconds)
        log.info("Timer expired: %s", message)
        
        # Notify
        show_notification("Timer Expired", message)
        
        # Speak (using a separate thread for TTS as well if needed, but speak() usually handles it)
        try:
            speak(f"Your timer for {message} is up.")
        except Exception as e:
            log.error("TTS failed for timer: %s", e)

    # Run in a background thread so we don't block the agent
    threading.Thread(target=_timer_thread, daemon=True).start()
    
    # Human readable time
    if seconds >= 60:
        m = seconds // 60
        s = seconds % 60
        time_str = f"{m} minute{'s' if m != 1 else ''}"
        if s > 0:
            time_str += f" and {s} second{'s' if s != 1 else ''}"
    else:
        time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
        
    return f"Timer set for {time_str}."
