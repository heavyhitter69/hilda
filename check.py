import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

ok = []
fail = []

def chk(label, fn):
    try:
        msg = fn() or "ok"
        ok.append((label, str(msg)[:60]))
    except Exception as e:
        fail.append((label, str(e)[:70]))

def test_config():
    from config.settings import settings
    assert settings.OPENAI_API_KEY.startswith("sk-")
    assert len(settings.PORCUPINE_ACCESS_KEY) > 10
    return "OpenAI key loaded, Porcupine key loaded, port=" + str(settings.WEBSOCKET_PORT)

def test_security():
    from core.security import check_command
    assert not check_command("delete system32").safe
    assert check_command("open notepad").safe
    return "blocklist working"

def test_memory():
    from memory.memory_manager import MemoryManager
    m = MemoryManager()
    m.log_action("health check", "ok")
    r = m.get_recent(1)
    return "SQLite last action: " + r[0]["action"]

def test_plugins():
    import pyautogui
    from plugins.app_control import APP_MAP
    from plugins.file_search import search_files
    from plugins.mouse_keyboard import move_mouse
    pos = pyautogui.position()
    return str(len(APP_MAP)) + " apps registered, mouse at " + str(pos)

def test_vision():
    from vision.screen_capture import capture_fullscreen
    img = capture_fullscreen()
    w, h = img.size
    return "captured " + str(w) + "x" + str(h)

def test_ws():
    from core.websocket_server import broadcast_state
    return "module ok"

def test_openai():
    from openai import AsyncOpenAI
    from config.settings import settings
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return "client initialised"

def test_pattern():
    from memory.pattern_learner import PatternLearner
    p = PatternLearner()
    return p.summarise_patterns()[:50]

chk("Config + API keys", test_config)
chk("Security filter", test_security)
chk("Memory SQLite", test_memory)
chk("Plugins + PyAutoGUI", test_plugins)
chk("Vision screen capture", test_vision)
chk("WebSocket module", test_ws)
chk("OpenAI client", test_openai)
chk("Pattern learner", test_pattern)

print()
print("=" * 60)
print("  EMILIO HEALTH CHECK")
print("=" * 60)
for label, msg in ok:
    print("  [OK]   " + label.ljust(28) + " " + msg)
for label, msg in fail:
    print("  [FAIL] " + label.ljust(28) + " " + msg)
print()
print("  Result: " + str(len(ok)) + "/" + str(len(ok)+len(fail)) + " passed")
if not fail:
    print("  >> Hilda is READY TO LAUNCH <<")
else:
    print("  >> Fix the above failures before launching <<")
print("=" * 60)
