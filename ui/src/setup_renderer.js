/**
 * Hilda first-run wizard (paired with ../main.py).
 */
const FLOW = ["welcome", "terms", "permissions", "enrollment", "voices", "practice", "done"];

let stepIndex = 0;
/** @type {Array<{id:string,name:string}>} */
let voiceChoices = [];
let selectedVoiceId = null;
/** @type {Record<string, unknown>} */
let envSnap = {};

const $ = (id) => document.getElementById(id);

function renderStepDots() {
  const el = $("steps");
  if (!el) return;
  el.innerHTML = FLOW.map((s, i) => {
    const label =
      ({
        welcome: "Start",
        terms: "Terms",
        permissions: "Access",
        enrollment: "Voice cal",
        voices: "Voice",
        practice: "Practice",
        done: "Done",
      }[s]) || s;
    return `<span class="${i === stepIndex ? "active" : ""}">${label}</span>`;
  }).join("");
}

function showOnlyStep(name) {
  FLOW.forEach((s) => {
    const n = $("step-" + s);
    if (n) n.classList.toggle("hidden", s !== name);
  });
}

function setStatus(msg, variant) {
  const st = $("status-line");
  if (!st) return;
  st.textContent = msg;
  st.classList.remove("ok", "bad");
  if (variant) st.classList.add(variant);
}

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function waitForBackend(maxMs = 120000) {
  const hp = window.hilda || window.emilio;
  if (!hp || !hp.wsReady || !hp.setupRequest) {
    setStatus("Preload bridge missing.", "bad");
    return false;
  }
  const started = Date.now();
  while (Date.now() - started < maxMs) {
    if (hp.wsReady()) {
      setStatus("Backend connected.", "ok");
      return true;
    }
    setStatus('Waiting for ws://localhost:8765 …  In a terminal run: python main.py', "bad");
    await sleep(400);
  }
  setStatus("Could not reach Python backend. Run python main.py then refresh this window.", "bad");
  return false;
}

async function loadVoiceList(slice = 8) {
  const hp = window.hilda || window.emilio;
  try {
    const resp = await hp.setupRequest("list_voices");
    if (!resp.ok) throw new Error(resp.error || "list_voices failed");
    const all = resp.voices || [];
    voiceChoices = all.slice(0, Math.min(slice, all.length));
    renderVoices();
  } catch (e) {
    setStatus(`Voice list failed: ${e.message}`, "bad");
    voiceChoices = [];
    renderVoices();
  }
}

let currentCarouselIndex = 0;

function updateCarouselUI() {
  const track = $("carousel-track");
  const dots = $("carousel-dots");
  const title = $("carousel-title");
  const desc = $("carousel-desc");
  if (!track || !dots || voiceChoices.length === 0) return;

  const cards = track.querySelectorAll(".carousel-item");
  const dotElements = dots.querySelectorAll(".carousel-dot");
  
  cards.forEach((card, idx) => {
    if (idx === currentCarouselIndex) {
      card.classList.add("active");
      const v = voiceChoices[idx];
      if (v) {
        if (title) title.textContent = v.name;
        if (desc) desc.textContent = v.desc || v.id;
        selectedVoiceId = v.id;
      }
    } else {
      card.classList.remove("active");
    }
  });

  dotElements.forEach((dot, idx) => {
    if (idx === currentCarouselIndex) {
      dot.classList.add("active");
    } else {
      dot.classList.remove("active");
    }
  });

  track.style.transform = `translateX(-${currentCarouselIndex * 100}%)`;
  
  const pv = $("btn-preview-voice");
  if (pv) pv.disabled = false;
  
  updateNavButtons();
}

function renderVoices() {
  const track = $("carousel-track");
  const dots = $("carousel-dots");
  if (!track || !dots) return;
  
  track.innerHTML = "";
  dots.innerHTML = "";
  currentCarouselIndex = 0;
  
  voiceChoices.forEach((v, i) => {
    const item = document.createElement("div");
    item.className = "carousel-item";
    item.innerHTML = `<h3 style="margin:0; font-size: 1.5rem; color: transparent;">${v.name}</h3>`;
    track.appendChild(item);

    const dot = document.createElement("div");
    dot.className = "carousel-dot";
    dot.addEventListener("click", () => {
      currentCarouselIndex = i;
      updateCarouselUI();
    });
    dots.appendChild(dot);
  });
  
  updateCarouselUI();
}

async function previewSelected() {
  const hp = window.hilda || window.emilio;
  if (!selectedVoiceId) return;
  try {
    setStatus("Playing preview via speakers…", "ok");
    await hp.setupRequest("preview_voice", {
      voice_id: selectedVoiceId,
      phrase: "Hi - I am Hilda. This is how I will sound.",
    });
    setStatus("Preview finished.", "ok");
  } catch (e) {
    setStatus(e.message || String(e), "bad");
  }
}

async function saveSelectedVoice() {
  const hp = window.hilda || window.emilio;
  if (!selectedVoiceId) return false;
  const resp = await hp.setupRequest("save_voice", { voice_id: selectedVoiceId });
  if (!resp.ok) {
    setStatus(resp.error || "Could not save voice", "bad");
    return false;
  }
  return true;
}

function buildPracticeUI() {
  const hint = $("wake-hint-practice");
  const box = $("practice-prompts");
  if (!hint || !box) return;

  hint.textContent = "";
  const p = document.createElement("p");
  p.style.margin = "0 0 10px";
  p.style.fontSize = "0.9rem";
  p.style.color = "var(--muted)";
  p.textContent =
    "Whisper wake mode: say “Hey Hilda”, “Hello Hilda”, or similar. Your enrollment helps recognition match your accent.";
  hint.appendChild(p);

  box.textContent = "";
  const samples = [
    "Hey Hilda — open my Downloads folder",
    "Hello Hilda — search the web for news",
    "Hilda — lock my computer",
  ];
  samples.forEach((t) => {
    const wrap = document.createElement("div");
    wrap.className = "prompt-box";
    wrap.appendChild(document.createTextNode("Try: "));
    wrap.appendChild(document.createTextNode(t));
    box.appendChild(wrap);
  });
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

async function renderEnrollmentList() {
  const hp = window.hilda || window.emilio;
  const wrap = $("enrollment-list");
  const st = $("enrollment-status");
  if (!wrap) return;
  wrap.innerHTML = "<p class=\"muted-tip\">Loading phrases…</p>";
  try {
    const r = await hp.setupRequest("list_enrollment_phrases");
    if (!r.ok) throw new Error(r.error || "failed");
    const phrases = r.phrases || [];
    wrap.innerHTML = "";
    phrases.forEach((p) => {
      const row = document.createElement("div");
      row.className = "enroll-row" + (p.recorded ? " recorded" : "");
      const heard =
        p.transcript && String(p.transcript).trim()
          ? `<span class="enroll-heard-label">Heard:</span> ${escapeHtml(String(p.transcript).trim())}`
          : "";
      row.innerHTML = `
        <div class="enroll-meta">
          <div class="enroll-prompt"><strong>Say:</strong> ${escapeHtml(p.prompt)}</div>
          <div class="enroll-hint">${escapeHtml(p.hint)}</div>
          <div class="enroll-transcript">${heard}</div>
        </div>
        <button type="button" class="btn primary btn-record-line" data-id="${escapeHtml(p.id)}">Record</button>`;
      wrap.appendChild(row);
    });
    wrap.querySelectorAll(".btn-record-line").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.getAttribute("data-id");
        setStatus("Listening… speak when ready.", "ok");
        btn.disabled = true;
        try {
          const resp = await hp.setupRequest("enrollment_record", { phrase_id: id });
          if (!resp || resp.ok !== true) {
            throw new Error((resp && resp.error) || "Recording failed");
          }
          if (resp.transcript && String(resp.transcript).trim()) {
            setStatus("Recorded: " + String(resp.transcript).trim(), "ok");
          } else {
            setStatus("Recorded (no transcript).", "ok");
          }
          await renderEnrollmentList();
        } catch (e) {
          setStatus(String(e.message || e), "bad");
        } finally {
          btn.disabled = false;
        }
      });
    });
    const done = phrases.filter((x) => x.recorded).length;
    if (st) {
      st.textContent = `${done} / ${phrases.length} lines recorded — complete all for best accuracy.`;
    }
  } catch (e) {
    wrap.innerHTML = "<p class=\"muted-tip\">Could not load enrollment.</p>";
  }
}

async function refreshEnv() {
  const hp = window.hilda || window.emilio;
  try {
    const r = await hp.setupRequest("env_info");
    if (r.ok) envSnap = r;
  } catch (_) {
    envSnap = {};
  }
}

function updateNavButtons() {
  const cur = FLOW[stepIndex];
  const back = $("btn-back");
  const next = $("btn-next");
  if (back) back.disabled = stepIndex === 0;
  const hp = window.hilda || window.emilio;

  if (next) {
    if (cur === "terms") {
      next.disabled = !$("accept-terms")?.checked;
    } else if (cur === "voices") {
      next.disabled = !selectedVoiceId;
    } else {
      next.disabled = false;
    }
    next.textContent = cur === "done" ? "Open Hilda" : "Next";
  }

  $("btn-skip")?.classList.toggle("hidden", cur !== "welcome");
}

async function gotoStep(delta) {
  const cur = FLOW[stepIndex];
  if (delta > 0 && cur === "welcome") {
    const nm = ($("user-display-name")?.value || "").trim();
    if (!nm) {
      setStatus("Enter your name so Hilda can say hi.", "bad");
      return;
    }
    try {
      const hp = window.hilda || window.emilio;
      await hp.setupRequest("save_display_name", { display_name: nm });
    } catch (e) {
      setStatus(String(e.message || e), "bad");
      return;
    }
    setStatus("Backend connected.", "ok");
  }
  if (delta > 0 && cur === "terms") {
    if (!$("accept-terms")?.checked) return;
  }
  if (delta > 0 && cur === "enrollment") {
    const hp = window.hilda || window.emilio;
    try {
      const r = await hp.setupRequest("list_enrollment_phrases");
      const n = (r.phrases || []).filter((x) => x.recorded).length;
      if (n < 3) {
        setStatus("Record at least three phrases (including “Hey Hilda” lines).", "bad");
        return;
      }
    } catch (e) {
      setStatus(String(e.message || e), "bad");
      return;
    }
  }
  const nextIdx = Math.max(0, Math.min(FLOW.length - 1, stepIndex + delta));
  if (delta > 0 && cur === "voices") {
    const ok = await saveSelectedVoice();
    if (!ok) return;
  }
  stepIndex = nextIdx;
  const name = FLOW[stepIndex];
  showOnlyStep(name);
  renderStepDots();

  if (name === "enrollment") await renderEnrollmentList();
  if (name === "voices" && voiceChoices.length === 0) {
    await loadVoiceList(8);
  }
  if (name === "practice") buildPracticeUI();
  updateNavButtons();
}

async function init() {
  renderStepDots();
  showOnlyStep("welcome");

  $("btn-skip")?.addEventListener("click", async () => {
    const hp = window.hilda || window.emilio;
    try {
      await hp.skipSetupWizard();
    } catch (e) {
      alert(e.message || String(e));
    }
  });

  $("accept-terms")?.addEventListener("change", updateNavButtons);

  $("btn-quit-decline").addEventListener("click", async () => {
    const hp = window.hilda || window.emilio;
    await hp.declineSetupQuit();
  });

  $("open-mic").addEventListener("click", async () => {
    await (window.hilda || window.emilio).openMicPrivacySettings();
  });

  $("open-path-hint")?.addEventListener("click", async () => {
    const fb = $("path-feedback");
    const r = await (window.hilda || window.emilio).addProjectToUserPath();
    if (fb) fb.textContent = r.ok ? "PATH updated (new terminals only)." : r.detail || "Failed";
  });

  $("btn-preview-voice")?.addEventListener("click", () => previewSelected());
  $("btn-prev-voice")?.addEventListener("click", () => {
    if (voiceChoices.length > 0) {
      currentCarouselIndex = (currentCarouselIndex - 1 + voiceChoices.length) % voiceChoices.length;
      updateCarouselUI();
    }
  });
  $("btn-next-voice")?.addEventListener("click", () => {
    if (voiceChoices.length > 0) {
      currentCarouselIndex = (currentCarouselIndex + 1) % voiceChoices.length;
      updateCarouselUI();
    }
  });

  $("btn-record-mic").addEventListener("click", async () => {
    const log = $("practice-log");
    const hp = window.hilda || window.emilio;
    if (log) log.textContent = "Listening… speak after noise settles.";
    try {
      const r = await hp.setupRequest("practice_transcribe");
      if (log) log.textContent = r.transcript || "(empty)";
    } catch (e) {
      if (log) log.textContent = e.message || String(e);
    }
  });

  $("btn-back").addEventListener("click", () => gotoStep(-1));
  $("btn-next").addEventListener("click", async () => {
    const cur = FLOW[stepIndex];
    const hp = window.hilda || window.emilio;
    if (cur === "done") {
      await hp.completeSetupWizard({
        finishedSetup: true,
        voiceIdSaved: !!selectedVoiceId,
        displayName: ($("user-display-name")?.value || "").trim(),
      });
      return;
    }
    await gotoStep(1);
  });

  await waitForBackend();
  await refreshEnv();
  await loadVoiceList(8);
  updateNavButtons();
}

document.addEventListener("DOMContentLoaded", init);
