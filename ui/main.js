/**
 * Electron main — Dynamic Island + Setup wizard + bundled Python backend.
 */
const { app, BrowserWindow, ipcMain, screen, shell, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn, spawnSync } = require("child_process");

app.name = "Hilda";

let islandWindow = null;
let setupWindow = null;
let isExpanded = false;
/** @type {import('child_process').ChildProcess | null} */
let backendChild = null;

const PILL_W = 340;
const PILL_H = 54;
const EXPANDED_W = 460;
const EXPANDED_H = 560;

function getProjectRoot() {
  return path.resolve(__dirname, "..");
}

function onboardingFile() {
  return path.join(app.getPath("userData"), "onboarding-complete.json");
}

function isOnboardingComplete() {
  if (process.argv.includes("--skip-setup")) {
    return true;
  }
  try {
    const data = JSON.parse(fs.readFileSync(onboardingFile(), "utf8"));
    return !!(data && data.completed);
  } catch {
    return false;
  }
}

function writeOnboarding(profile = {}) {
  fs.mkdirSync(path.dirname(onboardingFile()), { recursive: true });
  const payload = Object.assign({ completed: true, version: 1 }, profile || {});
  fs.writeFileSync(onboardingFile(), JSON.stringify(payload, null, 2), "utf8");
}

function resolveDefaultsEnvExample() {
  const candidates = [
    path.join(process.resourcesPath, "defaults", ".env.example"),
    path.join(process.resourcesPath, "backend", "defaults", ".env.example"),
    path.join(process.resourcesPath, "backend", "_internal", "defaults", ".env.example"),
  ];
  for (const p of candidates) {
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function ensureUserDataEnv() {
  const ud = app.getPath("userData");
  const envPath = path.join(ud, ".env");
  if (fs.existsSync(envPath)) return;
  const src = resolveDefaultsEnvExample();
  if (!src && !app.isPackaged) {
    const dev = path.join(getProjectRoot(), ".env.example");
    if (fs.existsSync(dev)) {
      fs.mkdirSync(ud, { recursive: true });
      fs.copyFileSync(dev, envPath);
    }
    return;
  }
  if (src) {
    fs.mkdirSync(ud, { recursive: true });
    fs.copyFileSync(src, envPath);
  }
}

function backendExePath() {
  return path.join(process.resourcesPath, "backend", "hilda-engine.exe");
}

function startBackend() {
  ensureUserDataEnv();
  const ud = app.getPath("userData");
  const env = Object.assign({}, process.env, {
    HILDA_USER_DATA: ud,
    // While setup is open, backend should not greet or run continuous wake listening.
    HILDA_SETUP_MODE: isOnboardingComplete() ? "0" : "1",
  });

  if (app.isPackaged) {
    const exe = backendExePath();
    if (!fs.existsSync(exe)) {
      dialog.showErrorBox(
        "Hilda",
        "The voice engine (hilda-engine.exe) is missing from this install.\nRebuild with npm run build:full or reinstall."
      );
      return;
    }
    backendChild = spawn(exe, [], {
      env,
      cwd: path.dirname(exe),
      stdio: "ignore",
      windowsHide: true,
    });
    backendChild.on("error", (err) => {
      console.error("Backend spawn error:", err);
    });
    backendChild.on("exit", (code) => {
      console.warn("Backend exited with code", code);
      backendChild = null;
    });
    return;
  }

  const root = getProjectRoot();
  const py = process.platform === "win32" ? "python" : "python3";
  backendChild = spawn(py, ["main.py"], {
    cwd: root,
    env,
    stdio: "ignore",
    windowsHide: true,
  });
  backendChild.on("error", (err) => {
    dialog.showErrorBox(
      "Hilda — backend",
      `Could not start Python (${py}). Install Python 3.10+ and pip install -r requirements.txt, or run the packaged installer.\n\n${err.message}`
    );
  });
  backendChild.on("exit", () => {
    backendChild = null;
  });
}

function stopBackend() {
  if (!backendChild || backendChild.killed) return;
  try {
    if (process.platform === "win32") {
      spawnSync("taskkill", ["/PID", String(backendChild.pid), "/T", "/F"], {
        stdio: "ignore",
        windowsHide: true,
      });
    } else {
      backendChild.kill("SIGTERM");
    }
  } catch (_) {
    try {
      backendChild.kill("SIGKILL");
    } catch (_) {}
  }
  backendChild = null;
}

function getWindowBounds(expanded) {
  const { width } = screen.getPrimaryDisplay().workAreaSize;
  const w = expanded ? EXPANDED_W : PILL_W;
  const h = expanded ? EXPANDED_H : PILL_H;
  return {
    x: Math.round((width - w) / 2),
    y: 12,
    width: w,
    height: h,
  };
}

function createIslandWindow() {
  if (islandWindow) return;
  const bounds = getWindowBounds(false);

  islandWindow = new BrowserWindow({
    ...bounds,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, "src", "hilda-ai.png"),
    show: false,
  });

  // Ignore mouse events on the transparent window background so clicks pass through to apps underneath
  islandWindow.setIgnoreMouseEvents(true, { forward: true });

  islandWindow.loadFile(path.join(__dirname, "src", "index.html"));
  islandWindow.setMenuBarVisibility(false);

  islandWindow.on("closed", () => {
    islandWindow = null;
  });
}

function createSetupWindow() {
  setupWindow = new BrowserWindow({
    width: 640,
    height: 720,
    minWidth: 520,
    minHeight: 580,
    show: false,
    autoHideMenuBar: true,
    backgroundColor: "#0f1218",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    icon: path.join(__dirname, "src", "hilda-ai.png"),
    title: "Hilda Setup",
  });
  setupWindow.loadFile(path.join(__dirname, "src", "setup.html"));
  setupWindow.once("ready-to-show", () => setupWindow && setupWindow.show());
  setupWindow.on("closed", () => {
    setupWindow = null;
  });
}

// ── IPC ────────────────────────────────────────────────────────────────────

ipcMain.on("set-visibility", (e, visible) => {
  if (!islandWindow) return;
  if (visible) {
    islandWindow.showInactive();
  } else {
    islandWindow.hide();
  }
});

ipcMain.on("toggle-expand", () => {
  if (!islandWindow) return;
  isExpanded = !isExpanded;
  const bounds = getWindowBounds(isExpanded);

  if (isExpanded) {
    islandWindow.setSize(bounds.width, bounds.height, true);
    islandWindow.setPosition(bounds.x, bounds.y, true);
  } else {
    setTimeout(() => {
      if (!isExpanded && islandWindow) {
        islandWindow.setSize(bounds.width, bounds.height, true);
        islandWindow.setPosition(bounds.x, bounds.y, true);
      }
    }, 350);
  }
});

ipcMain.on("start-drag", () => {
  if (islandWindow) islandWindow.setIgnoreMouseEvents(false);
});

ipcMain.on("set-ignore-mouse-events", (e, ignore, forward) => {
  if (islandWindow) {
    islandWindow.setIgnoreMouseEvents(ignore, { forward: forward });
  }
});

ipcMain.handle("get-project-root", () => getProjectRoot());

ipcMain.handle("open-microphone-settings", () => {
  shell.openExternal("ms-settings:privacy-microphone");
});

ipcMain.handle("open-speech-settings", () => {
  shell.openExternal("ms-settings:speech");
});

ipcMain.handle("add-project-to-user-path", () => {
  const dir = getProjectRoot();
  const escaped = dir.replace(/'/g, "''");
  const ps = `$target='${escaped}'; $p=[Environment]::GetEnvironmentVariable('Path','User'); if (-not $p) { $p='' }; if ($p -notlike '*'+$target+'*') { [Environment]::SetEnvironmentVariable('Path', ($p.TrimEnd(';')+';'+$target), 'User'); 'added' } else { 'already' }`;

  try {
    const r = spawnSync("powershell.exe", ["-NoProfile", "-STA", "-Command", ps], {
      encoding: "utf8",
    });
    const out = `${r.stdout || ""}${r.stderr || ""}`.trim();
    const ok = r.status === 0;
    return { ok, detail: ok ? out || "updated" : out || String(r.error || "powershell failed") };
  } catch (e) {
    return { ok: false, detail: String(e) };
  }
});

ipcMain.handle("complete-setup-wizard", (_, profile) => {
  writeOnboarding(profile || {});
  try {
    const ud = app.getPath("userData");
    const usPath = path.join(ud, "user_settings.json");
    let cur = {};
    try {
      cur = JSON.parse(fs.readFileSync(usPath, "utf8"));
    } catch (_) {}
    const dn = profile && profile.displayName ? String(profile.displayName).trim() : "";
    if (dn) {
      cur.user_display_name = dn;
      fs.mkdirSync(ud, { recursive: true });
      fs.writeFileSync(usPath, JSON.stringify(cur, null, 2), "utf8");
    }
  } catch (e) {
    console.error("user_settings.json merge failed:", e);
  }
  createIslandWindow();
  if (setupWindow) {
    setupWindow.close();
    setupWindow = null;
  }
  return true;
});

ipcMain.handle("skip-setup-wizard", () => {
  writeOnboarding({ skipped: true });
  createIslandWindow();
  if (setupWindow) {
    setupWindow.close();
    setupWindow = null;
  }
  return true;
});

ipcMain.handle("decline-setup-quit", () => {
  app.quit();
});

// ── Lifecycle ────────────────────────────────────────────────────────────────

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (setupWindow) setupWindow.focus();
    if (islandWindow) islandWindow.focus();
  });

  app.whenReady().then(() => {
    startBackend();
    if (isOnboardingComplete()) {
      createIslandWindow();
    } else {
      createSetupWindow();
    }
  });

  app.on("before-quit", () => {
    stopBackend();
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
  });

  app.on("activate", () => {
    if (!islandWindow && !setupWindow) {
      if (isOnboardingComplete()) createIslandWindow();
      else createSetupWindow();
    }
  });
}
