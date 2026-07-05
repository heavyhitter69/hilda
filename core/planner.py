"""
core/planner.py — LangChain-based task planner with Ollama + OpenAI support.

Upgrades:
- Ollama as primary planner (no OpenAI required for basic tool tasks)
- OpenAI as fallback for complex multi-step planning
- All new tools: web search, document reading, email, calendar, contacts
- Plugin system integration for user-defined tools
- Error recovery and retry logic
"""
import asyncio
import re
from typing import Optional

from langchain_core.tools import StructuredTool

from config.settings import settings
from core.logger import get_logger
from core.security import check_command, SecurityResult

log = get_logger(__name__)


# ── Safety decorator ──────────────────────────────────────────────────────────

def _safe(fn):
    """Pre-check the first argument through the security blocklist."""
    def wrapper(*args, **kwargs):
        first = str(args[0]) if args else str(next(iter(kwargs.values()), ""))
        sec: SecurityResult = check_command(first)
        if not sec.safe:
            return f"Blocked: {sec.reason}"
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# ── Core OS tools ─────────────────────────────────────────────────────────────

def _make_core_tools() -> list[StructuredTool]:
    """Build the core tool set from existing plugins."""
    from plugins.app_control import open_application, close_application
    from plugins.browser_control import open_url_sync, search_youtube_sync
    from plugins.system_control import (
        system_action, control_wifi, control_bluetooth,
        set_volume, get_volume, media_control, set_brightness,
        take_screenshot, get_battery_status, get_detailed_system_info,
        empty_recycle_bin, trigger_shortcut,
    )
    from plugins.mouse_keyboard import click, type_text, move_mouse, scroll, paste_text, hotkey
    from plugins.file_search import search_files, open_file, search_and_open
    from plugins.reminder_control import add_reminder, list_reminders
    from plugins.timer_control import set_timer
    from plugins.info_control import get_current_time, get_current_date
    from plugins.diagnostics import quick_pc_snapshot

    tools = [
        StructuredTool.from_function(_safe(open_application), name="open_application",
            description="Open an application by name (e.g., 'chrome', 'notepad', 'spotify')"),
        StructuredTool.from_function(_safe(close_application), name="close_application",
            description="Close/kill a running application by name"),
        StructuredTool.from_function(_safe(open_url_sync), name="open_url",
            description="Open a URL in the browser"),
        StructuredTool.from_function(_safe(search_youtube_sync), name="search_youtube",
            description="Search YouTube for a query"),
        StructuredTool.from_function(_safe(system_action), name="system_action",
            description="Execute system action: shutdown | restart | sleep | lock | cancel"),
        StructuredTool.from_function(_safe(set_volume), name="set_volume",
            description="Control volume: action=up|down|mute|unmute|set, level=0-100"),
        StructuredTool.from_function(get_volume, name="get_volume",
            description="Get current volume level (0-100)"),
        StructuredTool.from_function(_safe(media_control), name="media_control",
            description="Control media playback: play | pause | next | prev"),
        StructuredTool.from_function(_safe(set_brightness), name="set_brightness",
            description="Set screen brightness (0-100)"),
        StructuredTool.from_function(take_screenshot, name="take_screenshot",
            description="Take a screenshot and save to Desktop"),
        StructuredTool.from_function(get_battery_status, name="get_battery_status",
            description="Get battery level and charging status"),
        StructuredTool.from_function(get_detailed_system_info, name="get_system_info",
            description="Get OS, CPU, and RAM info"),
        StructuredTool.from_function(_safe(empty_recycle_bin), name="empty_recycle_bin",
            description="Empty the system recycle bin"),
        StructuredTool.from_function(_safe(click), name="click",
            description="Click at screen position (x, y)"),
        StructuredTool.from_function(_safe(type_text), name="type_text",
            description="Type text via keyboard"),
        StructuredTool.from_function(_safe(paste_text), name="paste_text",
            description="Paste text from clipboard (fast)"),
        StructuredTool.from_function(_safe(move_mouse), name="move_mouse",
            description="Move mouse to (x, y)"),
        StructuredTool.from_function(_safe(scroll), name="scroll",
            description="Scroll up (positive) or down (negative)"),
        StructuredTool.from_function(_safe(hotkey), name="hotkey",
            description="Press a keyboard shortcut (e.g., hotkey('ctrl', 'c'))"),
        StructuredTool.from_function(_safe(search_files), name="search_files",
            description="Search for files by name"),
        StructuredTool.from_function(_safe(open_file), name="open_file",
            description="Open a file with its default application"),
        StructuredTool.from_function(_safe(search_and_open), name="search_and_open",
            description="Search for a file and open the first match"),
        StructuredTool.from_function(_safe(add_reminder), name="add_reminder",
            description="Add a reminder: message, minutes_from_now OR absolute_time (HH:MM)"),
        StructuredTool.from_function(list_reminders, name="list_reminders",
            description="List all active reminders"),
        StructuredTool.from_function(_safe(set_timer), name="set_timer",
            description="Set a timer for X seconds with a message"),
        StructuredTool.from_function(get_current_time, name="get_current_time",
            description="Get the current time"),
        StructuredTool.from_function(get_current_date, name="get_current_date",
            description="Get the current date"),
        StructuredTool.from_function(quick_pc_snapshot, name="pc_diagnostics",
            description="Get PC health: disk space, memory, uptime"),
        StructuredTool.from_function(_safe(control_wifi), name="control_wifi",
            description="Enable or disable Wi-Fi (True/False)"),
        StructuredTool.from_function(_safe(control_bluetooth), name="control_bluetooth",
            description="Enable or disable Bluetooth (True/False)"),
        StructuredTool.from_function(_safe(trigger_shortcut), name="trigger_shortcut",
            description="Trigger system shortcut: project | cast | taskmgr"),
    ]
    return tools


# ── New intelligence tools ────────────────────────────────────────────────────

def _make_intelligence_tools() -> list[StructuredTool]:
    """Web search, document reading, email, calendar, contacts tools."""
    tools = []

    # Web search
    if settings.USE_WEB_SEARCH:
        try:
            from plugins.web_search import search_and_summarize, get_page_content, summarize_url
            tools.extend([
                StructuredTool.from_function(search_and_summarize, name="web_search",
                    description="Search the web and get a summarized answer. Use for weather, news, real-time info."),
                StructuredTool.from_function(get_page_content, name="read_webpage",
                    description="Fetch and extract text content from a URL"),
                StructuredTool.from_function(summarize_url, name="summarize_url",
                    description="Fetch a URL and summarize its content"),
            ])
        except Exception as e:
            log.debug("Web search tools unavailable: %s", e)

    # Document reading
    try:
        from plugins.web_reader import read_document, summarize_document
        tools.extend([
            StructuredTool.from_function(read_document, name="read_document",
                description="Read a local file (PDF, DOCX, TXT, etc.) and return its text"),
            StructuredTool.from_function(summarize_document, name="summarize_document",
                description="Read and summarize a local document, or answer a question about it"),
        ])
    except Exception as e:
        log.debug("Document tools unavailable: %s", e)

    # Email
    if settings.EMAIL_ADDRESS:
        try:
            from plugins.email_integration import check_email, send_email, search_email, summarize_inbox
            tools.extend([
                StructuredTool.from_function(check_email, name="check_email",
                    description="Check inbox for unread emails"),
                StructuredTool.from_function(send_email, name="send_email",
                    description="Send an email: to, subject, body"),
                StructuredTool.from_function(search_email, name="search_email",
                    description="Search emails by subject keyword"),
                StructuredTool.from_function(summarize_inbox, name="summarize_inbox",
                    description="Get an AI summary of unread emails"),
            ])
        except Exception as e:
            log.debug("Email tools unavailable: %s", e)

    # Calendar
    try:
        from plugins.calendar_integration import (
            add_event, get_todays_events, get_upcoming_events, delete_event,
        )
        tools.extend([
            StructuredTool.from_function(add_event, name="add_calendar_event",
                description="Add a calendar event: title, start_time, end_time, description, location"),
            StructuredTool.from_function(get_todays_events, name="get_todays_events",
                description="Get today's scheduled events"),
            StructuredTool.from_function(get_upcoming_events, name="get_upcoming_events",
                description="Get upcoming events for the next N days"),
            StructuredTool.from_function(delete_event, name="delete_event",
                description="Delete a calendar event by title"),
        ])
    except Exception as e:
        log.debug("Calendar tools unavailable: %s", e)

    # Contacts
    try:
        from plugins.contacts_manager import add_contact, find_contact, list_contacts, delete_contact
        tools.extend([
            StructuredTool.from_function(add_contact, name="add_contact",
                description="Add a contact: name, email, phone, notes"),
            StructuredTool.from_function(find_contact, name="find_contact",
                description="Search contacts by name, email, or phone"),
            StructuredTool.from_function(list_contacts, name="list_contacts",
                description="List all saved contacts"),
            StructuredTool.from_function(delete_contact, name="delete_contact",
                description="Delete a contact by name"),
        ])
    except Exception as e:
        log.debug("Contacts tools unavailable: %s", e)

    # Memory tools
    try:
        from memory.semantic_memory import get_semantic_memory
        mem = get_semantic_memory()
        tools.extend([
            StructuredTool.from_function(
                lambda text, category="knowledge": mem.remember(text, category) and f"Remembered: {text[:60]}",
                name="remember",
                description="Store information in memory for later recall"),
            StructuredTool.from_function(
                lambda query: "\n".join(r["text"] for r in mem.recall_all_categories(query, top_k=3)) or "No relevant memories.",
                name="recall_memory",
                description="Search memory for relevant information"),
        ])
    except Exception as e:
        log.debug("Memory tools unavailable: %s", e)

    return tools


# ── Planner ───────────────────────────────────────────────────────────────────

PLANNER_SYSTEM = (
    "You are Hilda's task planner. Given a user request, decompose it into "
    "precise tool calls and execute them in order. Always use the minimum "
    "number of steps needed. If a tool fails, try an alternative approach. "
    "After completing all steps, summarize what you did in one sentence."
)


class HildaPlanner:
    """LangChain-powered planner with Ollama primary + OpenAI fallback."""

    def __init__(self) -> None:
        self._tools: Optional[list] = None
        self._agent = None

    def _get_tools(self) -> list:
        if self._tools is None:
            self._tools = _make_core_tools() + _make_intelligence_tools()

            # Load user plugins
            try:
                from plugins.plugin_loader import get_all_plugin_tools
                user_tools = get_all_plugin_tools()
                if user_tools:
                    self._tools.extend(user_tools)
                    log.info("Loaded %d user plugin tools.", len(user_tools))
            except Exception as e:
                log.debug("Plugin loading failed: %s", e)

            log.info("Planner initialized with %d tools.", len(self._tools))
        return self._tools

    def _build_agent(self):
        """Build the LangChain agent."""
        if self._agent is not None:
            return self._agent

        tools = self._get_tools()

        # Try OpenAI first (better function calling)
        if settings.OPENAI_API_KEY:
            try:
                from langchain_openai import ChatOpenAI
                from langchain.agents import create_tool_calling_agent, AgentExecutor
                from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

                llm = ChatOpenAI(
                    model=settings.OPENAI_MODEL,
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0.0,
                    max_tokens=500,
                )

                prompt = ChatPromptTemplate.from_messages([
                    ("system", PLANNER_SYSTEM),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ])

                agent = create_tool_calling_agent(llm, tools, prompt)
                self._agent = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    max_iterations=8,
                    handle_parsing_errors=True,
                    verbose=False,
                )
                log.info("Planner using OpenAI %s.", settings.OPENAI_MODEL)
                return self._agent
            except Exception as e:
                log.warning("OpenAI planner init failed: %s", e)

        # Fallback: direct tool matching (no LLM agent)
        log.info("Planner using direct tool matching (no LLM agent key available).")
        self._agent = "direct"
        return self._agent

    async def run(self, user_text: str) -> str:
        """Execute a task using the planner."""
        agent = self._build_agent()

        if agent == "direct":
            return await self._direct_tool_mode(user_text)

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: agent.invoke({"input": user_text}),
            )
            output = result.get("output", "")
            if output:
                return output
            return "Done."
        except Exception as e:
            log.error("Planner execution error: %s", e)
            # Retry with direct mode
            return await self._direct_tool_mode(user_text)

    async def _direct_tool_mode(self, user_text: str) -> str:
        """Fallback: try to match user text to a tool directly."""
        from core.fast_lane import try_dispatch

        result = try_dispatch(user_text)
        if result is not None:
            return result

        # Try Ollama for simple tool routing
        try:
            import ollama
            tools = self._get_tools()
            tool_descriptions = "\n".join(
                f"- {t.name}: {t.description}" for t in tools[:30]
            )
            response = ollama.chat(
                model=settings.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": f"You are a task router. Given the user's request, suggest which tool to use and with what arguments. Available tools:\n{tool_descriptions}"},
                    {"role": "user", "content": user_text},
                ],
                options={"temperature": 0.0, "num_predict": 200},
            )
            suggestion = response["message"]["content"].strip()

            # Try to find and execute the suggested tool
            for tool in tools:
                if tool.name.lower() in suggestion.lower():
                    # Extract likely argument
                    arg = re.sub(
                        r"(?i)(use|call|run|execute)\s+\w+\s*(with|for|on)?\s*",
                        "", user_text
                    ).strip()
                    try:
                        result = tool.invoke(arg or user_text)
                        return str(result)
                    except Exception:
                        continue

            return suggestion
        except Exception as e:
            log.error("Direct tool mode failed: %s", e)
            return f"I couldn't process that request without an AI planning model. Error: {e}"
