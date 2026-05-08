"""
scripts/add_to_startup.py — Register Hilda in Windows startup registry.

Run once with: python scripts/add_to_startup.py
To unregister:  python scripts/add_to_startup.py --remove
"""
import sys
import winreg
from pathlib import Path

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "HildaAssistant"


def add_startup():
    python = sys.executable
    main = Path(__file__).parent.parent / "main.py"
    cmd = f'"{python}" "{main}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
    print(f"Hilda added to Windows startup:\n   {cmd}")


def remove_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, APP_NAME)
        print("Hilda removed from Windows startup.")
    except FileNotFoundError:
        print("Hilda was not in the startup registry.")


if __name__ == "__main__":
    if "--remove" in sys.argv:
        remove_startup()
    else:
        add_startup()
