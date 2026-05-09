/**
 * ui/src/renderer.js — Dynamic Island state machine + waveform + chat.
 *
 * States: idle | listening | thinking | speaking
 * Communicates with Python via window.hilda.* (emilio alias still works).
 */

const ipc = typeof window !== "undefined" ? window.hilda || window.emilio : null;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const island      = document.getElementById("island");
const statusText  = document.getElementById("status-text");
const waveCanvas  = document.getElementById("waveform");
const chatLog     = document.getElementById("chat-log");
const chatInput   = document.getElementById("chat-input");
const avatarImg   = document.getElementById("avatar-img");

const waveCtx = waveCanvas.getContext("2d");

// ── Setup Avatar ──────────────────────────────────────────────────────────────
function setupAvatar() {
  // Using the HTTP API to bypass Electron renderer CommonJS 'require' errors
  // Seed 'Brian' generates the requested adventurer avatar
  avatarImg.src = 'https://api.dicebear.com/9.x/adventurer/svg?seed=Brian&backgroundColor=b6e3f4,c0aede,d1d4f9,ffd5dc,ffdfbf';
}
setupAvatar();

// ── State machine ─────────────────────────────────────────────────────────────
const STATE_CONFIG = {
  idle:       { label: "Hilda",      wave: false },
  listening:  { label: "Listening…", wave: true  },
  thinking:   { label: "Thinking…",  wave: false },
  speaking:   { label: "Speaking…",  wave: true  },
};

let currentState = "idle";

/** Keep the Electron window visible while the chat panel is open or focused (idle hides too fast otherwise). */
function shouldKeepIslandVisible() {
  if (!island) return false;
  if (island.classList.contains("expanded")) return true;
  const ae = document.activeElement;
  if (!ae) return false;
  if (ae === chatInput) return true;
  if (ae.id === "send-btn") return true;
  if (ae.id === "toggle-btn") return true;
  return Boolean(ae.closest && ae.closest(".panel"));
}

const IDLE_DWELL_MS = 2600;
let _idleDwellTimer = null;

function setState(state) {
  if (!STATE_CONFIG[state]) return;
  const prev = currentState;
  currentState = state;
  const cfg = STATE_CONFIG[state];

  // Update class (preserve expanded if island already had it user toggled)
  const expanded = island.classList.contains("expanded");
  island.className = "island " + state + (expanded ? " expanded" : "");

  // Status text
  statusText.textContent = cfg.label;
  statusText.style.opacity = cfg.wave ? "0" : "1";
  waveCanvas.style.display = cfg.wave ? "block" : "none";

  if (cfg.wave) {
    startWaveform(state === "listening" ? "#4cde80" : "#7c6af7");
  } else {
    stopWaveform();
  }

  if (_idleDwellTimer) {
    clearTimeout(_idleDwellTimer);
    _idleDwellTimer = null;
  }

  if (!ipc) return;

  if (state !== "idle") {
    ipc.send("set-visibility", true);
    return;
  }

  if (shouldKeepIslandVisible()) {
    ipc.send("set-visibility", true);
    return;
  }

  // Brief dwell after listening so the pill doesn’t vanish before you expand or read feedback
  if (prev === "listening") {
    ipc.send("set-visibility", true);
    _idleDwellTimer = setTimeout(() => {
      _idleDwellTimer = null;
      if (currentState === "idle" && !shouldKeepIslandVisible()) {
        ipc.send("set-visibility", false);
      }
    }, IDLE_DWELL_MS);
    return;
  }

  ipc.send("set-visibility", false);
}

// ── Waveform animation ────────────────────────────────────────────────────────
let _waveRaf = null;
let _waveColor = "#7c6af7";
let _wavePhase = 0;

function startWaveform(color) {
  _waveColor = color;
  if (_waveRaf) return;

  function draw() {
    const W = waveCanvas.width;
    const H = waveCanvas.height;
    waveCtx.clearRect(0, 0, W, H);

    const bars = 28;
    const gap  = 3;
    const barW = (W - gap * (bars - 1)) / bars;
    const cx   = H / 2;

    waveCtx.fillStyle = _waveColor;

    for (let i = 0; i < bars; i++) {
      const t = _wavePhase + i * 0.38;
      const amp = (Math.sin(t) * 0.5 + 0.5) * (H * 0.75) + H * 0.1;
      const x = i * (barW + gap);
      const h = Math.max(2, amp);
      const y = cx - h / 2;

      // Rounded rect
      waveCtx.beginPath();
      const r = barW / 2;
      waveCtx.moveTo(x + r, y);
      waveCtx.arcTo(x + barW, y,     x + barW, y + h, r);
      waveCtx.arcTo(x + barW, y + h, x,         y + h, r);
      waveCtx.arcTo(x,        y + h, x,         y,     r);
      waveCtx.arcTo(x,        y,     x + barW,  y,     r);
      waveCtx.closePath();
      waveCtx.fill();
    }

    _wavePhase += 0.08;
    _waveRaf = requestAnimationFrame(draw);
  }

  draw();
}

function stopWaveform() {
  if (_waveRaf) {
    cancelAnimationFrame(_waveRaf);
    _waveRaf = null;
  }
  waveCtx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);
}

// ── Chat messages ─────────────────────────────────────────────────────────────
function addMessage(role, text) {
  const wrap = document.createElement("div");
  wrap.className = "msg " + (role === "user" ? "user" : "ai");

  const label = document.createElement("div");
  label.className = "msg-label";
  label.textContent = role === "user" ? "You" : "Hilda";

  const content = document.createElement("div");
  content.textContent = text;

  wrap.appendChild(label);
  wrap.appendChild(content);
  chatLog.appendChild(wrap);
  chatLog.scrollTop = chatLog.scrollHeight;

  return { wrap, content };
}

let _streaming = {
  role: null,
  wrap: null,
  content: null,
  text: "",
};

// ── Toggle expand ─────────────────────────────────────────────────────────────
window.__toggleExpand = function () {
  island.classList.toggle("expanded");
  if (ipc) {
    ipc.send("toggle-expand");
    if (island.classList.contains("expanded")) {
      ipc.send("set-visibility", true);
    } else if (currentState === "idle") {
      ipc.send("set-visibility", false);
    }
  }
};

// ── Send typed command ────────────────────────────────────────────────────────
window.__sendCommand = function () {
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";

  addMessage("user", text);
  if (ipc) ipc.sendCommand(text);
  setState("thinking");
};

chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") window.__sendCommand();
});

chatInput.addEventListener("focus", () => {
  if (ipc && currentState === "idle") ipc.send("set-visibility", true);
});

// ── WebSocket messages from Python ────────────────────────────────────────────
if (ipc) ipc.onWsMessage((msg) => {
  switch (msg.type) {
    case "state":
      setState(msg.value);
      break;

    case "message":
      addMessage(msg.role, msg.text);
      break;

    case "message_start": {
      _streaming.role = msg.role || "assistant";
      _streaming.text = "";
      const { wrap, content } = addMessage(_streaming.role, "");
      _streaming.wrap = wrap;
      _streaming.content = content;
      break;
    }

    case "delta": {
      if (!_streaming.content) {
        // If UI didn't get a start event (or refreshed), fall back gracefully.
        const { wrap, content } = addMessage(msg.role || "assistant", "");
        _streaming.wrap = wrap;
        _streaming.content = content;
        _streaming.role = msg.role || "assistant";
        _streaming.text = "";
      }
      _streaming.text += msg.text || "";
      _streaming.content.textContent = _streaming.text;
      chatLog.scrollTop = chatLog.scrollHeight;
      break;
    }

    case "message_end":
      _streaming.role = null;
      _streaming.wrap = null;
      _streaming.content = null;
      _streaming.text = "";
      break;

    case "error":
      addMessage("ai", "⚠️ " + msg.text);
      setState("idle");
      break;

    case "ws_open":
      console.log("[renderer] Python backend connected.");
      addMessage("ai", "Connected to Hilda backend.");
      break;

    case "expand":
      if (!island.classList.contains("expanded")) {
        window.__toggleExpand();
      }
      break;
  }
});

// ── Mouse Events (Click-through) ──────────────────────────────────────────────
island.addEventListener('mouseenter', () => {
  if (ipc) ipc.send("set-ignore-mouse-events", false);
});
island.addEventListener('mouseleave', () => {
  if (ipc) ipc.send("set-ignore-mouse-events", true, true);
});

// ── Init ──────────────────────────────────────────────────────────────────────
setState("idle");
