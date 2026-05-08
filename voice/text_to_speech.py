"""
voice/text_to_speech.py — Synthesise and play assistant speech.

Default engine : pyttsx3 (fast, offline, no downloads needed)
Upgrade path   : Coqui TTS (higher quality, ~1 GB model)
                 Enable by setting USE_COQUI_TTS=true in .env
"""
from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_pyttsx3_engine = None
_pyttsx3_voice_set = False
# After setup wizard: override until process exit (also persisted in user_settings.json).
_active_voice_hint: str | None = None


def set_active_voice_hint(hint: str | None) -> None:
    """Apply a new TTS voice hint (substring match against pyttsx3 voice names)."""
    global _active_voice_hint, _pyttsx3_engine, _pyttsx3_voice_set
    _active_voice_hint = (hint or "").strip() or None
    _pyttsx3_engine = None
    _pyttsx3_voice_set = False


def _lazy_user_voice_from_disk() -> None:
    global _active_voice_hint
    if _active_voice_hint is not None:
        return
    try:
        from config.user_settings_file import get_tts_voice_hint

        h = get_tts_voice_hint(settings.WRITABLE_ROOT)
        if h:
            _active_voice_hint = h
    except Exception:
        pass


def preview_voice_sample(voice_id: str, phrase: str | None = None) -> None:
    """Speak a one-off sample with a specific SAPI voice id (setup wizard)."""
    import pyttsx3

    text = (phrase or "Hi, I'm Hilda. This is how I will sound on your PC.").strip()
    eng = pyttsx3.init()
    try:
        eng.setProperty("rate", settings.TTS_RATE)
        eng.setProperty("voice", voice_id)
        eng.say(text)
        eng.runAndWait()
    finally:
        try:
            eng.stop()
        except Exception:
            pass


# ── pyttsx3 (default) ─────────────────────────────────────────────────────────

def _speak_pyttsx3(text: str) -> None:
    import pyttsx3
    global _pyttsx3_engine, _pyttsx3_voice_set
    _lazy_user_voice_from_disk()
    if _pyttsx3_engine is None:
        _pyttsx3_engine = pyttsx3.init()
    engine = _pyttsx3_engine
    engine.setProperty("rate", settings.TTS_RATE)
    if not _pyttsx3_voice_set:
        # Prefer a female voice (e.g., "Zira" on Windows) (only once; this is slow on Windows)
        try:
            voices = engine.getProperty("voices")
            hint = (_active_voice_hint or getattr(settings, "TTS_VOICE_HINT", "") or "").lower().strip()
            chosen = None

            if hint:
                for v in voices:
                    if hint in (v.name or "").lower():
                        chosen = v
                        break

            # Heuristic fallback: pick a voice that looks female
            if chosen is None:
                for v in voices:
                    nm = (v.name or "").lower()
                    if "zira" in nm or "female" in nm or "woman" in nm:
                        chosen = v
                        break

            if chosen is not None:
                engine.setProperty("voice", chosen.id)
        finally:
            _pyttsx3_voice_set = True
    engine.say(text)
    engine.runAndWait()


# ── Coqui TTS (optional upgrade) ─────────────────────────────────────────────

def _speak_coqui(text: str) -> None:
    import io
    import sounddevice as sd
    import soundfile as sf
    from TTS.api import TTS as CoquiTTS  # type: ignore

    # Lazy singleton
    if not hasattr(_speak_coqui, "_tts"):
        log.info("Loading Coqui TTS model (first load may take a while)…")
        _speak_coqui._tts = CoquiTTS("tts_models/en/ljspeech/tacotron2-DDC")
        log.info("Coqui TTS ready.")

    tts: CoquiTTS = _speak_coqui._tts  # type: ignore
    buf = io.BytesIO()
    tts.tts_to_file(text=text, file_path=buf)
    buf.seek(0)
    data, samplerate = sf.read(buf)
    sd.play(data, samplerate)
    sd.wait()


# ── Public API ────────────────────────────────────────────────────────────────

def speak(text: str) -> None:
    """
    Convert text to speech and play it through the system audio.
    Uses Coqui TTS if USE_COQUI_TTS=true, otherwise pyttsx3.
    """
    if not text or not text.strip():
        return
    # Use ASCII only here; Windows consoles often run cp1252.
    log.info("TTS -> '%s'", text[:80])
    try:
        if settings.USE_COQUI_TTS:
            _speak_coqui(text)
        else:
            _speak_pyttsx3(text)
    except Exception as e:
        log.error("TTS failed: %s. Falling back to pyttsx3.", e)
        try:
            _speak_pyttsx3(text)
        except Exception as e2:
            log.error("pyttsx3 fallback also failed: %s", e2)
