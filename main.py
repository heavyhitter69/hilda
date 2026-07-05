"""
main.py — Hilda desktop assistant entry point.

Starts:
  1. WebSocket server (for Electron UI communication)
  2. Voice pipeline (wake word → STT → agent → TTS)
  3. Memory pattern greeting on startup
"""
import asyncio
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from core.logger import get_logger
from core.websocket_server import start_server, broadcast_message, broadcast_state
from voice.audio_manager import AudioManager, set_audio_manager
from core.agent import get_agent

log = get_logger("hilda.main")

ASCII_BANNER = r"""
+-------------------------------------------+
|  HILDA  ·  Desktop voice assistant       |
|  Tip: Say your Porcupine wake word, then   |
|  "open downloads" / "lock" / "type ..."  |
+-------------------------------------------+
"""


async def startup_greeting() -> None:
    """Deliver a startup greeting and habit suggestion."""
    from memory.pattern_learner import PatternLearner
    from core.personality import get_startup_greeting

    suggestion = PatternLearner().get_suggestion_now()
    greeting = get_startup_greeting(suggestion=suggestion)

    await broadcast_state("speaking")
    await broadcast_message("assistant", greeting)

    from voice.text_to_speech import speak
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, speak, greeting)
    await broadcast_state("idle")


async def reminder_worker() -> None:
    """Background task to poll for due reminders."""
    from memory.memory_manager import MemoryManager
    from voice.text_to_speech import speak
    from plugins.reminder_control import show_notification
    from core.websocket_server import broadcast_message, broadcast_state

    mm = MemoryManager()
    log.info("Reminder worker started.")
    
    while True:
        try:
            due = mm.get_due_reminders()
            for r in due:
                msg = f"Reminder: {r['message']}"
                log.info("Triggering reminder: %s", msg)
                
                # Visual + WS
                await broadcast_state("speaking")
                await broadcast_message("assistant", msg)
                show_notification("Reminder", r['message'])
                
                # Voice
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, speak, msg)
                
                # Mark done
                mm.mark_reminder_completed(r['id'])
                await broadcast_state("idle")
                
        except Exception as e:
            log.error("Error in reminder worker: %s", e)
            
        await asyncio.sleep(30)  # Check every 30 seconds


async def main() -> None:
    from core import websocket_server as ws_server

    ws_server.register_event_loop(asyncio.get_running_loop())

    print(ASCII_BANNER)
    log.info("Hilda starting up…")
    log.info("WebSocket   : ws://%s:%d", settings.WEBSOCKET_HOST, settings.WEBSOCKET_PORT)
    log.info("Local model : %s @ %s", settings.OLLAMA_MODEL, settings.OLLAMA_HOST)
    log.info("Cloud model : %s (key set: %s)", settings.OPENAI_MODEL, bool(settings.OPENAI_API_KEY))
    _tts_engine = "Edge TTS" if settings.USE_EDGE_TTS else ("Coqui" if settings.USE_COQUI_TTS else "pyttsx3")
    log.info("Voice TTS   : %s", _tts_engine)
    log.info("Vision      : %s", "enabled" if settings.USE_VISION else "disabled")

    loop = asyncio.get_event_loop()

    setup_mode = str(os.getenv("HILDA_SETUP_MODE", "")).strip() in ("1", "true", "True", "yes", "on")
    if setup_mode:
        log.info("Setup mode enabled — suppressing greeting and wake listener.")
    else:
        # Start audio manager (wake word in background thread)
        audio = AudioManager(loop)
        audio.start()
        set_audio_manager(audio)

    # Deliver startup greeting after WS server is ready
    async def delayed_greeting():
        await asyncio.sleep(1.5)
        if not setup_mode:
            await startup_greeting()

    # Start proactive engine
    from core.proactive_engine import start_proactive_engine
    if not setup_mode:
        start_proactive_engine()

    # Run WebSocket server + greeting + reminder worker concurrently
    await asyncio.gather(
        start_server(),
        delayed_greeting(),
        reminder_worker(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        from core.agent import get_agent
        from core.proactive_engine import stop_proactive_engine
        
        stop_proactive_engine()
        get_agent().save_conversation()
        log.info("Hilda shut down by user.")
