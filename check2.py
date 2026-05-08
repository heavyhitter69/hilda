import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

checks = []

# pvporcupine
try:
    import pvporcupine
    checks.append("pvporcupine: OK")
except Exception as e:
    checks.append("pvporcupine: FAIL - " + str(e))

# langchain_openai
try:
    from langchain_openai import ChatOpenAI
    checks.append("langchain_openai: OK")
except Exception as e:
    checks.append("langchain_openai: FAIL - " + str(e)[:60])

# voice tts
try:
    import pyttsx3
    engine = pyttsx3.init()
    engine.stop()
    checks.append("pyttsx3 TTS: OK")
except Exception as e:
    checks.append("pyttsx3 TTS: FAIL - " + str(e)[:60])

# whisper
try:
    import whisper
    checks.append("whisper: OK")
except Exception as e:
    checks.append("whisper: FAIL - " + str(e)[:60])

# pyaudio
try:
    import pyaudio
    checks.append("pyaudio: OK")
except Exception as e:
    checks.append("pyaudio: FAIL - " + str(e)[:60])

# playwright
try:
    from playwright.sync_api import sync_playwright
    checks.append("playwright: OK")
except Exception as e:
    checks.append("playwright: FAIL - " + str(e)[:60])

# pattern learner
try:
    from memory.pattern_learner import PatternLearner
    p = PatternLearner()
    s = p.summarise_patterns()
    checks.append("pattern_learner: OK - " + s[:40])
except Exception as e:
    checks.append("pattern_learner: FAIL - " + str(e)[:60])

for c in checks:
    print(c)
