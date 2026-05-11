import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.memory_manager import MemoryManager
from plugins.reminder_control import add_reminder, list_reminders, show_notification
from plugins.info_control import get_current_time, get_current_date

def test_db():
    print("Testing DB...")
    mm = MemoryManager()
    
    # Clean up
    mm.clear()
    
    # Add reminder
    due = datetime.now() + timedelta(seconds=10)
    mm.add_reminder("Test Message", due)
    
    # Check due
    reminders = mm.get_due_reminders()
    print(f"Due now (should be 0): {len(reminders)}")
    
    import time
    print("Waiting 12 seconds...")
    time.sleep(12)
    
    reminders = mm.get_due_reminders()
    print(f"Due now (should be 1): {len(reminders)}")
    if reminders:
        print(f"Message: {reminders[0]['message']}")
        mm.mark_reminder_completed(reminders[0]['id'])
        
    reminders = mm.get_due_reminders()
    print(f"Due now (should be 0): {len(reminders)}")

def test_plugins():
    print("\nTesting Plugins...")
    print(add_reminder("Drink water", minutes_from_now=1))
    print(list_reminders())
    print(get_current_time())
    print(get_current_date())

def test_notification():
    print("\nTesting Notification...")
    show_notification("Hilda Test", "This is a test notification from Hilda!")

if __name__ == "__main__":
    test_db()
    test_plugins()
    test_notification()
