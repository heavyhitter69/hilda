"""
core/websocket_server.py — WebSocket server bridging Hilda backend ↔ Electron UI.

Messages are JSON objects:
  { "type": "state",   "value": "listening" | "thinking" | "speaking" | "idle" }
  { "type": "message", "role": "user" | "assistant", "text": "..." }
  { "type": "setup",   "request_id": "...", "action": "list_voices" | ... }
  { "type": "setup_response", "request_id": "...", ... }
  { "type": "error",   "text": "..." }
"""
import asyncio
import json
from typing import Dict, Set

import websockets
from websockets.server import WebSocketServerProtocol

from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)

_clients: Set[WebSocketServerProtocol] = set()
_send_locks: Dict[WebSocketServerProtocol, asyncio.Lock] = {}

# Main asyncio loop (registered from async entry) — wake detection runs in threads.
_main_loop: asyncio.AbstractEventLoop | None = None


def register_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def broadcast_state_from_thread(state: str) -> None:
    """Schedule state broadcast from a background thread (wake detector). Safe no-op if loop missing."""
    if _main_loop is None:
        return

    def _done(fut) -> None:  # concurrent.futures.Future
        try:
            fut.result()
        except Exception as e:
            log.warning("broadcast_state_from_thread(%s): %s", state, e)

    fut = asyncio.run_coroutine_threadsafe(broadcast_state(state), _main_loop)
    fut.add_done_callback(_done)


async def _handle_setup(ws: WebSocketServerProtocol, data: dict) -> None:
    """Fulfill wizard requests and reply only to the requesting socket."""
    from voice.setup_commands import run_setup_action

    req_id = data.get("request_id")
    action = str(data.get("action") or "")
    payload = {
        k: v
        for k, v in data.items()
        if k not in ("type", "request_id", "action") and isinstance(k, str)
    }
    result = await run_setup_action(action, payload)
    out = {"type": "setup_response", "request_id": req_id, **result}
    await _safe_send(ws, json.dumps(out))


async def _handler(ws: WebSocketServerProtocol) -> None:
    """Handle a new Electron UI connection."""
    _clients.add(ws)
    _send_locks[ws] = asyncio.Lock()
    log.info("UI client connected. Total: %d", len(_clients))
    try:
        async for raw in ws:
            # UI → Python (e.g. manual text command from chat panel)
            try:
                data = json.loads(raw)
                log.debug("UI → Agent: %s", data)
                if data.get("type") == "setup":
                    asyncio.create_task(_handle_setup(ws, data))
                    continue
                from core.agent import get_agent

                agent = get_agent()
                if data.get("type") == "command" and "text" in data:
                    asyncio.create_task(agent.handle_text(data["text"]))
            except json.JSONDecodeError:
                log.warning("Received non-JSON message from UI: %s", raw[:100])
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        log.warning("UI client disconnected unexpectedly: %s", e)
    finally:
        _clients.discard(ws)
        _send_locks.pop(ws, None)
        log.info("UI client removed. Total: %d", len(_clients))


async def _safe_send(ws: WebSocketServerProtocol, payload: str) -> bool:
    """
    Send payload to a single client with a per-socket lock.
    Returns False if client is closed/disconnected.
    """
    lock = _send_locks.get(ws)
    if lock is None:
        return False
    try:
        async with lock:
            await ws.send(payload)
        return True
    except websockets.exceptions.ConnectionClosed:
        return False


async def broadcast(message: dict) -> None:
    """Send a JSON message to all connected Electron UI clients."""
    if not _clients:
        return
    payload = json.dumps(message)
    clients = list(_clients)
    results = await asyncio.gather(*(_safe_send(ws, payload) for ws in clients), return_exceptions=True)
    for ws, ok in zip(clients, results):
        if ok is False or isinstance(ok, Exception):
            _clients.discard(ws)
            _send_locks.pop(ws, None)


async def broadcast_state(state: str) -> None:
    """Helper: broadcast a state-change notification."""
    await broadcast({"type": "state", "value": state})


async def broadcast_message(role: str, text: str) -> None:
    """Helper: broadcast a chat message to the UI."""
    await broadcast({"type": "message", "role": role, "text": text})


async def broadcast_delta(role: str, delta: str) -> None:
    """
    Helper: broadcast streaming text deltas.
    UI can stitch these into the active assistant bubble.
    """
    if not delta:
        return
    await broadcast({"type": "delta", "role": role, "text": delta})


async def broadcast_message_start(role: str) -> None:
    """Helper: signal start of a streamed message."""
    await broadcast({"type": "message_start", "role": role})


async def broadcast_message_end(role: str) -> None:
    """Helper: signal end of a streamed message."""
    await broadcast({"type": "message_end", "role": role})

async def start_server() -> None:
    """Start the WebSocket server and run forever."""
    host = settings.WEBSOCKET_HOST
    port = settings.WEBSOCKET_PORT
    log.info("WebSocket server starting on ws://%s:%d", host, port)
    async with websockets.serve(_handler, host, port):
        await asyncio.Future()  # run forever
