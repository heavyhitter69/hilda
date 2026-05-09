/**
 * Context bridge: Dynamic Island UI + Setup wizard ↔ main process ↔ Python WS.
 *
 * Primary API: window.hilda (window.emilio is the same object).
 */
const { contextBridge, ipcRenderer } = require("electron");

const WS_URL = "ws://localhost:8765";
let ws = null;
const _wsListeners = [];
const _pendingSetup = new Map();

function mkRequestId() {
  try {
    if (global.crypto && typeof global.crypto.randomUUID === "function") {
      return global.crypto.randomUUID();
    }
  } catch (_) {}
  return `rid_${Date.now()}_${Math.random().toString(36).slice(2)}`;
}

function connectWS() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log("[preload] Connected to Hilda backend.");
    _wsListeners.forEach((fn) => fn({ type: "ws_open" }));
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);

      if (msg.type === "setup_response" && msg.request_id != null && _pendingSetup.has(msg.request_id)) {
        const entry = _pendingSetup.get(msg.request_id);
        clearTimeout(entry.timer);
        _pendingSetup.delete(msg.request_id);
        entry.resolve(msg);
        return;
      }

      _wsListeners.forEach((fn) => fn(msg));
    } catch (e) {
      console.error("[preload] WS parse error:", e);
    }
  };

  ws.onclose = () => {
    console.warn("[preload] WS closed. Reconnecting in 2s.");
    setTimeout(connectWS, 2000);
  };

  ws.onerror = (e) => {
    console.error("[preload] WS error:", e.message || e);
  };
}

connectWS();

const hildaBridge = {
  send: (channel, data, ...args) => ipcRenderer.send(channel, data, ...args),

  onIpc: (channel, callback) =>
    ipcRenderer.on(channel, (_, ...args) => callback(...args)),

  onWsMessage: (callback) => _wsListeners.push(callback),

  sendCommand: (text) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "command", text }));
    } else {
      console.warn("[preload] WS not ready, command dropped:", text);
    }
  },

  /** Setup wizard RPC (waits for matching setup_response). */
  setupRequest: (action, extras = {}) =>
    new Promise((resolve, reject) => {
      if (!ws || ws.readyState !== WebSocket.OPEN) {
        reject(new Error("Hilda backend is not connected."));
        return;
      }
      const request_id = mkRequestId();
      const timer = setTimeout(() => {
        if (_pendingSetup.has(request_id)) {
          _pendingSetup.delete(request_id);
          reject(new Error("Setup step timed out (is Python still running?)"));
        }
      }, 180000);

      _pendingSetup.set(request_id, { resolve, reject, timer });
      try {
        ws.send(JSON.stringify({ type: "setup", request_id, action, ...extras }));
      } catch (e) {
        clearTimeout(timer);
        _pendingSetup.delete(request_id);
        reject(e);
      }
    }),

  openMicPrivacySettings: () => ipcRenderer.invoke("open-microphone-settings"),

  openStartupSoundSettings: () => ipcRenderer.invoke("open-speech-settings"),

  addProjectToUserPath: () => ipcRenderer.invoke("add-project-to-user-path"),

  completeSetupWizard: (profile) => ipcRenderer.invoke("complete-setup-wizard", profile),

  declineSetupQuit: () => ipcRenderer.invoke("decline-setup-quit"),

  skipSetupWizard: () => ipcRenderer.invoke("skip-setup-wizard"),

  wsReady: () => ws && ws.readyState === WebSocket.OPEN,

  projectRootEstimate: () => ipcRenderer.invoke("get-project-root"),
};

contextBridge.exposeInMainWorld("hilda", hildaBridge);
contextBridge.exposeInMainWorld("emilio", hildaBridge);
