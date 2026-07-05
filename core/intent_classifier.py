"""
core/intent_classifier.py — Smart NLU layer for Hilda.

Uses a lightweight Ollama call to classify user intent, replacing
fragile regex-only routing. Falls back to regex if Ollama is unavailable.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


@dataclass
class Intent:
    """Classified user intent."""
    category: str  # TOOL_ACTION, QUESTION, CONVERSATION, MEMORY_QUERY, WEB_SEARCH, CREATIVE, VISION
    confidence: float = 0.8
    target_action: str = ""  # e.g., "open", "close", "search", "set_reminder"
    entities: dict = field(default_factory=dict)  # extracted entities
    raw_input: str = ""


# ── Regex fallback (fast, reliable for exact patterns) ────────────────────────

_TOOL_VERBS = re.compile(
    r"(?i)\b(open|launch|start|close|quit|exit|kill|shutdown|restart|reboot|"
    r"sleep|suspend|lock|unlock|type|paste|scroll|navigate|dictate|run|"
    r"powershell|play|pause|next|previous|find|search|download|show\s+me|"
    r"go\s+to|open\s+url|youtube|google|mute|unmute|volume|brightness|"
    r"screenshot|battery|timer|remind|set\s+a|empty|trash|wifi|bluetooth|"
    r"airplane|hotspot|project|cast|task\s+manager)\b"
    r"|(?:\bhttps?://|\bwww\.)\S+"
)

_QUESTION_PATTERN = re.compile(
    r"(?i)\b(how\s+(do\s+i|to|does|can\s+i|would\s+i)|explain|"
    r"why\s+(is|does|are|will|wont|won't)|"
    r"what\s+(is|are|was|were|does)|tell\s+me\s+(about|how)|"
    r"can\s+you\s+explain|describe|define)\b"
)

_WEB_SEARCH_PATTERN = re.compile(
    r"(?i)\b(weather|news|stock|price|score|result|latest|current|"
    r"today's|who\s+won|what\s+happened|search\s+for|look\s+up|"
    r"search\s+the\s+web|search\s+online|find\s+out)\b"
)

_MEMORY_PATTERN = re.compile(
    r"(?i)\b(remember|recall|did\s+i|last\s+time|previously|"
    r"we\s+discussed|we\s+talked|you\s+said|i\s+told\s+you|"
    r"do\s+you\s+remember|what\s+did\s+i)\b"
)

_CREATIVE_PATTERN = re.compile(
    r"(?i)\b(write|draft|compose|create|generate|summarize|summarise|"
    r"translate|analyze|analyse|compare|code|script|refactor|debug|"
    r"proofread|rewrite|brainstorm)\b"
)

_VISION_PATTERN = re.compile(
    r"(?i)\b(what's\s+on\s+screen|what\s+do\s+you\s+see|look\s+at|"
    r"describe\s+my\s+screen|read\s+my\s+screen|what\s+am\s+i\s+looking\s+at|"
    r"screenshot|screen\s+capture)\b"
)

_EMAIL_PATTERN = re.compile(
    r"(?i)\b(email|inbox|send\s+an?\s+email|check\s+email|"
    r"compose\s+email|mail|unread)\b"
)

_CALENDAR_PATTERN = re.compile(
    r"(?i)\b(calendar|schedule|appointment|meeting|event|"
    r"what's\s+on\s+my\s+schedule|today's\s+events|upcoming)\b"
)


def classify_regex(text: str) -> Intent:
    """Fast regex-based intent classification (fallback)."""
    low = text.lower().strip()

    if _VISION_PATTERN.search(text):
        return Intent("VISION", 0.9, "vision", raw_input=text)

    if _EMAIL_PATTERN.search(text):
        return Intent("TOOL_ACTION", 0.85, "email", raw_input=text)

    if _CALENDAR_PATTERN.search(text):
        return Intent("TOOL_ACTION", 0.85, "calendar", raw_input=text)

    if _MEMORY_PATTERN.search(text):
        return Intent("MEMORY_QUERY", 0.8, raw_input=text)

    if _WEB_SEARCH_PATTERN.search(text):
        return Intent("WEB_SEARCH", 0.8, raw_input=text)

    # Check for tool verbs, but not if it's clearly a question
    if _TOOL_VERBS.search(text):
        if _QUESTION_PATTERN.search(text):
            # "How do I open..." → question, not action
            action_start = re.match(
                r"(?i)^\s*(open|launch|start|close|type|paste|run|"
                r"scroll|shutdown|restart|find|search|show|mute|set)",
                low,
            )
            if not action_start:
                return Intent("QUESTION", 0.7, raw_input=text)
        return Intent("TOOL_ACTION", 0.85, raw_input=text)

    if _CREATIVE_PATTERN.search(text):
        return Intent("CREATIVE", 0.8, raw_input=text)

    if _QUESTION_PATTERN.search(text):
        return Intent("QUESTION", 0.8, raw_input=text)

    # Default: if short and casual → conversation, else question
    if len(text.split()) <= 5:
        return Intent("CONVERSATION", 0.5, raw_input=text)
    return Intent("QUESTION", 0.5, raw_input=text)


# ── LLM-based classification (smart, handles natural language) ────────────────

_CLASSIFY_PROMPT = """Classify the user's message into exactly one intent category. Respond ONLY with valid JSON.

Categories:
- TOOL_ACTION: User wants to DO something on their computer (open app, change setting, run command, control media, etc.)
- QUESTION: User is asking for information, explanation, or knowledge
- CONVERSATION: Casual chat, greetings, thanks, or social interaction
- MEMORY_QUERY: User is asking about something previously discussed or told to the assistant
- WEB_SEARCH: User needs current/real-time information (weather, news, stocks, scores, etc.)
- CREATIVE: User wants written content (email draft, code, summary, translation, analysis)
- VISION: User wants the assistant to look at/describe the screen
- EMAIL: User wants to check, send, or manage email
- CALENDAR: User wants to check or manage calendar/schedule

Respond with JSON: {"category": "...", "confidence": 0.0-1.0, "target_action": "brief verb", "entities": {}}

User message: """


def classify_llm(text: str) -> Optional[Intent]:
    """Classify intent using a lightweight Ollama call."""
    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You are a precise intent classifier. Respond ONLY with valid JSON."},
                {"role": "user", "content": _CLASSIFY_PROMPT + f'"{text}"'},
            ],
            options={
                "temperature": 0.0,
                "num_predict": 80,
            },
        )
        raw = response["message"]["content"].strip()
        # Extract JSON from response
        json_match = re.search(r"\{[^}]+\}", raw)
        if json_match:
            data = json.loads(json_match.group())
            return Intent(
                category=data.get("category", "QUESTION"),
                confidence=float(data.get("confidence", 0.7)),
                target_action=data.get("target_action", ""),
                entities=data.get("entities", {}),
                raw_input=text,
            )
    except Exception as e:
        log.debug("LLM classify failed (using regex fallback): %s", e)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

_cache: dict[str, tuple[Intent, float]] = {}
_CACHE_TTL = 30.0  # seconds


def classify(text: str, use_llm: bool = True) -> Intent:
    """
    Classify user intent. Uses LLM when available, falls back to regex.
    Results are cached for the current turn.
    """
    # Check cache
    if text in _cache:
        intent, ts = _cache[text]
        if time.time() - ts < _CACHE_TTL:
            return intent

    intent = None
    if use_llm and getattr(settings, "USE_INTENT_CLASSIFIER", True):
        intent = classify_llm(text)

    if intent is None:
        intent = classify_regex(text)

    _cache[text] = (intent, time.time())

    # Evict old cache entries
    if len(_cache) > 50:
        cutoff = time.time() - _CACHE_TTL
        to_remove = [k for k, (_, ts) in _cache.items() if ts < cutoff]
        for k in to_remove:
            del _cache[k]

    log.info("Intent: %s (%.0f%%) for: '%s'", intent.category, intent.confidence * 100, text[:60])
    return intent
