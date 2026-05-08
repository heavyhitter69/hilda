"""
core/agent.py — Hybrid router for Hilda.

Routing logic:
  - Obvious desktop commands → fast local intent router (no LLM)
  - Remaining control tasks   → LangChain tool planner (optional OpenAI)
  - Chat / reasoning          → Ollama locally, or OpenAI when complexity keywords match
  - Vision requests           → OpenAI GPT-4o Vision (when enabled)
"""
import asyncio
import re
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

from config.settings import settings
from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)

_openai_client: Optional[AsyncOpenAI] = None
_agent_instance: Optional["HildaAgent"] = None

_EXPLANATORY = re.compile(
    r"(?i)\b(how\s+(do\s+i|to|does|can\s+i|would\s+i)|explain|why\s+(is|does|are|will|wont|won't)|"
    r"what\s+(is|are)|tell\s+me\s+(about|how))\b",
)
_TOOL_VERB = re.compile(
    r"(?i)\b(open|launch|start|close|quit|exit|kill|shutdown|restart|reboot|sleep|suspend|lock|unlock|"
    r"type|paste|scroll|navigate|dictate|run|powershell|play|find|search|download|show\s+me|"
    r"go\s+to|open\s+url|youtube|google)\b|\b(https?://|www\.)\S+",
)


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


NAME = (settings.ASSISTANT_NAME or "Hilda").strip()
SYSTEM_PROMPT = f"""You are {NAME}, a smart, friendly, extremely crisp desktop AI assistant on Windows.
You help the user control their computer, answer questions, and automate tasks.
CRITICAL: You are an audio-first assistant. You must keep ALL spoken responses to an absolute maximum of 1 or 2 very short sentences. DO NOT YACK. Do not ramble. Get straight to the point.
When a task requires multiple steps, think step-by-step and call appropriate tools.
Never perform dangerous or destructive actions on the system."""


def _looks_like_tool_request(text: str) -> bool:
    """True when we should attempt tool execution (after skipping pure Q&A phrasing)."""
    low = text.lower().strip()
    if not low:
        return False
    if _EXPLANATORY.search(text) and not re.match(
        r"(?i)^\s*(open|launch|start|close|type|paste|run|scroll|shutdown|restart|find|search|show)\b",
        low,
    ):
        return False
    return bool(_TOOL_VERB.search(text))


class HildaAgent:
    """Routes queries between the fast lane, planner+tools, and LLM backends."""

    def __init__(self) -> None:
        self._history: list[dict] = []
        self._planner = None

    def _get_planner(self):
        if self._planner is None:
            from core.planner import HildaPlanner

            self._planner = HildaPlanner()
        return self._planner

    def _should_use_cloud(self, text: str) -> bool:
        if not settings.USE_CLOUD_FALLBACK or not settings.OPENAI_API_KEY:
            return False
        complex_keywords = [
            "explain", "analyze", "analyse", "write", "summarize", "translate",
            "code", "script", "compare", "research", "vision", "screenshot",
            "what do you see", "look at",
        ]
        text_lower = text.lower()
        if len(text) > settings.CLOUD_ROUTING_THRESHOLD:
            return True
        return any(kw in text_lower for kw in complex_keywords)

    def _trim_history(self) -> None:
        max_pairs = settings.MAX_CONVERSATION_HISTORY * 2
        if len(self._history) > max_pairs:
            self._history = self._history[-max_pairs:]

    async def _run_tools_pipeline(self, user_text: str) -> str:
        """Fast pattern match first; only then the LangChain/OpenAI planner."""
        from core.fast_lane import try_dispatch

        quick = try_dispatch(user_text)
        if quick is not None:
            return quick
        try:
            return await self._get_planner().run(user_text)
        except Exception as e:
            log.error("Planner error: %s", e)
            return f"I ran into an error executing that task: {e}"

    async def _call_ollama(self, messages: list[dict]) -> str:
        try:
            import ollama
            response = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=messages,
                options={
                    "temperature": 0.3,
                    "num_predict": 100,
                },
            )
            return response["message"]["content"]
        except Exception as e:
            log.error("Ollama call failed: %s", e)
            if settings.USE_CLOUD_FALLBACK and settings.OPENAI_API_KEY:
                log.info("Falling back to cloud model after Ollama failure.")
                return await self._call_openai(messages)
            return "I'm having trouble connecting to my local AI model. Please check that Ollama is running."

    async def _call_ollama_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        import ollama

        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _run() -> None:
            try:
                for part in ollama.chat(
                    model=settings.OLLAMA_MODEL,
                    messages=messages,
                    stream=True,
                    options={
                        "temperature": 0.3,
                        "num_predict": 120,
                    },
                ):
                    delta = (part.get("message", {}) or {}).get("content", "")
                    if delta:
                        loop.call_soon_threadsafe(queue.put_nowait, delta)
            except Exception as e:
                loop.call_soon_threadsafe(queue.put_nowait, f"\n[Ollama error: {e}]")
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        worker = asyncio.create_task(asyncio.to_thread(_run))

        while True:
            item = await queue.get()
            if item is None:
                break
            yield item
        await worker

    async def _call_openai(self, messages: list[dict]) -> str:
        try:
            client = _get_openai()
            resp = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                max_tokens=100,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            log.error("OpenAI call failed: %s", e)
            return "I couldn't reach the cloud model. Please check your API key or internet connection."

    async def _call_openai_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        client = _get_openai()
        stream = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=140,
            temperature=0.3,
            stream=True,
        )
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content  # type: ignore[attr-defined]
            except Exception:
                delta = None
            if delta:
                yield delta

    async def think(self, user_text: str) -> str:
        sec = check_command(user_text)
        if not sec.safe:
            return f"I can't do that. {sec.reason}"

        self._history.append({"role": "user", "content": user_text})
        self._trim_history()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history

        if _looks_like_tool_request(user_text):
            log.info("Routing to tools pipeline: '%s'", user_text[:60])
            response = await self._run_tools_pipeline(user_text)
        elif self._should_use_cloud(user_text):
            log.info("Routing to cloud (OpenAI): '%s'", user_text[:60])
            response = await self._call_openai(messages)
        else:
            log.info("Routing to local (Ollama): '%s'", user_text[:60])
            response = await self._call_ollama(messages)

        self._history.append({"role": "assistant", "content": response})
        return response

    async def handle_text(self, text: str) -> None:
        from core import websocket_server
        from voice.text_to_speech import speak

        log.info("User said: %s", text)
        await websocket_server.broadcast_state("thinking")
        await websocket_server.broadcast_message("user", text)

        sec = check_command(text)
        if not sec.safe:
            response = f"I can't do that. {sec.reason}"
            await websocket_server.broadcast_state("speaking")
            await websocket_server.broadcast_message("assistant", response)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, speak, response)
            await websocket_server.broadcast_state("idle")
            return

        self._history.append({"role": "user", "content": text})
        self._trim_history()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._history

        response = ""
        if _looks_like_tool_request(text):
            try:
                response = await self._run_tools_pipeline(text)
            except Exception as e:
                log.error("Tools pipeline error: %s", e)
                response = f"I ran into an error executing that task: {e}"
            await websocket_server.broadcast_state("speaking")
            await websocket_server.broadcast_message("assistant", response)
        else:
            use_cloud = self._should_use_cloud(text)
            stream_ok = bool(settings.STREAM_TO_UI)

            if stream_ok:
                await websocket_server.broadcast_message_start("assistant")

            try:
                if use_cloud:
                    if stream_ok:
                        first_spoken = False
                        first_chunk = ""
                        tts_first_task: Optional[asyncio.Task] = None
                        async for delta in self._call_openai_stream(messages):
                            response += delta
                            await websocket_server.broadcast_delta("assistant", delta)
                            if not first_spoken:
                                first_chunk += delta
                                if any(p in first_chunk for p in (".", "!", "?", "\n")) and len(first_chunk.strip()) >= 12:
                                    first_sentence = first_chunk.split("\n", 1)[0]
                                    for sep in (".", "!", "?"):
                                        if sep in first_sentence:
                                            first_sentence = first_sentence.split(sep, 1)[0] + sep
                                            break
                                    first_sentence = first_sentence.strip()
                                    if first_sentence:
                                        await websocket_server.broadcast_state("speaking")
                                        loop = asyncio.get_event_loop()
                                        tts_first_task = asyncio.create_task(
                                            loop.run_in_executor(None, speak, first_sentence)
                                        )
                                        first_spoken = True
                    else:
                        response = await self._call_openai(messages)
                else:
                    if stream_ok:
                        first_spoken = False
                        first_chunk = ""
                        tts_first_task = None
                        async for delta in self._call_ollama_stream(messages):
                            response += delta
                            await websocket_server.broadcast_delta("assistant", delta)
                            if not first_spoken:
                                first_chunk += delta
                                if any(p in first_chunk for p in (".", "!", "?", "\n")) and len(first_chunk.strip()) >= 12:
                                    first_sentence = first_chunk.split("\n", 1)[0]
                                    for sep in (".", "!", "?"):
                                        if sep in first_sentence:
                                            first_sentence = first_sentence.split(sep, 1)[0] + sep
                                            break
                                    first_sentence = first_sentence.strip()
                                    if first_sentence:
                                        await websocket_server.broadcast_state("speaking")
                                        loop = asyncio.get_event_loop()
                                        tts_first_task = asyncio.create_task(
                                            loop.run_in_executor(None, speak, first_sentence)
                                        )
                                        first_spoken = True
                    else:
                        response = await self._call_ollama(messages)
            except Exception as e:
                log.error("LLM streaming error: %s", e)
                response = "I hit an error generating that response."

            if stream_ok:
                await websocket_server.broadcast_message_end("assistant")
            else:
                await websocket_server.broadcast_message("assistant", response)

            await websocket_server.broadcast_state("speaking")

        loop = asyncio.get_event_loop()
        if "tts_first_task" in locals() and locals().get("tts_first_task") is not None:
            try:
                await locals()["tts_first_task"]
            except Exception:
                pass
            spoken_prefix = (locals().get("first_sentence") or "").strip()
            remaining = response
            if spoken_prefix and remaining.startswith(spoken_prefix):
                remaining = remaining[len(spoken_prefix) :].lstrip()
            if remaining.strip():
                await loop.run_in_executor(None, speak, remaining)
        else:
            await loop.run_in_executor(None, speak, response)

        await websocket_server.broadcast_state("idle")

        try:
            from memory.memory_manager import MemoryManager

            MemoryManager().log_action(text, response)
        except Exception as e:
            log.warning("Memory log failed: %s", e)

        self._history.append({"role": "assistant", "content": response})
        self._trim_history()


def get_agent() -> HildaAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HildaAgent()
    return _agent_instance
