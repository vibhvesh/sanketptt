import { loadConfig, saveConfig, isAllowedServer } from "./config.js";
import { localCapability, serverHealthy } from "./detect.js";
import { transcribeTransmission } from "./router.js";

const notes = new Map();

function escapeText(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function lineHtml(note) {
  if (!note || note.pending) return '<span class="ptt2-badge wait">…</span> transcribing';
  const label = note.source === "server" ? "server" : "local";
  const text = note.text ? escapeText(note.text) : "(empty result)";
  return `<span class="ptt2-badge ${label}">${label}</span> ${text}`;
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
    line.innerHTML = lineHtml(notes.get(entry.key));
  });
}

export function watchRecorder(recorder, renderLog) {
  const originalEnd = recorder.end.bind(recorder);
  recorder.end = function () {
    const entry = originalEnd();
    if (entry && entry.wav) {
      notes.set(entry.key, { pending: true });
      decorateLog(recorder.entries);
      transcribeTransmission(entry.wav).then((result) => {
        notes.set(entry.key, { pending: false, source: result.source, text: result.text });
        decorateLog(recorder.entries);
      }).catch((error) => {
        notes.set(entry.key, { pending: false, source: "local", text: "Local transcription failed: " + (error && error.message ? error.message : String(error)) });
        decorateLog(recorder.entries);
      });
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
    <p class="ptt2-hint">Auto and Server use Sanket Transcribe when it answers. Otherwise the clip stays on this device.</p>
    <label for="ptt2Server">Sanket Transcribe server URL</label>
    <input id="ptt2Server" type="url" placeholder="https://….sanketptt.com" autocomplete="off">
    <label for="ptt2Language">Language</label>
    <select id="ptt2Language">
      <option value="en">English</option>
      <option value="hi">Hindi</option>
      <option value="auto">Auto</option>
    </select>
    <div class="row"><label><input id="ptt2Translate" type="checkbox"> Translate to English</label></div>
    <p id="ptt2Status"></p>
  `;
  const mode = root.querySelector("#ptt2Mode");
  const server = root.querySelector("#ptt2Server");
  const language = root.querySelector("#ptt2Language");
  const translate = root.querySelector("#ptt2Translate");
  const status = root.querySelector("#ptt2Status");
  mode.value = config.mode;
  server.value = config.serverUrl;
  language.value = ["en", "hi", "auto"].includes(config.language) ? config.language : "en";
  translate.checked = config.translate;

  async function refreshStatus() {
    const current = loadConfig();
    const device = localCapability();
    let serverText = "Server not set.";
    if (current.rejectedServer) serverText = "That server is not a Sanket Transcribe host.";
    else if (current.serverUrl) {
      const up = await serverHealthy(current.serverUrl);
      serverText = up ? "Sanket Transcribe server responded." : "Sanket Transcribe server did not respond. Local will be used.";
    }
    status.textContent = serverText + (device.ok ? " Local Whisper can run here" + (device.webgpu ? " (WebGPU)." : " (WASM).") : " This browser cannot run local Whisper.");
  }

  function persist() {
    const typed = server.value.trim();
    if (typed && !isAllowedServer(typed)) {
      status.textContent = "Server URL must be https on sanketptt.com. It was not saved.";
      return;
    }
    saveConfig({
      mode: mode.value,
      serverUrl: typed,
      language: language.value,
      translate: translate.checked,
    });
    refreshStatus();
  }

  mode.addEventListener("change", persist);
  server.addEventListener("change", persist);
  language.addEventListener("change", persist);
  translate.addEventListener("change", persist);
  refreshStatus();
}
