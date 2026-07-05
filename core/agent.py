"""
core/agent.py — Intelligent hybrid router for Hilda.

Routing logic (upgraded):
  1. Security check (blocklist)
  2. Intent classification (LLM-based with regex fallback)
  3. Route by intent:
     - TOOL_ACTION → fast lane → LangChain planner
     - WEB_SEARCH → web search + summarize
     - MEMORY_QUERY → semantic memory recall
     - VISION → GPT-4o Vision
     - EMAIL → email tools
     - CALENDAR → calendar tools
     - CREATIVE → Ollama (uncapped) or OpenAI
     - QUESTION → Ollama (uncapped) or OpenAI
     - CONVERSATION → Ollama (quick chat)
  4. Context injection (active window, user facts, memories)
  5. Memory storage (semantic + facts extraction)
  6. Conversation persistence
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


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


class HildaAgent:
    """Intelligent assistant that routes queries with context awareness and memory."""

    def __init__(self) -> None:
        self._history: list[dict] = []
        self._planner = None
        self._conversation = None
        self._conversation_store = None
        self._is_voice_input = False
        self._init_conversation()

    def _init_conversation(self) -> None:
        """Load or create a conversation thread."""
        try:
            from memory.conversation_store import ConversationStore, ConversationThread
            self._conversation_store = ConversationStore()
            # Try to resume recent conversation
            recent = self._conversation_store.get_latest(
                max_age_minutes=settings.CONVERSATION_RESUME_MINUTES
            )
            if recent:
                self._conversation = recent
                self._history = recent.get_history(settings.MAX_CONVERSATION_HISTORY)
                log.info("Resumed conversation '%s' (%d messages)", recent.title, len(recent.messages))
            else:
                self._conversation = ConversationThread()
                log.info("Started new conversation: %s", self._conversation.id)
        except Exception as e:
            log.warning("Conversation init failed: %s", e)
            from memory.conversation_store import ConversationThread
            self._conversation = ConversationThread()

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

    def _build_system_prompt(self, user_text: str) -> str:
        """Build a rich, context-aware system prompt."""
        try:
            from core.personality import build_system_prompt

            # Gather context
            context = None
            if settings.USE_CONTEXT_AWARENESS:
                try:
                    from core.context_awareness import build_context_snapshot
                    context = build_context_snapshot()
                except Exception as e:
                    log.debug("Context snapshot failed: %s", e)

            # Gather user facts
            user_facts = None
            if settings.USE_SEMANTIC_MEMORY:
                try:
                    from memory.semantic_memory import get_semantic_memory
                    mem = get_semantic_memory()
                    user_facts = mem.get_user_facts(top_k=10)
                except Exception as e:
                    log.debug("User facts retrieval failed: %s", e)

            # Gather relevant memories
            relevant_memories = None
            if settings.USE_SEMANTIC_MEMORY:
                try:
                    from memory.semantic_memory import get_semantic_memory
                    mem = get_semantic_memory()
                    results = mem.recall(user_text, category="conversations", top_k=3)
                    relevant_memories = [
                        r["text"] for r in results
                        if r.get("distance", 1.0) < 0.6
                    ]
                except Exception as e:
                    log.debug("Memory recall failed: %s", e)

            # Get conversation summary if history is long
            conv_summary = None
            if self._conversation and len(self._history) > 20:
                conv_summary = self._conversation.summary

            return build_system_prompt(
                context=context,
                user_facts=user_facts,
                relevant_memories=relevant_memories,
                conversation_summary=conv_summary,
                is_voice=self._is_voice_input,
            )
        except Exception as e:
            log.warning("Personality prompt failed, using fallback: %s", e)
            name = (settings.ASSISTANT_NAME or "Hilda").strip()
            return (
                f"You are {name}, a smart, friendly desktop AI assistant on Windows. "
                f"Keep responses concise (1-2 sentences for voice, more for text)."
            )

    async def _run_tools_pipeline(self, user_text: str) -> str:
        """Fast pattern match first; then the LangChain planner."""
        from core.fast_lane import try_dispatch

        quick = try_dispatch(user_text)
        if quick is not None:
            return quick
        try:
            return await self._get_planner().run(user_text)
        except Exception as e:
            log.error("Planner error: %s", e)
            return f"I ran into an error executing that task: {e}"

    async def _handle_web_search(self, user_text: str) -> str:
        """Handle web search requests."""
        try:
            from plugins.web_search import search_and_summarize
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, search_and_summarize, user_text)
        except Exception as e:
            log.error("Web search failed: %s", e)
            return f"I couldn't search the web: {e}"

    async def _handle_memory_query(self, user_text: str) -> str:
        """Handle memory/recall requests."""
        try:
            from memory.semantic_memory import get_semantic_memory
            mem = get_semantic_memory()
            results = mem.recall_all_categories(user_text, top_k=5)
            if not results:
                return "I don't have any relevant memories about that."

            context = "\n".join(f"- {r['text']}" for r in results[:5])
            # Use LLM to formulate a natural response
            messages = [
                {"role": "system", "content": "Answer the user's question using ONLY the provided memories. Be concise."},
                {"role": "user", "content": f"Question: {user_text}\n\nRelevant memories:\n{context}"},
            ]
            return await self._call_ollama(messages)
        except Exception as e:
            log.error("Memory query failed: %s", e)
            return "I had trouble searching my memory."

    async def _handle_email(self, user_text: str) -> str:
        """Route email-related requests."""
        low = user_text.lower()
        loop = asyncio.get_event_loop()
        try:
            from plugins.email_integration import check_email, summarize_inbox, search_email

            if any(w in low for w in ("check", "unread", "inbox", "new email")):
                return await loop.run_in_executor(None, check_email, 5)
            if "summarize" in low or "summary" in low:
                return await loop.run_in_executor(None, summarize_inbox)
            if "search" in low or "find" in low:
                # Extract search query
                q = re.sub(r"(?i)(search|find)\s+(for\s+)?email(s)?\s+(about|for|with)?\s*", "", user_text).strip()
                return await loop.run_in_executor(None, search_email, q)
            return await loop.run_in_executor(None, check_email, 5)
        except Exception as e:
            return f"Email error: {e}"

    async def _handle_calendar(self, user_text: str) -> str:
        """Route calendar-related requests."""
        low = user_text.lower()
        loop = asyncio.get_event_loop()
        try:
            from plugins.calendar_integration import get_todays_events, get_upcoming_events

            if any(w in low for w in ("today", "today's", "schedule")):
                return await loop.run_in_executor(None, get_todays_events)
            if any(w in low for w in ("upcoming", "next", "week", "this week")):
                return await loop.run_in_executor(None, get_upcoming_events, 7)
            # For add requests, delegate to planner
            return await self._get_planner().run(user_text)
        except Exception as e:
            return f"Calendar error: {e}"

    async def _call_ollama(self, messages: list[dict]) -> str:
        try:
            import ollama
            response = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=messages,
                options={
                    "temperature": 0.3,
                    "num_predict": settings.OLLAMA_MAX_TOKENS,
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
                        "num_predict": settings.OLLAMA_MAX_TOKENS,
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
                max_tokens=settings.OLLAMA_MAX_TOKENS,
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
            max_tokens=settings.OLLAMA_MAX_TOKENS,
            temperature=0.3,
            stream=True,
        )
        async for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content
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

        system_prompt = self._build_system_prompt(user_text)
        messages = [{"role": "system", "content": system_prompt}] + self._history

        # Classify intent
        from core.intent_classifier import classify
        intent = classify(user_text)

        if intent.category == "TOOL_ACTION":
            response = await self._run_tools_pipeline(user_text)
        elif intent.category == "WEB_SEARCH":
            response = await self._handle_web_search(user_text)
        elif intent.category == "MEMORY_QUERY":
            response = await self._handle_memory_query(user_text)
        elif intent.category == "VISION":
            try:
                from vision.vision_agent import describe_screen
                response = await describe_screen()
            except Exception as e:
                response = f"Vision error: {e}"
        elif intent.category == "EMAIL":
            response = await self._handle_email(user_text)
        elif intent.category == "CALENDAR":
            response = await self._handle_calendar(user_text)
        elif self._should_use_cloud(user_text):
            response = await self._call_openai(messages)
        else:
            response = await self._call_ollama(messages)

        self._history.append({"role": "assistant", "content": response})
        return response

    async def handle_text(self, text: str, is_voice: bool = True) -> None:
        from core import websocket_server
        from voice.text_to_speech import speak

        self._is_voice_input = is_voice
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

        # Store in conversation thread
        if self._conversation:
            self._conversation.add_message("user", text)

        system_prompt = self._build_system_prompt(text)
        messages = [{"role": "system", "content": system_prompt}] + self._history

        response = ""

        # Classify intent
        from core.intent_classifier import classify
        intent = classify(text, use_llm=settings.USE_INTENT_CLASSIFIER)

        # ── Direct-action intents (no streaming) ──────────────────────────
        if intent.category in ("TOOL_ACTION", "WEB_SEARCH", "MEMORY_QUERY",
                                "VISION", "EMAIL", "CALENDAR"):
            try:
                if intent.category == "TOOL_ACTION":
                    response = await self._run_tools_pipeline(text)
                elif intent.category == "WEB_SEARCH":
                    response = await self._handle_web_search(text)
                elif intent.category == "MEMORY_QUERY":
                    response = await self._handle_memory_query(text)
                elif intent.category == "VISION":
                    from vision.vision_agent import describe_screen
                    response = await describe_screen()
                elif intent.category == "EMAIL":
                    response = await self._handle_email(text)
                elif intent.category == "CALENDAR":
                    response = await self._handle_calendar(text)
            except Exception as e:
                log.error("Intent handling error: %s", e)
                response = f"I ran into an error: {e}"

            await websocket_server.broadcast_state("speaking")
            await websocket_server.broadcast_message("assistant", response)

        # ── Streaming LLM intents ─────────────────────────────────────────
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

        # ── TTS ───────────────────────────────────────────────────────────
        loop = asyncio.get_event_loop()
        if "tts_first_task" in locals() and locals().get("tts_first_task") is not None:
            try:
                await locals()["tts_first_task"]
            except Exception:
                pass
            spoken_prefix = (locals().get("first_sentence") or "").strip()
            remaining = response
            if spoken_prefix and remaining.startswith(spoken_prefix):
                remaining = remaining[len(spoken_prefix):].lstrip()
            if remaining.strip():
                await loop.run_in_executor(None, speak, remaining)
        else:
            await loop.run_in_executor(None, speak, response)

        await websocket_server.broadcast_state("idle")

        # ── Store in conversation + memory ────────────────────────────────
        if self._conversation:
            self._conversation.add_message("assistant", response)
            # Auto-title after 3 turns
            if self._conversation.turn_count == 3:
                try:
                    from memory.conversation_store import auto_title_conversation
                    title = auto_title_conversation(self._conversation.messages)
                    self._conversation.title = title
                except Exception:
                    pass
            # Save periodically
            if self._conversation_store and self._conversation.turn_count % 3 == 0:
                try:
                    self._conversation_store.save(self._conversation)
                except Exception as e:
                    log.debug("Conversation save failed: %s", e)

        # SQLite action log (legacy)
        try:
            from memory.memory_manager import MemoryManager
            MemoryManager().log_action(text, response)
        except Exception as e:
            log.warning("Memory log failed: %s", e)

        # Semantic memory storage
        if settings.USE_SEMANTIC_MEMORY:
            try:
                from memory.semantic_memory import get_semantic_memory
                mem = get_semantic_memory()
                mem.remember(
                    f"User: {text}\nAssistant: {response[:300]}",
                    category="conversations",
                )
            except Exception as e:
                log.debug("Semantic memory store failed: %s", e)

        # Fact extraction (background, non-blocking)
        if settings.USE_FACT_EXTRACTION:
            try:
                from memory.fact_extractor import extract_and_store
                asyncio.get_event_loop().run_in_executor(
                    None, extract_and_store, text, response
                )
            except Exception as e:
                log.debug("Fact extraction failed: %s", e)

        self._history.append({"role": "assistant", "content": response})
        self._trim_history()

    def save_conversation(self) -> None:
        """Save the current conversation to disk (called on shutdown)."""
        if self._conversation and self._conversation_store and self._conversation.messages:
            try:
                # Summarize if long
                if len(self._conversation.messages) > 10 and not self._conversation.summary:
                    try:
                        from memory.conversation_summarizer import summarize_messages
                        self._conversation.summary = summarize_messages(
                            self._conversation.messages[:20]
                        )
                    except Exception:
                        pass
                self._conversation_store.save(self._conversation)
                log.info("Conversation saved: %s (%d messages)",
                         self._conversation.id, len(self._conversation.messages))
            except Exception as e:
                log.error("Conversation save failed: %s", e)


def get_agent() -> HildaAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = HildaAgent()
    return _agent_instance
