"""
core/planner.py — LangChain-based task planner for Hilda.

Converts natural-language user requests into ordered tool calls.
All tools pass through security.check_command before execution.
"""
import asyncio
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config.settings import settings
from core.logger import get_logger
from core.security import check_command

log = get_logger(__name__)


# ── Tool input schemas ────────────────────────────────────────────────────────

class AppInput(BaseModel):
    name: str = Field(description="Name of the application to open, e.g. 'notepad', 'chrome', 'vscode'")

class CloseAppInput(BaseModel):
    name: str = Field(description="Name of the application/process to close, e.g. 'notepad', 'chrome'")

class BrowserInput(BaseModel):
    url: str = Field(description="URL to navigate to")

class SearchInput(BaseModel):
    query: str = Field(description="Search query to use on YouTube or Google")

class TypeInput(BaseModel):
    text: str = Field(description="Text to type via keyboard")

class PasteInput(BaseModel):
    text: str = Field(description="Text to paste quickly via clipboard + Ctrl+V")

class ClickInput(BaseModel):
    x: int = Field(description="X screen coordinate")
    y: int = Field(description="Y screen coordinate")

class HotkeyInput(BaseModel):
    keys: list[str] = Field(description="Hotkey combination, e.g. ['ctrl','c'] or ['alt','tab']")

class ScrollInput(BaseModel):
    clicks: int = Field(description="Scroll amount (positive up, negative down)")

class FileInput(BaseModel):
    query: str = Field(description="File name or keyword to search for")
    path: str = Field(default="C:\\", description="Root path to search from")

class SearchOpenFileInput(BaseModel):
    query: str = Field(description="File name or keyword to search for, then open the best match")
    path: str = Field(default="C:\\Users", description="Root path to search from")

class OpenPathInput(BaseModel):
    path: str = Field(description="Exact file or folder path to open")

class SystemInput(BaseModel):
    action: str = Field(description="System action: shutdown | restart | sleep | lock")

class CommandInput(BaseModel):
    command: str = Field(description="PowerShell command to run (keep it short and safe)")

class DictationInput(BaseModel):
    mode: str = Field(default="paste", description="How to enter text: paste | type")

class HardwareInput(BaseModel):
    state: bool = Field(description="True to enable/turn on, False to disable/turn off")

class BrightnessInput(BaseModel):
    level: int = Field(description="Brightness level from 0 to 100")

class VolumeInput(BaseModel):
    action: str = Field(description="Volume action: up | down | mute")

class MediaInput(BaseModel):
    action: str = Field(description="Media action: play | pause | next | prev")

class ShortcutInput(BaseModel):
    action: str = Field(description="Shortcut action: project | cast | taskmgr")

class ReminderInput(BaseModel):
    message: str = Field(description="The message of the reminder")
    minutes_from_now: Optional[int] = Field(None, description="Minutes from now to trigger")
    absolute_time: Optional[str] = Field(None, description="Absolute time string like HH:MM")

class TimerInput(BaseModel):
    seconds: int = Field(description="Number of seconds for the timer")
    message: str = Field(default="Timer", description="Message to show when timer expires")


# ── Tool implementations ──────────────────────────────────────────────────────

def _safe(fn):
    """Decorator: run security check on first string arg before executing."""
    def wrapper(*args, **kwargs):
        first_arg = str(args[0] if args else next(iter(kwargs.values()), ""))
        sec = check_command(first_arg)
        if not sec.safe:
            return f"Blocked: {sec.reason}"
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


@_safe
def tool_open_app(name: str) -> str:
    from plugins.app_control import open_application
    return open_application(name)

@_safe
def tool_close_app(name: str) -> str:
    from plugins.app_control import close_application
    return close_application(name)

@_safe
def tool_open_url(url: str) -> str:
    from plugins.browser_control import open_url_sync
    return open_url_sync(url)

@_safe
def tool_search_youtube(query: str) -> str:
    from plugins.browser_control import search_youtube_sync
    return search_youtube_sync(query)

@_safe
def tool_type_text(text: str) -> str:
    from plugins.mouse_keyboard import type_text
    return type_text(text)

@_safe
def tool_paste_text(text: str) -> str:
    from plugins.mouse_keyboard import paste_text
    return paste_text(text)

def tool_click(x: int, y: int) -> str:
    from plugins.mouse_keyboard import click
    return click(x, y)

def tool_hotkey(keys: list[str]) -> str:
    from plugins.mouse_keyboard import hotkey
    return hotkey(*keys)

def tool_scroll(clicks: int) -> str:
    from plugins.mouse_keyboard import scroll
    return scroll(clicks)

@_safe
def tool_file_search(query: str, path: str = "C:\\") -> str:
    from plugins.file_search import search_files
    results = search_files(query, path)
    if results:
        return "Found:\n" + "\n".join(results[:10])
    return f"No files found matching '{query}'."

@_safe
def tool_open_path(path: str) -> str:
    from plugins.file_search import open_file
    return open_file(path)

@_safe
def tool_search_and_open_file(query: str, path: str = "C:\\Users") -> str:
    from plugins.file_search import search_and_open
    return search_and_open(query, path)

@_safe
def tool_system_action(action: str) -> str:
    from plugins.system_control import system_action
    return system_action(action)

@_safe
def tool_run_powershell(command: str) -> str:
    import subprocess
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=20,
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode == 0:
            return out[:2000] or "Command completed."
        return (err or out or "Command failed.")[:2000]
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Command error: {e}"

def tool_dictate_and_enter(mode: str = "paste") -> str:
    """
    Record speech and enter it into the currently-focused application.
    This is intended for "dictation" and "type what I say" workflows.
    """
    from voice.speech_to_text import listen_and_transcribe
    from plugins.mouse_keyboard import type_text, paste_text

    text = listen_and_transcribe().strip()
    if not text:
        return "I didn't catch anything."
    if mode.lower().strip() == "type":
        return type_text(text)
    return paste_text(text)

def tool_toggle_wifi(state: bool) -> str:
    from plugins.system_control import control_wifi
    return control_wifi(state)

def tool_toggle_bluetooth(state: bool) -> str:
    from plugins.system_control import control_bluetooth
    return control_bluetooth(state)

def tool_toggle_airplane(state: bool) -> str:
    from plugins.system_control import control_airplane_mode
    return control_airplane_mode(state)

def tool_toggle_hotspot(state: bool) -> str:
    from plugins.system_control import control_hotspot
    return control_hotspot(state)

def tool_screenshot() -> str:
    from plugins.system_control import take_screenshot
    return take_screenshot()

def tool_set_volume(action: str) -> str:
    from plugins.system_control import set_volume
    return set_volume(action)

def tool_set_brightness(level: int) -> str:
    from plugins.system_control import set_brightness
    return set_brightness(level)

def tool_media_control(action: str) -> str:
    from plugins.system_control import media_control
    return media_control(action)

def tool_trigger_shortcut(action: str) -> str:
    from plugins.system_control import trigger_shortcut
    return trigger_shortcut(action)

def tool_battery_status() -> str:
    from plugins.system_control import get_battery_status
    return get_battery_status()

def tool_set_reminder(message: str, minutes_from_now: Optional[int] = None, absolute_time: Optional[str] = None) -> str:
    from plugins.reminder_control import add_reminder
    return add_reminder(message, minutes_from_now, absolute_time)

def tool_list_reminders() -> str:
    from plugins.reminder_control import list_reminders
    return list_reminders()

def tool_set_timer(seconds: int, message: str = "Timer") -> str:
    from plugins.timer_control import set_timer
    return set_timer(seconds, message)

def tool_get_time() -> str:
    from plugins.info_control import get_current_time
    return get_current_time()

def tool_get_date() -> str:
    from plugins.info_control import get_current_date
    return get_current_date()

def tool_empty_trash() -> str:
    from plugins.system_control import empty_recycle_bin
    return empty_recycle_bin()

def tool_system_info() -> str:
    from plugins.system_control import get_detailed_system_info
    return get_detailed_system_info()

def tool_get_capabilities() -> str:
    import sys
    import shutil
    caps = [f"Operating System: {sys.platform}"]
    if sys.platform == "win32":
        caps.append("Capabilities: PowerShell, WinRT Notifications, AppControl (Start Menu)")
    elif sys.platform == "darwin":
        caps.append("Capabilities: AppleScript, osascript Notifications, AppControl (open)")
        if shutil.which("blueutil"):
            caps.append("Extra: bluetooth control (blueutil) available")
    else:
        caps.append("Capabilities: systemctl, notify-send Notifications, AppControl (xdg-open)")
        if shutil.which("nmcli"): caps.append("Extra: wifi control (nmcli) available")
        if shutil.which("rfkill"): caps.append("Extra: bluetooth control (rfkill) available")
    
    return "\n".join(caps)


# ── Build LangChain tools ─────────────────────────────────────────────────────

TOOLS = [
    StructuredTool.from_function(
        func=tool_open_app,
        name="open_application",
        description="Open an application by name on Windows.",
        args_schema=AppInput,
    ),
    StructuredTool.from_function(
        func=tool_close_app,
        name="close_application",
        description="Close an application by name/process.",
        args_schema=CloseAppInput,
    ),
    StructuredTool.from_function(
        func=tool_open_url,
        name="open_url",
        description="Open a URL in the default browser.",
        args_schema=BrowserInput,
    ),
    StructuredTool.from_function(
        func=tool_search_youtube,
        name="search_youtube",
        description="Open YouTube and search for the given query.",
        args_schema=SearchInput,
    ),
    StructuredTool.from_function(
        func=tool_type_text,
        name="type_text",
        description="Type text using the keyboard.",
        args_schema=TypeInput,
    ),
    StructuredTool.from_function(
        func=tool_paste_text,
        name="paste_text",
        description="Paste text quickly using clipboard + Ctrl+V.",
        args_schema=PasteInput,
    ),
    StructuredTool.from_function(
        func=tool_click,
        name="click",
        description="Click at specific screen coordinates.",
        args_schema=ClickInput,
    ),
    StructuredTool.from_function(
        func=tool_hotkey,
        name="hotkey",
        description="Press a keyboard shortcut, e.g. ctrl+c, alt+tab.",
        args_schema=HotkeyInput,
    ),
    StructuredTool.from_function(
        func=tool_scroll,
        name="scroll",
        description="Scroll up/down by a number of clicks.",
        args_schema=ScrollInput,
    ),
    StructuredTool.from_function(
        func=tool_file_search,
        name="search_files",
        description="Search for files by name or keyword.",
        args_schema=FileInput,
    ),
    StructuredTool.from_function(
        func=tool_search_and_open_file,
        name="search_and_open_file",
        description="Search for a file and open the best match.",
        args_schema=SearchOpenFileInput,
    ),
    StructuredTool.from_function(
        func=tool_open_path,
        name="open_path",
        description="Open a file/folder by exact path (uses the default app).",
        args_schema=OpenPathInput,
    ),
    StructuredTool.from_function(
        func=tool_system_action,
        name="system_action",
        description="Execute a system action: shutdown, restart, sleep, or lock.",
        args_schema=SystemInput,
    ),
    StructuredTool.from_function(
        func=tool_run_powershell,
        name="run_powershell",
        description="Run a short PowerShell command and return output.",
        args_schema=CommandInput,
    ),
    StructuredTool.from_function(
        func=tool_dictate_and_enter,
        name="dictate_and_enter",
        description="Record speech and enter it into the focused app (dictation).",
        args_schema=DictationInput,
    ),
    StructuredTool.from_function(
        func=tool_toggle_wifi,
        name="toggle_wifi",
        description="Turn Wi-Fi on (True) or off (False).",
        args_schema=HardwareInput,
    ),
    StructuredTool.from_function(
        func=tool_toggle_bluetooth,
        name="toggle_bluetooth",
        description="Turn Bluetooth on (True) or off (False).",
        args_schema=HardwareInput,
    ),
    StructuredTool.from_function(
        func=tool_toggle_airplane,
        name="toggle_airplane_mode",
        description="Turn Airplane Mode on (True) or off (False).",
        args_schema=HardwareInput,
    ),
    StructuredTool.from_function(
        func=tool_toggle_hotspot,
        name="toggle_hotspot",
        description="Turn Mobile Hotspot on (True) or off (False).",
        args_schema=HardwareInput,
    ),
    StructuredTool.from_function(
        func=tool_screenshot,
        name="take_screenshot",
        description="Capture a screenshot of the entire screen.",
    ),
    StructuredTool.from_function(
        func=tool_set_volume,
        name="set_volume",
        description="Adjust volume: up, down, or mute.",
        args_schema=VolumeInput,
    ),
    StructuredTool.from_function(
        func=tool_set_brightness,
        name="set_brightness",
        description="Adjust display brightness level (0-100).",
        args_schema=BrightnessInput,
    ),
    StructuredTool.from_function(
        func=tool_media_control,
        name="media_control",
        description="Control media playback: play, pause, next, prev.",
        args_schema=MediaInput,
    ),
    StructuredTool.from_function(
        func=tool_trigger_shortcut,
        name="trigger_system_shortcut",
        description="Trigger a system shortcut: project (Win+P), cast (Win+K), or taskmgr.",
        args_schema=ShortcutInput,
    ),
    StructuredTool.from_function(
        func=tool_battery_status,
        name="get_battery_info",
        description="Get current battery percentage and charging state.",
    ),
    StructuredTool.from_function(
        func=tool_set_reminder,
        name="set_reminder",
        description="Set a reminder for the user. Provide either minutes_from_now OR absolute_time (HH:MM).",
        args_schema=ReminderInput,
    ),
    StructuredTool.from_function(
        func=tool_list_reminders,
        name="list_reminders",
        description="List all active reminders.",
    ),
    StructuredTool.from_function(
        func=tool_set_timer,
        name="set_timer",
        description="Set a short-term timer in seconds.",
        args_schema=TimerInput,
    ),
    StructuredTool.from_function(
        func=tool_get_time,
        name="get_current_time",
        description="Get the current local time.",
    ),
    StructuredTool.from_function(
        func=tool_get_date,
        name="get_current_date",
        description="Get today's date.",
    ),
    StructuredTool.from_function(
        func=tool_empty_trash,
        name="empty_recycle_bin",
        description="Empty the system recycle bin / trash.",
    ),
    StructuredTool.from_function(
        func=tool_system_info,
        name="get_system_info",
        description="Get technical information about the PC (OS, CPU, RAM).",
    ),
    StructuredTool.from_function(
        func=tool_get_capabilities,
        name="get_machine_capabilities",
        description="Detect the OS and what system-level tools are available.",
    ),
]


# ── Planner class ─────────────────────────────────────────────────────────────

_PLANNER_PROMPT = (
    "You are Hilda's task planner. Given a user request, decompose it into "
    "precise tool calls and execute them in order. Always use the minimum number "
    "of steps needed. After completing all steps, summarise what you did in one "
    "short sentence."
)


class HildaPlanner:
    """
    LangChain AgentExecutor that maps user requests to tool calls.
    Falls back to a simple local description if OpenAI is not configured.
    """

    def __init__(self) -> None:
        if settings.OPENAI_API_KEY:
            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY,
                temperature=0,
            )
            self._executor = create_agent(
                model=llm,
                tools=TOOLS,
                system_prompt=_PLANNER_PROMPT,
            )
        else:
            log.warning(
                "No OPENAI_API_KEY set — planner running in direct-tool mode."
            )
            self._executor = None

    async def run(self, user_input: str) -> str:
        """Execute the planning pipeline for the given input."""
        if self._executor is None:
            return await self._direct_tool_mode(user_input)

        loop = asyncio.get_event_loop()
        try:
            result: dict[str, Any] = await loop.run_in_executor(
                None,
                lambda: self._executor.invoke({"messages": [("user", user_input)]}),
            )
            messages = result.get("messages", [])
            if messages:
                return messages[-1].content
        except Exception as e:
            log.error(f"LLM planner failed (e.g. quota/network error): {e}. Falling back to direct tool dispatch.")
            return await self._direct_tool_mode(user_input)
            
        return "Task completed."

    async def _direct_tool_mode(self, text: str) -> str:
        """
        When no LLM planner is available, use the same fast pattern router
        as the live agent, then a clear message if nothing matched.
        """
        from core.fast_lane import try_dispatch

        hit = try_dispatch(text)
        if hit is not None:
            return hit
        return (
            "I could not match that to a local command. "
            "Add an OpenAI API key in .env for full natural-language planning, "
            "or try a direct command such as 'open notepad'."
        )


# Backward compatibility for older scripts / docs
EmilioPlanner = HildaPlanner
