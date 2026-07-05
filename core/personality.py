"""
core/personality.py — Dynamic Jarvis-level personality engine.

Builds a rich, context-aware system prompt that makes Hilda feel intelligent,
witty, and deeply aware of the user's world.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

NAME = (settings.ASSISTANT_NAME or "Hilda").strip()


def _time_of_day() -> str:
    h = datetime.now().hour
    if h < 5:
        return "late night"
    if h < 12:
        return "morning"
    if h < 17:
        return "afternoon"
    if h < 21:
        return "evening"
    return "night"


def _day_greeting() -> str:
    tod = _time_of_day()
    greetings = {
        "late night": "It's late — I'm here if you need me.",
        "morning": "Good morning.",
        "afternoon": "Good afternoon.",
        "evening": "Good evening.",
        "night": "Good night's work ahead.",
    }
    return greetings.get(tod, "")


_CORE_PERSONALITY = f"""You are {NAME}, an elite AI desktop assistant — sharp, resourceful, and indispensable.

PERSONALITY:
- You are confident, slightly witty, and efficient — like Jarvis from Iron Man.
- You anticipate needs before being asked. You notice patterns and proactively offer help.
- You're warm but never sycophantic. You respect the user's time above all else.
- When you don't know something, you say so directly — never make things up.
- You have dry humor. You're allowed to be clever, but never at the user's expense.
- You remember things the user tells you and reference them naturally later.

RESPONSE RULES:
- For voice responses: Keep it to 1–3 sentences maximum. Be crisp and direct.
- For text/chat responses: You may be more detailed, but stay focused. Use markdown when helpful.
- For task execution: Describe what you did in one short sentence after completing it.
- NEVER pad responses with filler phrases like "Sure!", "Of course!", "Absolutely!". Just do the thing.
- When executing tasks, confirm completion briefly. Don't narrate each step.

CAPABILITIES:
- You can control this computer: open/close apps, manage files, adjust settings, run commands.
- You can search the web and summarize content from URLs and documents.
- You can manage email, calendar events, and contacts.
- You can remember facts, preferences, and past conversations.
- You can see what the user is currently working on (active window, running apps).
- You can set reminders and timers.
- When you need current/real-time information, use web search — don't guess.

SAFETY:
- Never execute destructive operations without confirming.
- Never access, share, or expose sensitive credentials.
- If a request seems dangerous, explain why and suggest a safer alternative."""


def build_system_prompt(
    *,
    context: Optional[dict[str, Any]] = None,
    user_facts: Optional[list[str]] = None,
    relevant_memories: Optional[list[str]] = None,
    conversation_summary: Optional[str] = None,
    is_voice: bool = True,
) -> str:
    """
    Build a rich, context-aware system prompt.

    Parameters
    ----------
    context : dict — output of context_awareness.build_context_snapshot()
    user_facts : list[str] — known facts about the user from semantic memory
    relevant_memories : list[str] — relevant past conversation snippets
    conversation_summary : str — summary of earlier conversation turns
    is_voice : bool — True if input came via voice (shorter responses)
    """
    sections: list[str] = [_CORE_PERSONALITY]

    # ── Time context ──────────────────────────────────────────────────────
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")
    date_str = now.strftime("%A, %B %d, %Y")
    sections.append(f"\nCURRENT TIME: {time_str} on {date_str} ({_time_of_day()})")

    # ── User identity ─────────────────────────────────────────────────────
    from config.user_settings_file import get_user_display_name
    user_name = get_user_display_name(settings.WRITABLE_ROOT).strip()
    if not user_name:
        user_name = (os.getenv("USERNAME") or os.getenv("USER") or "").strip()
    if user_name:
        sections.append(f"USER: {user_name}")

    # ── Active context ────────────────────────────────────────────────────
    if context:
        ctx_lines = ["\nCURRENT CONTEXT:"]
        if context.get("active_window"):
            ctx_lines.append(f"  Active window: {context['active_window']}")
        if context.get("active_app"):
            ctx_lines.append(f"  Active app: {context['active_app']}")
        if context.get("running_apps"):
            apps = ", ".join(context["running_apps"][:10])
            ctx_lines.append(f"  Running apps: {apps}")
        if context.get("battery"):
            ctx_lines.append(f"  Battery: {context['battery']}")
        sections.append("\n".join(ctx_lines))

    # ── Known user facts ──────────────────────────────────────────────────
    if user_facts:
        facts_str = "\n".join(f"  - {f}" for f in user_facts[:15])
        sections.append(f"\nTHINGS I KNOW ABOUT THE USER:\n{facts_str}")

    # ── Relevant memories ─────────────────────────────────────────────────
    if relevant_memories:
        mem_str = "\n".join(f"  - {m}" for m in relevant_memories[:5])
        sections.append(f"\nRELEVANT PAST CONTEXT:\n{mem_str}")

    # ── Conversation summary ──────────────────────────────────────────────
    if conversation_summary:
        sections.append(
            f"\nEARLIER IN THIS CONVERSATION (summary):\n  {conversation_summary}"
        )

    # ── Response mode ─────────────────────────────────────────────────────
    if is_voice:
        sections.append(
            "\nMODE: Voice output. Keep responses extremely concise (1-2 sentences max)."
        )
    else:
        sections.append(
            "\nMODE: Text chat. You may be more detailed. Use markdown formatting."
        )

    return "\n".join(sections)


def get_startup_greeting(user_name: str = "", suggestion: str = "") -> str:
    """Generate a contextual startup greeting."""
    tod = _time_of_day()
    name_part = f", {user_name}" if user_name else ""

    if suggestion:
        return suggestion

    greetings = {
        "late night": f"Burning the midnight oil{name_part}? I'm ready when you are.",
        "morning": f"Good morning{name_part}. What's on the agenda?",
        "afternoon": f"Good afternoon{name_part}. How can I help?",
        "evening": f"Good evening{name_part}. What do you need?",
        "night": f"Evening{name_part}. I'm here if you need anything.",
    }
    return greetings.get(tod, f"Hello{name_part}. How can I help?")
