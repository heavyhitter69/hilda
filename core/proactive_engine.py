"""
core/proactive_engine.py — Proactive suggestion engine for Hilda.

Runs periodically in the background to analyze desktop context and memory,
suggesting helpful actions before the user asks.
"""
import asyncio

from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_proactive_task: Optional[asyncio.Task] = None
_last_suggestion_time = 0.0
_SUGGESTION_COOLDOWN_SECS = 3600  # Only suggest once per hour


async def _proactive_loop() -> None:
    """Background loop that periodically checks context and makes suggestions."""
    log.info("Proactive engine started.")
    
    while True:
        await asyncio.sleep(300)  # Check every 5 minutes
        
        if not getattr(settings, "USE_PROACTIVE_SUGGESTIONS", True):
            continue
            
        import time
        if time.time() - _last_suggestion_time < _SUGGESTION_COOLDOWN_SECS:
            continue
            
        try:
            suggestion = await generate_proactive_suggestion()
            if suggestion:
                log.info("Proactive suggestion: %s", suggestion)
                
                # Speak and show notification
                from core import websocket_server
                from voice.text_to_speech import speak
                from plugins.reminder_control import show_notification
                
                show_notification("Hilda Suggestion", suggestion)
                
                await websocket_server.broadcast_state("speaking")
                await websocket_server.broadcast_message("assistant", f"*(Proactive)* {suggestion}")
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, speak, suggestion)
                
                await websocket_server.broadcast_state("idle")
                
                global _last_suggestion_time
                _last_suggestion_time = time.time()
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error("Proactive loop error: %s", e)


async def generate_proactive_suggestion() -> Optional[str]:
    """Analyze context and generate a suggestion if appropriate."""
    try:
        from core.context_awareness import build_context_snapshot
        context = build_context_snapshot()
        
        # Don't interrupt if they are active in a full-screen app or game
        apps = context.get("running_apps", [])
        active = context.get("active_app", "").lower()
        if any(game in active for game in ("steam", "epic", "obs", "vlc", "game")):
            return None
            
        # Get user facts
        user_facts = []
        if settings.USE_SEMANTIC_MEMORY:
            try:
                from memory.semantic_memory import get_semantic_memory
                mem = get_semantic_memory()
                user_facts = mem.get_user_facts(top_k=5)
            except Exception:
                pass
                
        # Build prompt
        prompt = (
            "You are a proactive AI assistant. Based on the user's current context, "
            "suggest ONE helpful action you can perform. If no action is clearly helpful right now, "
            "respond with exactly 'NONE'. Be very concise (1 sentence).\n\n"
            f"Time: {context.get('time')}\n"
            f"Active Window: {context.get('active_window')}\n"
            f"Active App: {context.get('active_app')}\n"
            f"Running Apps: {', '.join(apps[:10])}\n"
            f"Battery: {context.get('battery')}\n"
        )
        if user_facts:
            prompt += f"Known Facts: {', '.join(user_facts)}\n"
            
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are a proactive assistant. Suggest one helpful action or reply NONE."},
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0.4, "num_predict": 50}
        )
        
        suggestion = response["message"]["content"].strip()
        if suggestion.upper() == "NONE" or len(suggestion) < 10:
            return None
            
        # Strip quotes if the LLM added them
        suggestion = suggestion.strip('"').strip("'")
        return suggestion
        
    except Exception as e:
        log.debug("Proactive generation failed: %s", e)
        return None


def start_proactive_engine() -> None:
    """Start the background proactive engine task."""
    global _proactive_task
    if _proactive_task is None and getattr(settings, "USE_PROACTIVE_SUGGESTIONS", True):
        loop = asyncio.get_event_loop()
        _proactive_task = loop.create_task(_proactive_loop())


def stop_proactive_engine() -> None:
    """Stop the background proactive engine task."""
    global _proactive_task
    if _proactive_task:
        _proactive_task.cancel()
        _proactive_task = None
