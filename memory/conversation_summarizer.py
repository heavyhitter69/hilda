"""
memory/conversation_summarizer.py — Conversation thread summarization.

When conversation history exceeds the context window, older turns are
summarized to preserve key decisions, facts, and action items without
overwhelming the LLM context.
"""
from __future__ import annotations

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_SUMMARIZE_PROMPT = """Summarize this conversation into a concise paragraph. Preserve:
- Key decisions made
- Important facts or information shared
- Action items or tasks completed
- User preferences expressed
- Any commitments or promises made

Keep it under 150 words. Focus on what matters for continuing the conversation.

Conversation:
{conversation}

Summary:"""


def summarize_messages(messages: list[dict], max_words: int = 150) -> str:
    """
    Summarize a list of conversation messages into a concise paragraph.

    Parameters
    ----------
    messages : list of {"role": str, "content": str}
    max_words : int — target max words for the summary
    """
    if not messages:
        return ""

    # Build conversation text
    lines = []
    for msg in messages:
        role = msg.get("role", "user").capitalize()
        content = (msg.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content[:300]}")

    conversation_text = "\n".join(lines)

    if not conversation_text.strip():
        return ""

    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise conversation summarizer. Be concise and factual.",
                },
                {
                    "role": "user",
                    "content": _SUMMARIZE_PROMPT.format(conversation=conversation_text),
                },
            ],
            options={
                "temperature": 0.1,
                "num_predict": 200,
            },
        )
        summary = response["message"]["content"].strip()
        log.info("Summarized %d messages into %d chars.", len(messages), len(summary))
        return summary
    except Exception as e:
        log.error("Conversation summarization failed: %s", e)
        # Fallback: just list the user messages
        user_msgs = [m["content"][:80] for m in messages if m.get("role") == "user"]
        return "Topics discussed: " + "; ".join(user_msgs[:5])


def sliding_window_with_summary(
    messages: list[dict],
    max_recent: int = 20,
) -> tuple[str, list[dict]]:
    """
    If conversation exceeds max_recent messages, summarize older turns
    and return (summary, recent_messages).

    Returns
    -------
    (summary, recent_messages)
    summary : str — summary of older messages (empty if no truncation needed)
    recent_messages : list[dict] — the most recent messages to keep verbatim
    """
    if len(messages) <= max_recent:
        return "", messages

    # Split: older messages to summarize, recent messages to keep
    cutoff = len(messages) - max_recent
    older = messages[:cutoff]
    recent = messages[cutoff:]

    summary = summarize_messages(older)
    return summary, recent
