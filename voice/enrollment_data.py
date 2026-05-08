"""
Built-in enrollment lines — wake variants + phonetically rich English samples.

Users record each line so Whisper gets accent/context hints (via initial_prompt).
This is not a separate acoustic model like Siri’s on-device training; it’s the
practical offline equivalent using Whisper + stored prompts.
"""
from __future__ import annotations

from typing import TypedDict


class EnrollmentPhrase(TypedDict):
    id: str
    prompt: str
    hint: str


# Order matters for UX (short wake phrases first, then broader coverage).
ENROLLMENT_PHRASES: list[EnrollmentPhrase] = [
    {
        "id": "hey_hilda",
        "prompt": "Hey Hilda",
        "hint": "Wake phrase — say it naturally.",
    },
    {
        "id": "hello_hilda",
        "prompt": "Hello Hilda",
        "hint": "Alternative greeting.",
    },
    {
        "id": "hi_there",
        "prompt": "Hi there Hilda",
        "hint": "Casual wake.",
    },
    {
        "id": "pangram",
        "prompt": "The quick brown fox jumps over the lazy dog",
        "hint": "Covers many consonants and vowels in English.",
    },
    {
        "id": "vowel_weather",
        "prompt": "Hilda, please open my music, video, documents, and calendar",
        "hint": "Extra vowels and common assistant verbs.",
    },
    {
        "id": "numbers",
        "prompt": "One two three four five six seven eight nine ten",
        "hint": "Digit sounds.",
    },
]
