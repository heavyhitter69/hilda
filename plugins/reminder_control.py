"""
plugins/reminder_control.py — Manage and display Windows reminders.
"""
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Optional
from core.logger import get_logger
from memory.memory_manager import MemoryManager

log = get_logger(__name__)

def show_notification(title: str, message: str) -> None:
    """Show a native desktop notification based on the platform."""
    t = title.replace('"', '\\"')
    m = message.replace('"', '\\"')
    
    if sys.platform == "win32":
        # Windows: PowerShell/WinRT
        ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).AppendChild($template.CreateTextNode("{t}")) | Out-Null
$textNodes.Item(1).AppendChild($template.CreateTextNode("{m}")) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Hilda").Show($toast)
"""
        try:
            subprocess.run(["powershell", "-Command", ps_script], check=True, capture_output=True)
        except Exception as e:
            log.error("Windows notification failed: %s", e)
            
    elif sys.platform == "darwin":
        # macOS: AppleScript
        try:
            subprocess.run(["osascript", "-e", f'display notification "{m}" with title "{t}"'], check=True)
        except Exception as e:
            log.error("macOS notification failed: %s", e)
            
    else:
        # Linux: notify-send (common on GNOME/KDE)
        try:
            subprocess.run(["notify-send", t, m], check=True)
        except Exception as e:
            log.error("Linux notification failed: %s", e)

def add_reminder(message: str, minutes_from_now: Optional[int] = None, absolute_time: Optional[str] = None) -> str:
    """
    Add a new reminder.
    'minutes_from_now' is for relative offsets.
    'absolute_time' is a string like 'HH:MM'.
    """
    due_time = datetime.now()
    
    if minutes_from_now is not None:
        due_time += timedelta(minutes=minutes_from_now)
    elif absolute_time:
        try:
            # Parse HH:MM
            t = datetime.strptime(absolute_time, "%H:%M").time()
            due_time = datetime.combine(due_time.date(), t)
            # If the time has already passed today, assume tomorrow
            if due_time < datetime.now():
                due_time += timedelta(days=1)
        except ValueError:
            return "I couldn't understand that time format. Please use HH:MM."
    else:
        return "I need a time for the reminder."

    try:
        MemoryManager().add_reminder(message, due_time)
        time_str = due_time.strftime("%I:%M %p")
        return f"Okay, I'll remind you to '{message}' at {time_str}."
    except Exception as e:
        log.error("Failed to add reminder: %s", e)
        return f"I had trouble saving that reminder: {e}"

def list_reminders() -> str:
    """List all active reminders."""
    try:
        reminders = MemoryManager().get_all_reminders()
        if not reminders:
            return "You have no active reminders."
        
        lines = ["Your current reminders:"]
        for r in reminders:
            due = datetime.fromisoformat(r["due_time"])
            lines.append(f"- {r['message']} at {due.strftime('%I:%M %p')}")
        return "\n".join(lines)
    except Exception as e:
        log.error("Failed to list reminders: %s", e)
        return "I couldn't retrieve your reminders."

def delete_reminder_by_id(reminder_id: int) -> str:
    """Delete a reminder."""
    try:
        if MemoryManager().delete_reminder(reminder_id):
            return f"Reminder {reminder_id} deleted."
        return f"I couldn't find a reminder with ID {reminder_id}."
    except Exception as e:
        log.error("Failed to delete reminder: %s", e)
        return "Error deleting reminder."
