"""
voice/speech_to_text.py — Convert recorded audio to text using Whisper.

The recording starts when triggered (post-wake-word) and stops after
a configurable silence timeout.
"""
import io
import wave
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import whisper

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_SAMPLE_RATE   = 16000
_CHANNELS      = 1
_CHUNK         = 1024
_SILENCE_SECS  = float(getattr(settings, "STT_SILENCE_SECS", 0.9))
_SILENCE_THRESH = int(getattr(settings, "STT_SILENCE_THRESH", 100))
_MAX_RECORD_SECS = int(getattr(settings, "STT_MAX_RECORD_SECS", 20))

# Load model lazily
_model: Optional[whisper.Whisper] = None


def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        log.info("Loading Whisper model '%s' (first load may take a moment)…",
                 settings.WHISPER_MODEL)
        _model = whisper.load_model(settings.WHISPER_MODEL)
        log.info("Whisper model loaded.")
    return _model


def record_until_silence() -> bytes:
    """
    Record from the microphone until silence is detected.
    Returns raw PCM bytes (16-bit signed, 16 kHz, mono).
    """
    log.info("Recording… (speak now)")
    frames: list[bytes] = []
    silent_chunks = 0
    max_silent = int(_SILENCE_SECS * _SAMPLE_RATE / _CHUNK)
    max_total = int(_MAX_RECORD_SECS * _SAMPLE_RATE / _CHUNK)

    with sd.RawInputStream(samplerate=_SAMPLE_RATE, blocksize=_CHUNK,
                           dtype='int16', channels=_CHANNELS) as stream:
        for _ in range(max_total):
            data, overflowed = stream.read(_CHUNK)
            data_bytes = bytes(data)
            frames.append(data_bytes)
            amplitude = np.abs(np.frombuffer(data_bytes, dtype=np.int16)).max()
            if amplitude < _SILENCE_THRESH:
                silent_chunks += 1
            else:
                silent_chunks = 0
            if silent_chunks >= max_silent:
                break

    log.info("Recording finished. %d frames captured.", len(frames))
    return b"".join(frames)


def pcm_to_wav(pcm: bytes) -> bytes:
    """Wrap raw PCM bytes in a WAV container (in memory)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(pcm)
    return buf.getvalue()


def transcribe(pcm: bytes, initial_prompt: str | None = None) -> str:
    """
    Transcribe PCM audio to text using Whisper.
    Optional initial_prompt biases recognition toward enrolled phrases / accent context.
    """
    model = _get_model()
    wav_bytes = pcm_to_wav(pcm)
    audio_np = (
        np.frombuffer(wav_bytes[44:], dtype=np.int16).astype(np.float32) / 32768.0
    )
    kw: dict = {"language": settings.STT_LANGUAGE, "fp16": False}
    if initial_prompt and initial_prompt.strip():
        kw["initial_prompt"] = initial_prompt.strip()
    result = model.transcribe(audio_np, **kw)
    text = result.get("text", "").strip()
    log.info("Transcribed: '%s'", text)
    return text


def record_next_utterance(
    max_secs: float = 5.0,
    silence_secs: float | None = None,
    silence_thresh: int | None = None,
    speech_chunks_needed: int = 4,
    on_speech_start: Callable[[], None] | None = None,
) -> bytes:
    """
    Wait until the user starts speaking (energy above threshold), then record
    until silence or max_secs. Used for wake-word passes without burning CPU on silence.
    """
    ss = float(silence_secs if silence_secs is not None else settings.STT_SILENCE_SECS)
    st = int(silence_thresh if silence_thresh is not None else settings.STT_SILENCE_THRESH)

    frames: list[bytes] = []
    loud_run = 0
    phase = "wait_speech"
    _speech_cb_fired = False

    max_chunks_wait = int(25 * _SAMPLE_RATE / _CHUNK)
    waited = 0

    try:
        with sd.RawInputStream(samplerate=_SAMPLE_RATE, blocksize=_CHUNK,
                               dtype='int16', channels=_CHANNELS) as stream:
            while phase == "wait_speech" and waited < max_chunks_wait:
                data, overflowed = stream.read(_CHUNK)
                data_bytes = bytes(data)
                waited += 1
                amp = int(np.abs(np.frombuffer(data_bytes, dtype=np.int16)).max())
                if amp >= st:
                    loud_run += 1
                    if loud_run >= speech_chunks_needed:
                        frames.append(data_bytes)
                        phase = "recording"
                        if on_speech_start and not _speech_cb_fired:
                            _speech_cb_fired = True
                            try:
                                on_speech_start()
                            except Exception:
                                pass
                        break
                else:
                    loud_run = 0

            if phase != "recording":
                return b""

            silent_chunks = 0
            max_silent = int(ss * _SAMPLE_RATE / _CHUNK)
            max_total = int(max_secs * _SAMPLE_RATE / _CHUNK)

            while len(frames) < max_total:
                data, overflowed = stream.read(_CHUNK)
                data_bytes = bytes(data)
                frames.append(data_bytes)
                amp = int(np.abs(np.frombuffer(data_bytes, dtype=np.int16)).max())
                if amp < st:
                    silent_chunks += 1
                    if silent_chunks >= max_silent:
                        break
                else:
                    silent_chunks = 0

            return b"".join(frames)
    except Exception:
        raise


def listen_and_transcribe() -> str:
    """Record until silence, then transcribe with enrollment-based bias if available."""
    from voice.enrollment_store import build_whisper_initial_prompt

    pcm = record_until_silence()
    prompt = build_whisper_initial_prompt()
    return transcribe(pcm, initial_prompt=prompt or None)
