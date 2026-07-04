"""
config/settings.py — Central configuration for Hilda desktop assistant.
Environment: .env in WRITABLE_ROOT (user data) overrides .env next to the app in dev.
When HILDA_USER_DATA is set (by the Electron shell), logs/config live there.
"""
import json
import os
import sys
from pathlib import Path


def _code_dir() -> Path:
    """Directory containing the app (repo root in dev, install folder when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


CODE_DIR: Path = _code_dir()

_ud = os.getenv("HILDA_USER_DATA", "").strip()
WRITABLE_ROOT: Path = Path(_ud).expanduser().resolve() if _ud else CODE_DIR

def load_env_file(path: Path) -> None:
    if not path.is_file(): return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'").strip('"')
            if k: os.environ[k] = v
    except Exception:
        pass

# Load configuration: optional packaged defaults are overridden by user .env
load_env_file(CODE_DIR / ".env")
load_env_file(WRITABLE_ROOT / ".env")


def _merge_tts_voice_hint() -> str:
    path = WRITABLE_ROOT / "user_settings.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            hint = str(data.get("tts_voice_hint", "") or "").strip()
            if hint:
                return hint
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return os.getenv("TTS_VOICE_HINT", "zira").strip() or "zira"


class Settings:
    # Code / read-only (resources next to frozen exe; repo root in dev)
    CODE_DIR: Path = CODE_DIR
    # User-writable: %APPDATA%/Hilda when running under Electron, else project folder
    WRITABLE_ROOT: Path = WRITABLE_ROOT
    LOGS_DIR: Path = WRITABLE_ROOT / "logs"
    MEMORY_DB: Path = WRITABLE_ROOT / "memory" / "user_patterns.db"

    # ── AI Models ────────────────────────────────────────────────────────────
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_VISION_MODEL: str = os.getenv("OPENAI_VISION_MODEL", "gpt-4o")

    # ── Voice ────────────────────────────────────────────────────────────────
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "tiny")
    TTS_RATE: int = 175
    TTS_VOICE_HINT: str = _merge_tts_voice_hint()
    STT_SILENCE_SECS: float = float(os.getenv("STT_SILENCE_SECS", "1.15"))
    STT_SILENCE_THRESH: int = int(os.getenv("STT_SILENCE_THRESH", "300"))
    STT_MAX_RECORD_SECS: int = int(os.getenv("STT_MAX_RECORD_SECS", "20"))
    STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "en")

    # Wake: whisper_phrase (default, no Picovoice)
    WAKE_MAX_UTTERANCE_SECS: float = float(os.getenv("WAKE_MAX_UTTERANCE_SECS", "4"))
    WAKE_SILENCE_SECS: float = float(os.getenv("WAKE_SILENCE_SECS", "0.55"))
    WAKE_COOLDOWN_SECS: float = float(os.getenv("WAKE_COOLDOWN_SECS", "1.5"))

    SCREEN_CAPTURE_FPS: int = 1

    USE_CLOUD_FALLBACK: bool = os.getenv("USE_CLOUD_FALLBACK", "true").lower() == "true"
    USE_VISION: bool = os.getenv("USE_VISION", "true").lower() == "true"
    USE_COQUI_TTS: bool = os.getenv("USE_COQUI_TTS", "false").lower() == "true"
    USE_EDGE_TTS: bool = os.getenv("USE_EDGE_TTS", "false").lower() == "true"
    EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")
    USE_FAST_LANE: bool = os.getenv("USE_FAST_LANE", "true").lower() == "true"

    WEBSOCKET_HOST: str = "localhost"
    WEBSOCKET_PORT: int = int(os.getenv("WEBSOCKET_PORT", "8765"))

    CLOUD_ROUTING_THRESHOLD: int = 200
    MAX_CONVERSATION_HISTORY: int = 20
    STREAM_TO_UI: bool = os.getenv("STREAM_TO_UI", "true").lower() == "true"
    ASSISTANT_NAME: str = os.getenv("ASSISTANT_NAME", "Hilda")


settings = Settings()

# Back-compat alias for older modules expecting BASE_DIR
BASE_DIR = CODE_DIR
