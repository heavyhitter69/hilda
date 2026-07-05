"""
memory/fact_extractor.py — Extract personal facts from conversations.

After each conversation exchange, uses the LLM to identify any new personal
facts, preferences, or important information about the user, then stores
them in semantic memory for future reference.
"""
from __future__ import annotations

import json
import re


from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_EXTRACT_PROMPT = """Analyze this conversation exchange and extract any personal facts, preferences, or important information about the user. Only extract CONCRETE, SPECIFIC facts — not vague observations.

Examples of good facts:
- "User's name is Alex"
- "User prefers dark mode"
- "User works as a software engineer"
- "User's mother is named Sarah"
- "User uses Gmail for work email"
- "User's favorite programming language is Python"
- "User has a meeting every Tuesday at 3 PM"

Examples of BAD facts (too vague, don't extract):
- "User asked a question"
- "User wanted to open an app"
- "User seems busy"

Respond with a JSON array of extracted facts. If no personal facts are present, respond with an empty array: []

Conversation:
User: {user_msg}
Assistant: {assistant_msg}

Extracted facts (JSON array):"""


def extract_facts(user_msg: str, assistant_msg: str) -> list[str]:
    """
    Extract personal facts from a conversation exchange.
    Returns a list of fact strings.
    """
    if not user_msg or len(user_msg.strip()) < 10:
        return []

    # Quick pre-filter: skip obvious commands and short queries
    low = user_msg.lower()
    skip_patterns = [
        "open ", "close ", "launch ", "start ", "type ", "paste ",
        "search ", "google ", "youtube ", "lock", "shutdown", "restart",
        "volume ", "mute", "brightness", "screenshot", "timer ", "remind ",
    ]
    if any(low.startswith(p) for p in skip_patterns):
        return []

    try:
        import ollama
        prompt = _EXTRACT_PROMPT.format(
            user_msg=user_msg[:500],
            assistant_msg=assistant_msg[:500],
        )
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "You extract personal facts from conversations. Respond ONLY with a JSON array."},
                {"role": "user", "content": prompt},
            ],
            options={
                "temperature": 0.0,
                "num_predict": 200,
            },
        )
        raw = response["message"]["content"].strip()

        # Parse JSON array from response
        json_match = re.search(r"\[.*\]", raw, re.DOTALL)
        if json_match:
            facts = json.loads(json_match.group())
            if isinstance(facts, list):
                cleaned = [str(f).strip() for f in facts if isinstance(f, str) and len(str(f).strip()) > 5]
                if cleaned:
                    log.info("Extracted %d facts from conversation.", len(cleaned))
                return cleaned[:5]  # Cap at 5 facts per exchange
    except Exception as e:
        log.debug("Fact extraction failed: %s", e)

    return []


def extract_and_store(user_msg: str, assistant_msg: str) -> int:
    """
    Extract facts from a conversation exchange and store them in semantic memory.
    Returns the number of facts stored.
    """
    facts = extract_facts(user_msg, assistant_msg)
    if not facts:
        return 0

    try:
        from memory.semantic_memory import get_semantic_memory
        mem = get_semantic_memory()
        stored = 0
        for fact in facts:
            # Check if we already know this (avoid duplicates)
            existing = mem.recall(fact, category="user_facts", top_k=1)
            if existing and existing[0].get("distance", 1.0) < 0.15:
                log.debug("Fact already known: %s", fact[:60])
                continue
            if mem.store_fact(fact, source="conversation"):
                stored += 1
                log.info("Stored new fact: %s", fact[:60])
        return stored
    except Exception as e:
        log.error("extract_and_store failed: %s", e)
        return 0
