"""
plugins/info_control.py — System information tools.
"""
from datetime import datetime
from core.logger import get_logger

log = get_logger(__name__)

def get_current_time() -> str:
    """Return the current time in a friendly format."""
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')}."

def get_current_date() -> str:
    """Return the current date in a friendly format."""
    now = datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."
