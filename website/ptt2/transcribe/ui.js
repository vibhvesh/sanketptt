import { SANKET_TRANSCRIBE_SERVER, SERVER_CUSTOM, SERVER_SANKET, loadConfig, saveConfig, isAllowedServer } from "./config.js";
import { localCapability, serverHealthy } from "./detect.js";
import { transcribeTransmission } from "./router.js";
import { lineFromRadio } from "./line.js";

const notes = new Map();

function escapeText(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function lineHtml(note, key) {
  if (!note || note.pending) return '<span class="ptt2-badge wait">…</span> transcribing';
  if (note.skipped) return '<span class="ptt2-badge wait">too short</span> too short';
  if (note.failed) {
    return '<span class="ptt2-badge local">failed</span> transcription failed <button type="button" class="ptt2-retry" data-retry="' + key + '">Retry</button>';
  }
  const label = note.source === "server" ? "server" : "local";
  const text = note.text ? escapeText(note.text) : "(no speech)";
  const extra = note.note ? `<span class="ptt2-note">${escapeText(note.note)}</span>` : "";
  return `<span class="ptt2-badge ${label}">${label}</span> ${text}${extra}`;
}

export function decorateLog(entries) {
  const log = document.getElementById("log");
  if (!log || !entries) return;
  entries.forEach((entry) => {
    const button = log.querySelector(`button[data-k="${entry.key}"]`);
    if (!button) return;
    const item = button.closest("li");
    if (!item) return;
    let line = item.querySelector(".ptt2-line");
    if (!line) {
      line = document.createElement("div");
      line.className = "ptt2-line";
      item.append(line);
    }
    line.innerHTML = lineHtml(notes.get(entry.key), entry.key);
  });
}

const clips = new Map();
const SAFETY_MS = 50000;

function remember(key, wav) {
  clips.set(key, wav);
  if (clips.size > 30) clips.delete(clips.keys().next().value);
}

function applyResult(recorder, key, result) {
  notes.set(key, {
    pending: false,
    skipped: !!result.skipped,
    failed: !!result.failed,
    source: result.source,
    text: result.text || "",
    note: result.note || "",
  });
  decorateLog(recorder.entries);
  if (result.note && !result.skipped) {
    const status = document.getElementById("ptt2Status");
    if (status) status.textContent = result.note;
  }
}

function startJob(recorder, key, wav, line) {
  notes.set(key, { pending: true });
  decorateLog(recorder.entries);
  let settled = false;
  const finish = (result) => {
    if (settled) return;
    settled = true;
    applyResult(recorder, key, result);
  };
  const watchdog = setTimeout(() => finish({ failed: true, text: "transcription failed", note: "timed out" }), SAFETY_MS);
  transcribeTransmission(wav, line).then((result) => {
    clearTimeout(watchdog);
    finish(result || { failed: true, text: "transcription failed" });
  }).catch((error) => {
    clearTimeout(watchdog);
    finish({ failed: true, text: "transcription failed", note: error && error.message ? error.message : "" });
  });
}

export function watchRecorder(recorder, renderLog) {
  const log = document.getElementById("log");
  if (log && !log.dataset.ptt2Retry) {
    log.dataset.ptt2Retry = "1";
    log.addEventListener("click", (event) => {
      const button = event.target.closest("[data-retry]");
      if (!button) return;
      event.preventDefault();
      event.stopPropagation();
      const key = Number(button.getAttribute("data-retry"));
      const wav = clips.get(key);
      if (!wav) return;
      startJob(recorder, key, wav, lineFromRadio(globalThis.radio, { mine: true, name: globalThis.radio && globalThis.radio.name, id: globalThis.radio && globalThis.radio.id }));
    }, true);
  }
  const originalEnd = recorder.end.bind(recorder);
  recorder.end = function () {
    const entry = originalEnd();
    if (entry && entry.wav) {
      remember(entry.key, entry.wav);
      startJob(recorder, entry.key, entry.wav, lineFromRadio(globalThis.radio, entry));
    }
    return entry;
  };
  recorder.onChange = function (entries) {
    renderLog(entries);
    decorateLog(entries);
  };
}

export function mountSettings(root) {
  const config = loadConfig();
  root.innerHTML = `
    <h3>TRANSCRIPTION</h3>
    <label for="ptt2Mode">Mode</label>
    <select id="ptt2Mode">
      <option value="auto">Auto</option>
      <option value="local">Local</option>
      <option value="server">Server</option>
    </select>
    <p class="ptt2-hint">Auto uses Sanket Transcribe when it answers. Line default keeps that channel's language and model.</p>
    <label for="ptt2ServerChoice">Server</label>
    <select id="ptt2ServerChoice">
      <option value="sanket">Sanket Transcribe (stlu-001)</option>
      <option value="custom">Custom URL…</option>
    </select>
    <label for="ptt2Server" id="ptt2ServerLabel" hidden>Custom URL</label>
    <input id="ptt2Server" type="url" placeholder="https://…" autocomplete="off" hidden>
    <label for="ptt2Language">Language</label>
    <select id="ptt2Language">
      <option value="auto">Line default</option>
      <option value="gu">Gujarati</option>
      <option value="hi">Hindi</option>
      <option value="en">English</option>
    </select>
    <div class="row"><label><input id="ptt2Translate" type="checkbox"> Translate to English</label></div>
    <p id="ptt2Status"></p>
  `;
  const mode = root.querySelector("#ptt2Mode");
  const choice = root.querySelector("#ptt2ServerChoice");
  const serverLabel = root.querySelector("#ptt2ServerLabel");
  const server = root.querySelector("#ptt2Server");
  const language = root.querySelector("#ptt2Language");
  const translate = root.querySelector("#ptt2Translate");
  const status = root.querySelector("#ptt2Status");
  mode.value = config.mode;
  choice.value = config.serverChoice === SERVER_CUSTOM ? SERVER_CUSTOM : SERVER_SANKET;
  server.value = config.serverChoice === SERVER_CUSTOM ? config.serverUrl : "";
  language.value = ["en", "hi", "gu", "auto"].includes(config.language) ? config.language : "auto";
  translate.checked = config.translate;

  function showCustom() {
    const custom = choice.value === SERVER_CUSTOM;
    server.hidden = !custom;
    serverLabel.hidden = !custom;
  }

  async function refreshStatus() {
    const current = loadConfig();
    const device = localCapability();
    let serverText = "Server not set.";
    if (current.rejectedServer) serverText = "Custom URL must start with https.";
    else if (current.serverUrl) {
      const health = await serverHealthy(current.serverUrl);
      serverText = health.ok ? "Sanket Transcribe server responded." : health.reason;
    }
    status.textContent = serverText + (device.ok ? " Local Whisper can run here" + (device.webgpu ? " (WebGPU)." : " (WASM).") : " This browser cannot run local Whisper.");
  }

  function persist() {
    showCustom();
    const custom = choice.value === SERVER_CUSTOM;
    const typed = server.value.trim();
    if (custom && typed && !isAllowedServer(typed)) {
      status.textContent = "Custom URL must start with https. It was not saved.";
      return;
    }
    saveConfig({
      mode: mode.value,
      serverChoice: custom ? SERVER_CUSTOM : SERVER_SANKET,
      serverUrl: custom ? typed : SANKET_TRANSCRIBE_SERVER,
      language: language.value,
      translate: translate.checked,
    });
    refreshStatus();
  }

  showCustom();
  mode.addEventListener("change", persist);
  choice.addEventListener("change", persist);
  server.addEventListener("change", persist);
  language.addEventListener("change", persist);
  translate.addEventListener("change", persist);
  refreshStatus();
}
