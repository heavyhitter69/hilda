# Hilda — Desktop voice assistant

> A Windows-first personal assistant: wake word, local “fast lane” for common commands (open apps/folders, lock, type, web search, quick PC health), optional Ollama + OpenAI for harder questions, Dynamic Island UI, and hooks for vision and habits.

---

## What Hilda does

- 🎙️ **Voice-first** — Porcupine wake word (built-in `computer` keyword by default, or your custom “Hey Hilda” `.ppn` via `.env`) → Whisper → action or answer
- ⚡ **Fast lane** — Commands like “open downloads”, “lock”, “google …”, “youtube …”, “disk space” run **without** calling an LLM (`USE_FAST_LANE=true` in `.env`)
- 🧠 **Hybrid brain** — Follow-up reasoning via **Ollama** locally; harder / long prompts optionally go to **OpenAI** when `OPENAI_API_KEY` is set
- 🖥️ **Computer control** — Apps, paths, clipboard paste typing, shell snippets, shutdown/sleep/lock (all filtered by `core/security.py`)
- 👁️ **Vision** — Optional GPT-4o Vision for “what’s on screen” style flows
- 🧠 **Memory** — SQLite log + habit suggestions over time
- 🌊 **Dynamic Island UI** — Electron pill + chat; exposes `window.hilda` (`window.emilio` kept as an alias)

---

## Requirements

| Tool | Install |
|------|---------|
| Python 3.10+ | [python.org](https://python.org) |
| Node.js 20+ | [nodejs.org](https://nodejs.org) |
| Git | [git-scm.com](https://git-scm.com) |
| Ollama | [ollama.ai](https://ollama.ai) |

---

## Quick Start

### 1 — Clone & configure

```bash
git clone <your-repo-url>
cd "emilio ai"
copy .env.example .env
# Edit .env and fill in your keys
```

### 2 — Install Python dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3 — Pull the local AI model

```bash
ollama pull llama3
```

### 4 — Install Electron UI dependencies

```bash
cd ui
npm install
cd ..
```

### 5 — Run from source (developers)

From **`ui`**, a single command starts **both** the Python engine and the Electron shell (do **not** also run `python main.py` in another window—the websocket port would clash):

```bash
cd ui
npm start
```

Logs and `.env` for that session use `%APPDATA%\Hilda` because Electron sets `HILDA_USER_DATA`. To hack on Python only without the island, run `python main.py` from the repo root **instead** (no Electron).

### Packaged installer (`Hilda-Setup.exe`)

Building **`npm run build:full`** inside `ui` bundles **`hilda-engine.exe`** (PyInstaller) into the installer’s `resources/backend/` folder. Double‑clicking **Hilda** after install launches **both** the Electron UI and that engine—no separate terminal.

**Before running `npm run build:backend`:** install project deps into the **same** Python you use to freeze the app: `pip install -r requirements.txt` plus `pip install pyinstaller`. Prefer Python **3.11.x** for reliable Whisper/torch wheels on Windows.

First‑run **Setup wizard** (terms → mic → voice previews → practise recording): appears once unless you use `--skip-setup` or delete `%APPDATA%\Hilda\onboarding-complete.json`.

Optional API keys live in **`%APPDATA%\Hilda\.env`** (seeded from `.env.example` on first launch). Whisper may download its chosen model on first use (~75–150&nbsp;MB for `tiny`).

Voice rehearsal uses **offline Whisper** for transcription only; a bespoke wake phrase still uses a Picovoice **`.ppn`** when configured (see [.env.example](.env.example)).

---

## Configuration (.env)

| Key | Required | Description |
|-----|----------|-------------|
| `OPENAI_API_KEY` | For cloud AI & vision | Get at [platform.openai.com](https://platform.openai.com) |
| `PORCUPINE_ACCESS_KEY` | For custom wake word | Get free at [console.picovoice.ai](https://console.picovoice.ai) |
| `OLLAMA_MODEL` | No (default: llama3) | Local model name |
| `USE_FAST_LANE` | No (default: true) | Pattern-match simple commands locally (recommended) |
| `USE_CLOUD_FALLBACK` | No (default: true) | Route complex requests to GPT-4o |
| `USE_VISION` | No (default: true) | Enable screen vision |
| `USE_COQUI_TTS` | No (default: false) | High-quality TTS (requires ~1 GB model) |
| `ASSISTANT_NAME` | No (default: Hilda) | Spoken name + system prompt persona |

---

## Project Structure

```
emilio ai/
├── main.py                  ← Entry point
├── requirements.txt
├── .env.example
│
├── config/
│   └── settings.py          ← All configuration
│
├── core/
│   ├── agent.py             ← Hybrid router (fast lane + planner + LLMs)
│   ├── fast_lane.py         ← Zero-LLM command patterns
│   ├── planner.py           ← LangChain tool executor
│   ├── security.py          ← Dangerous command filter
│   ├── websocket_server.py  ← UI ↔ Python bridge
│   └── logger.py
│
├── voice/
│   ├── wake_word.py         ← Porcupine / energy fallback
│   ├── speech_to_text.py    ← Whisper STT
│   ├── text_to_speech.py    ← pyttsx3 / Coqui TTS
│   └── audio_manager.py     ← Pipeline coordinator
│
├── plugins/
│   ├── app_control.py       ← Open / close Windows apps
│   ├── diagnostics.py       ← Quick memory / disk snapshot
│   ├── browser_control.py   ← Playwright + default-browser URL open
│   ├── system_control.py    ← Shutdown / Wi-Fi / etc.
│   ├── file_search.py       ← File system search
│   └── mouse_keyboard.py    ← PyAutoGUI wrapper
│
├── vision/
│   ├── screen_capture.py    ← MSS screenshot
│   └── vision_agent.py      ← GPT-4o Vision reasoning
│
├── memory/
│   ├── memory_manager.py    ← SQLite action log
│   └── pattern_learner.py   ← Habit detection
│
├── ui/                      ← Electron Dynamic Island
│   ├── main.js
│   ├── preload.js
│   ├── package.json
│   └── src/
│       ├── index.html
│       ├── styles.css
│       └── renderer.js
│
├── scripts/
│   └── add_to_startup.py    ← Windows boot registration
│
├── website/                 ← Static landing + download button
│   ├── index.html
│   ├── styles.css
│   └── downloads/
│       └── Hilda-Setup.exe  ← `npm run build:full` from /ui (backend + NSIS)
│
├── dist/hilda-engine/       ← PyInstaller output (`npm run build:backend`)
├── hilda-engine.spec
│
└── (logs default to repo when dev; packaged logs → %APPDATA%/Hilda/logs/)
```

---

## Adding Hilda to Windows startup

```bash
python scripts/add_to_startup.py
# To remove:
python scripts/add_to_startup.py --remove
```

---

## Building the desktop installer (website download)

```bash
pip install -r requirements.txt pyinstaller
cd ui
npm install
npm run build:full
```

Produces **`website/downloads/Hilda-Setup.exe`** (Electron + bundled `hilda-engine.exe`). UI‑only rebuild (no backend folder): `npm run build:website` (requires existing `../dist/hilda-engine`).

---

## Wake word

1. Put your Picovoice access key in `.env` as `PORCUPINE_ACCESS_KEY`.
2. Either keep a **built-in** English keyword (`PORCUPINE_KEYWORD=computer` is the default), **or** train **“Hey Hilda”** (or any phrase Picovoice supports) and set `PORCUPINE_KEYWORD_PATH` to the downloaded `.ppn` file path.
3. With no Porcupine key, Hilda falls back to a loud-sound energy detector (better than nothing for dev only).

---

## Safety

Hilda includes a built-in command blocklist (`core/security.py`) that blocks obviously destructive patterns (disk wipes, nuking System32, disabling Defender, etc.). Tool arguments still require sensible use.

Logs rotate under `%APPDATA%\Hilda\logs\hilda.log` when installed; under `logs/hilda.log` in the repo during development.
